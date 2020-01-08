#!/usr/bin/env python
# * coding: utf8 *
'''
engine.py

A module that contains the implementation of the cli commands
'''

import logging
import socket
import sys
from imp import load_source
from json import dump, load
from os import linesep, listdir, walk
from os.path import (abspath, basename, dirname, exists, join, normpath,
                     realpath, splitext)
from re import compile
from shutil import copytree, rmtree
from time import clock, sleep

import pystache
from colorama import Fore
from colorama import init as colorama_init
from git import Repo
from requests import get

from . import config, core, lift, seat
from .arcgis import LightSwitch
from .config import get_config_prop
from .messaging import send_email, send_to_slack
from .models import Pallet
from .slack import lift_report_to_blocks

log = logging.getLogger('forklift')
lift_template = join(abspath(dirname(__file__)), 'templates', 'lift.html')
ship_template = join(abspath(dirname(__file__)), 'templates', 'ship.html')
speedtest_destination = join(dirname(realpath(__file__)), '..', '..', 'speedtest', 'data')
packing_slip_file = 'packing-slip.json'
colorama_init()

pallet_file_regex = compile(r'pallet.*\.py$')


def init():
    '''Creates the default config in the forklift-garage if it does not exists

    returns the full path to the config
    '''
    if exists(config.config_location):
        return abspath(config.config_location)

    return config.create_default_config()


def add_repo(repo):
    '''repo: string `username/repository`

    Adds the repository to the repositories section of the config

    returns a status string message
    '''
    try:
        _validate_repo(repo, raises=True)
    except Exception as e:
        return e

    return config.set_config_prop('repositories', repo)


def remove_repo(repo):
    '''repo: string `username/repository`

    Removes the repository from the config section

    returns a status string message
    '''
    repos = _get_repos()

    try:
        repos.remove(repo)
    except ValueError:
        return '{} is not in the repositories list!'.format(repo)

    config.set_config_prop('repositories', repos, override=True)

    repository_name = repo.split('/')[1]
    possible_path = join(config.get_config_prop('warehouse'), repository_name)

    lift._remove_if_exists(possible_path)

    return '{} removed'.format(repo)


def list_pallets():
    '''Finds all of the pallets in the warehouse

    returns an array of tuples where the tuple is a file path and a pallet instance
    '''
    return _get_pallets_in_folder(config.get_config_prop('warehouse'))


def list_repos():
    '''Returns a list of valid github repositories in the format of repo: [Valid] or [Invalid repo name or owner]
    '''
    folders = _get_repos()

    validate_results = []
    for folder in folders:
        validate_results.append(_validate_repo(folder))

    return validate_results


def lift_pallets(file_path=None, pallet_arg=None, skip_git=False):
    '''
    file_path: string - an optional path to a pallet.py file
    pallet_arg: string - an optional argument to send to a pallet
    skip_git: boolean - an optional argument to skip git pulling all of the repositories

    The first part of the forklift process. This method updates all of the github repositories, builds all of the pallets,
    prepares them for packaging,processes the crates, processes the pallets, drops off the data in the drop off location,
    and then gift wraps it. It then creates a packing slip that will be used later in the ship method amd sends a report
    about what happened.

    This is the method that initiates change detection and copies data that has changed to the drop off location without
    forklift hashes and the data is compressed and ready for production use.

    The drop off location data is deleted every time lift_pallets is run.
    '''
    log.info('starting forklift')

    if not skip_git:
        git_errors = git_update()
    else:
        git_errors = []

    start_seconds = clock()

    log.debug('building pallets')
    pallets_to_lift, import_errors = _build_pallets(file_path, pallet_arg)

    log.debug('processing checklist')
    lift.process_checklist(config)

    start_process = clock()
    lift.prepare_packaging_for_pallets(pallets_to_lift)
    log.info('prepare_packaging_for_pallets time: %s', seat.format_time(clock() - start_process))

    start_process = clock()
    core.init(log)
    lift.process_crates_for(pallets_to_lift, core.update)
    log.info('process_crates time: %s', seat.format_time(clock() - start_process))

    start_process = clock()
    lift.process_pallets(pallets_to_lift)
    log.info('process_pallets time: %s', seat.format_time(clock() - start_process))

    start_process = clock()
    lift.dropoff_data(pallets_to_lift, config.get_config_prop('dropoffLocation'))
    log.info('dropoff_data time: %s', seat.format_time(clock() - start_process))

    start_process = clock()
    lift.gift_wrap(config.get_config_prop('dropoffLocation'))
    log.info('gift wrapping data time: %s', seat.format_time(clock() - start_process))

    #: log process times for each pallet
    for pallet in pallets_to_lift:
        log.debug('processing times (in seconds) for %r: %s', pallet, pallet.processing_times)

    elapsed_time = seat.format_time(clock() - start_seconds)
    status = lift.get_lift_status(pallets_to_lift, elapsed_time, git_errors, import_errors)

    _generate_packing_slip(status, config.get_config_prop('dropoffLocation'))

    _send_report_email(lift_template, status, 'Lifting', include_packing_slip=True)
    _send_report_to_slack(status, 'Lifting')

    report = _generate_console_report(status)
    log.info('finished in {}.'.format(elapsed_time))

    log.info('%s', report)

    return report


def ship_data(pallet_arg=None, by_service=False):
    '''pallet_arg: string - an optional value to pass to a pallet when it is being built

    This is the second phase of the forklift process. This looks for a packing slip and data
    in the drop off location, stops the arcgis server, copies the data to the server, starts
    the server back up, then calls post copy process and ship on pallets that qualify.
    A report is generated on the status of the pallets and any services that did not start

    returns the report object
    '''
    log.info('starting forklift')

    start_seconds = clock()

    #: look for servers in config
    servers = config.get_config_prop('servers')

    if servers is None or len(servers) == 0:
        log.info('no servers defined in config')
        servers = []

    #: look for drop off location
    pickup_location = config.get_config_prop('dropoffLocation')

    files_and_folders = set(listdir(pickup_location))
    if not exists(pickup_location) or len(files_and_folders) == 0:
        log.warning('no data found or packing slip found in pickup location.. exiting')

        return False

    missing_packing_slip = False
    if packing_slip_file not in files_and_folders:
        missing_packing_slip = True
        log.info('no packing slip found in pickup location... copying data only')

    ship_only = False
    if missing_packing_slip is False and len(files_and_folders) == 1:
        log.info('only packing slip found in pickup location... shipping pallets only')
        ship_only = True

    server_reports = []
    all_failed_copies = {}
    start_process = clock()

    if not ship_only:
        switches = [LightSwitch(server) for server in servers.items()]

        if by_service:
            all_pallets, _ = _build_pallets(None, pallet_arg)

        #: for each server
        for switch in switches:
            server_report = {'name': switch.server_label, 'failed_copies': {}, 'successful_copies': [], 'problem_services': [], 'success': True, 'message': ''}

            log.info('stopping (%s)', switch.server_label)
            start_sub_process = clock()

            #: stop server or services
            if by_service:
                data_being_moved = set(listdir(config.get_config_prop('dropoffLocation'))) - set([packing_slip_file])
                services_affected = _get_affected_services(data_being_moved, all_pallets)
                status, messages = switch.ensure_services('off', services_affected)
                item_being_acted_upon = ', '.join([service_info[0] for service_info in services_affected])
            else:
                status, messages = switch.ensure('stop')
                item_being_acted_upon = switch.server_label

            log.info('stopping %s time: %s', item_being_acted_upon, seat.format_time(clock() - start_sub_process))

            if status is False:
                error_msg = '{} did not stop, skipping copy. {}'.format(item_being_acted_upon, messages)
                log.error(error_msg)
                server_report['success'] = False
                server_report['message'] = error_msg
                continue

            #: wait period (failover logic)
            sleep_timer = config.get_config_prop('serverStartWaitSeconds')
            log.debug('sleeping: %s', sleep_timer)
            sleep(sleep_timer)

            start_sub_process = clock()

            #: copy data
            successful_copies, failed_copies = lift.copy_data(
                config.get_config_prop('dropoffLocation'), config.get_config_prop('shipTo'), packing_slip_file, switch.server_qualified_name
            )
            server_report['successful_copies'] = successful_copies
            server_report['failed_copies'] = failed_copies
            all_failed_copies.update(failed_copies)

            log.info('copy data time: %s', seat.format_time(clock() - start_sub_process))

            log.info('starting (%s)', item_being_acted_upon)
            start_sub_process = clock()

            #: start server
            if by_service:
                status, messages = switch.ensure_services('on', services_affected)
            else:
                status, messages = switch.ensure('start')

            log.info('starting %s time: %s', item_being_acted_upon, seat.format_time(clock() - start_sub_process))

            if status is False:
                error_msg = '{} did not restart. {}'.format(item_being_acted_upon, messages)
                log.error(error_msg)
                server_report['success'] = False
                server_report['message'] = error_msg

            #: wait period (failover logic)
            log.debug('sleeping: %s', sleep_timer)
            sleep(sleep_timer)

            start_sub_process = clock()

            server_report['problem_services'] = switch.validate_service_state()
            log.info('validate service time: %s', seat.format_time(clock() - start_sub_process))
            if len(server_report['problem_services']) > 0:
                server_report['success'] = False
                server_report['has_service_issues'] = True

            server_reports.append(server_report)
        log.info('total copy time: %s', seat.format_time(clock() - start_process))

    pallet_reports = []
    if not missing_packing_slip:
        #: get affected pallets
        pallets_to_ship = _process_packing_slip(None, pallet_arg)

        for pallet in pallets_to_ship:
            slip = pallet.slip
            slip['total_processing_time'] = 0

            # check to see if copy was successful
            copy_items = [basename(item) for item in pallet.copy_data]
            for copy_item in copy_items:
                if copy_item in all_failed_copies:
                    slip['success'] = False
                    slip['message'] += all_failed_copies[copy_item]

            #: run pallet lifecycle
            slip['post_copy_processed'] = False
            slip['shipped'] = False
            try:
                if slip['success'] or slip['ship_on_fail'] and slip['requires_processing']:
                    log.info('post copy processing (%r)', pallet)
                    with seat.timed_pallet_process(pallet, 'post-copy-process'):
                        pallet.post_copy_process()

                    slip['post_copy_processed'] = True

                if slip['success'] or slip['ship_on_fail']:
                    log.info('shipping (%r)', pallet)
                    with seat.timed_pallet_process(pallet, 'ship'):
                        pallet.ship()

                    slip['shipped'] = True

                #: update pallet result for report in case the result was set
                #: during post_copy_process or ship
                slip['success'] = pallet.success[0]
                if pallet.success[1] is not None:
                    slip['message'] += pallet.success[1]
            except Exception as e:
                slip['success'] = False
                slip['message'] = e
                log.error('error for pallet: %r: %s', pallet, e, exc_info=True)

            slip['total_processing_time'] = seat.format_time(pallet.total_processing_time)
            pallet_reports.append(slip)

    elapsed_time = seat.format_time(clock() - start_seconds)
    status = {
        'hostname': socket.gethostname(),
        'total_pallets': len(pallet_reports),
        'pallets': pallet_reports,
        'num_success_pallets': len([p for p in pallet_reports if p['success']]),
        'server_reports': server_reports,
        'total_time': elapsed_time
    }

    _send_report_email(ship_template, status, 'Shipping')

    report = _generate_ship_console_report(status)

    log.info('%s', report)

    return report


def speedtest(pallet_location):
    '''pallet_location: string - a file path to a pallet.py

    Runs a repeatable process that is used to determine regressions or progressions in the efficiency of forklift

    returns a report object
    '''
    print(('{0}{1}Setting up speed test...{0}'.format(Fore.RESET, Fore.MAGENTA)))

    def _change_data(data_path):
        import arcpy

        def field_changer(value):
            return value[:-1] + 'X' if value else 'X'

        change_field = 'FieldToChange'
        value_field = 'UTAddPtID'

        with arcpy.da.UpdateCursor(data_path, [value_field, change_field]) as cursor:
            for row in cursor:
                row[1] = field_changer(row[0])
                cursor.updateRow(row)

    def _prep_change_data(data_path):
        import arcpy
        change_field = 'FieldToChange'
        value_field = 'UTAddPtID'

        arcpy.AddField_management(data_path, change_field, 'TEXT', field_length=150)
        where = 'OBJECTID >= 879389 and OBJECTID <= 899388'

        with arcpy.da.UpdateCursor(data_path, [value_field, change_field], where) as update_cursor:
            for row in update_cursor:
                row[1] = row[0]
                update_cursor.updateRow(row)

    #: remove logging
    log.handlers = [logging.NullHandler()]

    #: spoof garage & scratch location so there is no caching
    core.garage = speedtest_destination
    core.scratch_gdb_path = join(core.garage, core._scratch_gdb)

    #: delete destination and other artifacts form prior runs
    import arcpy
    if arcpy.Exists(join(speedtest_destination, 'DestinationData.gdb')):
        arcpy.Delete_management(join(speedtest_destination, 'DestinationData.gdb'))
        arcpy.CreateFileGDB_management(speedtest_destination, 'DestinationData.gdb')
    else:
        arcpy.CreateFileGDB_management(speedtest_destination, 'DestinationData.gdb')

    if arcpy.Exists(join(speedtest_destination, 'ChangeSourceData.gdb')):
        arcpy.Delete_management(join(speedtest_destination, 'ChangeSourceData.gdb'))

    arcpy.Copy_management(join(speedtest_destination, 'SourceData.gdb'), join(speedtest_destination, 'ChangeSourceData.gdb'))
    _prep_change_data(join(speedtest_destination, 'ChangeSourceData.gdb', 'AddressPoints'))

    if arcpy.Exists(core.scratch_gdb_path):
        arcpy.Delete_management(core.scratch_gdb_path)

    print(('{0}{1}Tests ready starting dry run...{0}'.format(Fore.RESET, Fore.MAGENTA)))

    start_seconds = clock()
    dry_report = lift_pallets(pallet_location, skip_git=True)
    dry_run = seat.format_time(clock() - start_seconds)

    print(('{0}{1}Changing data...{0}'.format(Fore.RESET, Fore.MAGENTA)))
    _change_data(join(speedtest_destination, 'ChangeSourceData.gdb', 'AddressPoints'))

    print(('{0}{1}Repeating test...{0}'.format(Fore.RESET, Fore.MAGENTA)))
    start_seconds = clock()
    repeat_report = lift_pallets(pallet_location, skip_git=True)
    repeat = seat.format_time(clock() - start_seconds)

    #: clean up so git state is unchanged
    if arcpy.Exists(join(speedtest_destination, 'DestinationData.gdb')):
        arcpy.Delete_management(join(speedtest_destination, 'DestinationData.gdb'))
    if arcpy.Exists(join(speedtest_destination, 'ChangeSourceData.gdb')):
        arcpy.Delete_management(join(speedtest_destination, 'ChangeSourceData.gdb'))
    if arcpy.Exists(core.scratch_gdb_path):
        arcpy.Delete_management(core.scratch_gdb_path)

    print(('{1}Dry Run Output{0}{2}{3}'.format(Fore.RESET, Fore.CYAN, linesep, dry_report)))
    print(('{1}Repeat Run Output{0}{2}{3}'.format(Fore.RESET, Fore.CYAN, linesep, repeat_report)))
    print(('{3}{0}{1}Speed Test Results{3}{0}{2}Dry Run:{0} {4}{3}{2}Repeat:{0} {5}'.format(Fore.RESET, Fore.GREEN, Fore.CYAN, linesep, dry_run, repeat)))


def scorched_earth():
    '''removes all of the hashed data sets from the config hashLocation property folder

    This method is used when things go poorly and starting over is the only solution
    '''
    hash_location = config.get_config_prop('hashLocation')
    for folder in [hash_location, core.scratch_gdb_path]:
        if exists(folder):
            log.info('deleting: %s', folder)
            rmtree(folder)


def git_update():
    '''updates all of the github repositories in the config repositories section

    returns an array containing any errors or empty array if no errors
    '''
    log.info('git updating...')

    repositories = config.get_config_prop('repositories')

    if len(repositories) == 0:
        log.info('no repositories to update')
        return []

    errors = []
    for repo in repositories:
        error, info = _clone_or_pull_repo(repo)

        if info is not None:
            log.info(info)
        if error is not None:
            log.error(error)
            errors.append(error)

    return errors


def gift_wrap(destination, source=None, pallet_path=None):
    '''
    destination: string - the path to the output folder
    source: string - the path to a file geodatabase
    pallet_path: string - the path to a pallet file

    Copies FGDBs from source or as defined by copy_data in pallet or in hashing directory
    and then scrubs the forklift hash field from them
    '''
    sources = []
    if pallet_path is not None:
        pallets, _ = _build_pallets(pallet_path)
        for pallet in pallets:
            for gdb in pallet.copy_data:
                sources.append(gdb)
    elif source is not None:
        sources.append(source)
    else:
        sources.append(config.get_config_prop('hashLocation'))

    for copy_source in sources:
        log.info('copying data from %s to %s', copy_source, destination)
        lift.copy_with_overwrite(copy_source, join(destination, basename(copy_source)))

    log.info('gift-wrapping data')
    lift.gift_wrap(destination)
    log.info('gift-wrapping completed successfully')


def move_dropoff_data(copy_to_temp):
    dropoff = config.get_config_prop('dropoffLocation')
    temp = dropoff + '_x'

    source = temp
    destination = dropoff

    if copy_to_temp:
        source = dropoff
        destination = temp

    lift._remove_if_exists(destination)

    log.info('copying data from %s to %s', source, destination)
    copytree(source, destination)


def _build_pallets(file_path, pallet_arg=None):
    '''
    file_path: string - the file path of a python.py file
    pallet_arg: string - an optional string to send to the constructor of a pallet

    Finds pallet classes in python files and instantiates them with any `pallet_arg`'s and calls build

    returns a tuple of an array of pallet objects and import errors
    '''
    import_errors = []
    if file_path is not None:
        pallet_infos, import_error = _get_pallets_in_file(file_path)
        if import_error is not None:
            import_errors.append(import_error)
    else:
        pallet_infos, import_errors = list_pallets()

    pallets = []
    for _, PalletClass in pallet_infos:
        try:
            if pallet_arg is not None:
                pallet = PalletClass(pallet_arg)
            else:
                pallet = PalletClass()

            try:
                log.debug('building pallet: %r', pallet)
                pallet.build(config.get_config_prop('configuration'))
            except Exception as e:
                pallet.success = (False, str(e))
                log.error('error building pallet: %s for pallet: %r', e, pallet, exc_info=True)

            pallets.append(pallet)
        except Exception as e:
            log.error('error creating pallet class: %s. %s', PalletClass.__name__, e, exc_info=True)

    pallets.sort(key=lambda p: p.__class__.__name__)

    return pallets, import_errors


def _generate_packing_slip(status, location):
    '''
    status: report object
    location: string - the drop off location folder

    this pulls the pallet status from the report object and writes it to a file in the drop off location
    for later use by the ship command
    '''
    status = [report for report in status['pallets'] if report['is_ready_to_ship'] or report['ship_on_fail']]

    if not exists(location):
        return

    with open(join(location, packing_slip_file), 'w', encoding='utf-8') as slip:
        dump(status, slip, indent=2)


def _process_packing_slip(packing_slip=None, pallet_arg=None):
    '''packing_slip: string - an optional packing slip to process otherwise the default location will be used
    pallet_arg: string - an optional string to send to the constructor of a pallet

    returns all of the pallets referenced by the packing slip
    '''
    if packing_slip is None:
        location = join(config.get_config_prop('dropoffLocation'), packing_slip_file)

        with open(location, 'r', encoding='utf-8') as slip:
            packing_slip = load(slip)

    log.info('packing slip contents: %s', packing_slip)

    pallets = []
    for item in packing_slip:
        if not item['success'] and not item['ship_on_fail']:
            continue

        pallet = _build_pallets(item['name'], pallet_arg)[0][0]
        pallet.add_packing_slip(item)

        pallets.append(pallet)

    return pallets


def _send_report_email(template, report_object, subject, include_packing_slip=False):
    '''Create and sends the report email
    template: string - the file path to a pystache template
    report_object: obj - the template model
    subject: string - a string to insert into the email subject line
    include_packing_slip: boolean - if true, the packing slip is attached to the email
    '''
    log_file = join(dirname(config.config_location), 'forklift.log')

    with open(template, 'r') as template_file:
        email_content = pystache.render(template_file.read(), report_object)

    attachments = [log_file]

    if include_packing_slip:
        packing_slip = join(config.get_config_prop('dropoffLocation'), packing_slip_file)
        attachments.append(packing_slip)

    send_email(config.get_config_prop('notify'),
               'Forklift {} Report for {}'.format(subject, report_object['hostname']),
               email_content,
               attachments)

    return email_content


def _send_report_to_slack(status, operation):
    url = None

    try:
        url = get_config_prop('slackWebhookUrl')
    except Exception:
        pass

    if url is None:
        return

    messages = []

    if operation == 'Lifting':
        messages = lift_report_to_blocks(status)

    send_to_slack(url, messages)


def _clone_or_pull_repo(repo_name):
    '''repo_name: string - a github repository username/reponame format
                  or an object with host, repo, and access token with the username/reponame syntax

                  "repositories": [{
                    "host": "gitlabs.com/",
                    "repo": "name/repo",
                    "token": "personal access token with `read_repository` access only"
                  }]

    clones or pull's the repo passed in

    returns a status tuple with None being successful or a string with the error
    '''
    warehouse = config.get_config_prop('warehouse')
    log_message = None
    shorthand = True
    safe_repo_name = None

    FAST_FORWARD = 64
    FORCED_UPDATE = 32
    HEAD_UPTODATE = 4

    try:
        if isinstance(repo_name, str):
            folder = join(warehouse, repo_name.split('/')[1])
        else:
            shorthand = False
            folder = join(warehouse, repo_name['repo'].split('/')[1])

        if shorthand:
            safe_repo_name = repo_name
        else:
            safe_repo_name = repo_name['repo']

        if not exists(folder):
            repo = Repo.clone_from(_repo_to_url(repo_name, shorthand), join(warehouse, folder))

            log_message = 'git cloning: {}'.format(safe_repo_name)
            repo.close()
        else:
            log_message = 'git updating: {}'.format(safe_repo_name)
            repo = _get_repo(folder)
            origin = repo.remotes[0]
            fetch_infos = origin.pull()

            if len(fetch_infos) > 0:
                if fetch_infos[0].flags == HEAD_UPTODATE:
                    log_message = log_message + '\nno updates to pallet'
                elif fetch_infos[0].flags in [FORCED_UPDATE, FAST_FORWARD]:
                    log_message = log_message + '\nupdated to %s', fetch_infos[0].commit.name_rev

        return (None, log_message)
    except Exception as e:
        return ('Git update error for {}: {}'.format(safe_repo_name, e), log_message)


def _get_repo(folder):
    #: abstraction to enable mocking in tests
    return Repo(folder)


def _repo_to_url(repo, shorthand=True):
    if shorthand:
        return 'https://github.com/{}.git'.format(repo)

    return 'https://forklift:{}@{}{}.git'.format(repo['token'], repo['host'], repo['repo'])


def _get_repos():
    return config.get_config_prop('repositories')


def _validate_repo(repo, raises=False):
    '''
    repo: string - the owner/name of a repository
    raises: boolean - an optional flag to raise an exception if the github repository is not valid

    makes an http request to the github url to validate the repository exists

    returns a validation string or an exception depending on `raises`
    '''
    url = _repo_to_url(repo)
    response = get(url)

    if response.status_code == 200:
        message = '[Valid]'
    else:
        message = '[Invalid repo name or owner]'
        if raises:
            raise Exception('{}: {}'.format(repo, message))

    return '{}: {}'.format(repo, message)


def _get_pallets_in_folder(folder):
    '''folder: string - a path to a folder

    finds all pallet classes in `folder` looking only in `pallet_file_regex` matching files

    returns an array of tuples consisting of the file path and the pallet class object
    '''
    pallets = []
    import_errors = []

    for root, _, files in walk(folder):
        for file_name in files:
            if pallet_file_regex.search(file_name.lower()):
                new_pallets, import_error = _get_pallets_in_file(join(root, file_name))
                pallets.extend(new_pallets)

                if import_error is not None:
                    import_errors.append(import_error)

    return pallets, import_errors


def _get_pallets_in_file(file_path):
    '''file_path: string - a path to a pallet.py file

    finds all python classes that inherit from Pallet

    returns tuple with the first value being an array of tuples consisting of
    the file path and the pallet class object and the second value being any
    import error that may have been thrown while trying to import the pallet.
    '''
    pallets = []
    file_name, extension = splitext(basename(file_path))
    folder = dirname(file_path)

    specific_pallet = None
    if ':' in extension:
        ext, specific_pallet = extension.split(':')
        file_path = join(folder, file_name + ext)

    if folder not in sys.path:
        sys.path.append(folder)

    try:
        try:
            mod = sys.modules[file_name]
        except KeyError:
            mod = load_source(file_name, file_path)
    except Exception as e:
        # skip modules that fail to import
        log.error('%s failed to import: %s', file_path, e, exc_info=True)
        return ([], 'pallet failed to import: {}, {}'.format(file_path, e))

    for member in dir(mod):
        try:
            potential_class = getattr(mod, member)
            if issubclass(potential_class, Pallet) and potential_class != Pallet:
                if specific_pallet is None:
                    pallets.append((file_path, potential_class))
                    continue

                if potential_class.__name__ == specific_pallet:
                    pallets.append((file_path, potential_class))
        except Exception:
            #: member was likely not a class
            pass

    return (pallets, None)


def _generate_console_report(pallet_reports):
    '''pallet_reports: object - the report object

    Formats the `pallet_reports` object into a string for printing to the console with color

    returns the formatted report string
    '''
    report_str = '{3}{3}    {4}{0}{2} out of {5}{1}{2} pallets ran successfully in {6}.{3}'.format(
        pallet_reports['num_success_pallets'], len(pallet_reports['pallets']), Fore.RESET, linesep, Fore.GREEN, Fore.CYAN, pallet_reports['total_time']
    )

    if len(pallet_reports['git_errors']) > 0:
        for git_error in pallet_reports['git_errors']:
            report_str += '{}{}{}'.format(Fore.RED, git_error, linesep)

    if len(pallet_reports['import_errors']) > 0:
        for import_error in pallet_reports['import_errors']:
            report_str += '{}{}{}'.format(Fore.RED, import_error, linesep)

    for report in pallet_reports['pallets']:
        color = Fore.GREEN
        if not report['success']:
            color = Fore.RED

        report_str += '{0}{1}{2} ({4}){3}'.format(color, report['name'], Fore.RESET, linesep, report['total_processing_time'])

        if report['message']:
            report_str += 'pallet message: {}{}{}{}'.format(Fore.RED, report['message'], Fore.RESET, linesep)

        for crate in report['crates']:
            report_str += '{0:>40} - {1}{3}{2}'.format(crate['name'], crate['result'], linesep, Fore.RESET)

            if crate['crate_message'] is None or len(crate['crate_message']) < 1:
                continue

            if crate['message_level'] == 'warning':
                color = Fore.YELLOW
            else:
                color = Fore.RED

            report_str += 'crate message: {0}{1}{2}{3}'.format(color, crate['crate_message'], Fore.RESET, linesep)

    return report_str


def _generate_ship_console_report(pallet_reports):
    '''status: object - the report object

    Formats the `pallet_reports` object into a string for printing to the console with color

    returns the formatted report string
    '''
    report_str = '{3}{3}    {4}{0}{2} out of {5}{1}{2} pallets ran successfully in {6}.{3}'.format(
        pallet_reports['num_success_pallets'], pallet_reports['total_pallets'], Fore.RESET, linesep, Fore.GREEN, Fore.CYAN, pallet_reports['total_time']
    )

    for report in pallet_reports['server_reports']:
        color = Fore.GREEN
        if not report['success']:
            color = Fore.RED

        report_str += '{1}ArcGIS Server Service Status for {2}{0}{3}{1}'.format(report['name'], linesep, Fore.CYAN, Fore.RESET)

        if report.get('has_service_issues', False):
            report_str += '  {1}Problem Services{2}{0}'.format(linesep, Fore.RED, Fore.RESET)

            for service in report['problem_services']:
                report_str += '    {1}{0}{2}{3}'.format(service, Fore.RED, Fore.RESET, linesep)
        else:
            report_str += '    {0}All services started{1}{2}'.format(Fore.GREEN, Fore.RESET, linesep)

        report_str += '  Datasets Copied{0}'.format(linesep)
        if len(report['successful_copies']) < 1:
            report_str += '    {0}No data updated{1}{2}'.format(Fore.RED, Fore.RESET, linesep)
        else:
            for data in report['successful_copies']:
                report_str += '    {2}{0}{3}{1}'.format(data, linesep, Fore.CYAN, Fore.RESET)

    report_str += '{0}Pallet Report{0}'.format(linesep)
    for report in pallet_reports['pallets']:
        color = Fore.GREEN
        if not report['success']:
            color = Fore.RED

        report_str += '  {0}{1}{2} ({4}){3}'.format(color, report['name'], Fore.RESET, linesep, report['total_processing_time'])
        report_str += '  Post Copy Processed: {2}{0}{3}    Shipped: {2}{1}{3}{4}'.format(
            report['post_copy_processed'], report['shipped'], Fore.CYAN, Fore.RESET, linesep
        )

        if report['message']:
            report_str += '  pallet message: {}{}{}{}'.format(color, report['message'], Fore.RESET, linesep)

    return report_str


def _get_affected_services(data_being_moved, all_pallets):
    #: return a list of services that are affected by the data in data_being_moved
    services_affected = set([])

    def normalize_workspace(workspace_path):
        return normpath(workspace_path.lower())

    #: append the services that share datasources
    for pallet in all_pallets:
        for workspace in pallet.copy_data:
            workspace = basename(normalize_workspace(workspace))
            if workspace not in data_being_moved:
                continue

            for service in pallet.arcgis_services:
                services_affected.add(service)
            break

    return services_affected
