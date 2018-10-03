#!/usr/bin/env python
# * coding: utf8 *
'''
engine.py

A module that contains the implementation of the cli commands
'''

import logging
import sys
from imp import load_source
from json import dump, load
from os import environ, linesep, listdir, walk
from os.path import (abspath, basename, dirname, exists, join, realpath,
                     splitext)
from re import compile
from shutil import rmtree
from time import clock, sleep

import pystache
from colorama import Fore
from colorama import init as colorama_init
from git import Repo
from multiprocess import Pool
from requests import get

from . import config, core, lift, seat
from .arcgis import LightSwitch
from .messaging import send_email
from .models import Pallet

log = logging.getLogger('forklift')
template = join(abspath(dirname(__file__)), 'report_template.html')
speedtest_destination = join(dirname(realpath(__file__)), '..', '..', 'speedtest', 'data')
packing_slip_file = 'packing-slip.json'
colorama_init()

pallet_file_regex = compile(r'pallet.*\.py$')


def init():
    '''Creates the default config in the forklift-garage if it does not exists

    returns the filt path to the config
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
    pallets_to_lift, all_pallets = _build_pallets(file_path, pallet_arg)

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
    lift.dropoff_data(pallets_to_lift, all_pallets, config.get_config_prop('dropoffLocation'))
    log.info('dropoff_data time: %s', seat.format_time(clock() - start_process))

    start_process = clock()
    lift.gift_wrap(config.get_config_prop('dropoffLocation'))
    log.info('gift wrapping data time: %s', seat.format_time(clock() - start_process))

    #: log process times for each pallet
    for pallet in pallets_to_lift:
        log.debug('processing times (in seconds) for %r: %s', pallet, pallet.processing_times)

    elapsed_time = seat.format_time(clock() - start_seconds)
    status = lift.get_lift_status(pallets_to_lift, elapsed_time, git_errors)

    _generate_packing_slip(status, config.get_config_prop('dropoffLocation'))

    # _send_report_email(status)

    report = _generate_console_report(status)
    log.info('Finished in {}.'.format(elapsed_time))

    log.info('%s', report)

    return report


def ship_data(pallet_arg=None):
    '''pallet_arg: string - an optional value to pass to a pallet when it is being built

    This is the second phase of the forklift process. This looks for a packing slip and data
    in the drop off location, stops the arcgis server, copies the data to the server, starts
    the server back up, then calls post copy process and ship on pallets that qualify.
    A report is generated on the status of the pallets and any services that did not start

    returns the report object
    '''
    #: look for servers in config
    servers = config.get_config_prop('servers')

    if servers is None or len(servers) == 0:
        log.info('no servers defined in config')
        servers = []

    #: look for drop off location
    pickup_location = config.get_config_prop('dropoffLocation')

    files_and_folders = set(listdir(pickup_location))
    if not exists(pickup_location) or len(files_and_folders) == 0:
        log.warn('no data found or packing slip found in pickup location.. exiting')

        return False

    missing_packing_slip = False
    if packing_slip_file not in files_and_folders:
        missing_packing_slip = True
        log.info('no packing slip found in pickup location... copying data only')

    ship_only = False
    if missing_packing_slip is False and len(files_and_folders) == 1:
        log.info('only packing slip found in pickup location... shipping pallets only')
        ship_only = True

    failed_copies = {}
    successful_copies = []
    problem_services = []
    if not ship_only:
        switches = [LightSwitch(server) for server in servers.items()]

        #: for each server
        for switch in switches:
            log.info('stopping (%s)', switch.server_label)
            #: stop server
            status, messages = switch.ensure('stop')
            #: copy data
            successful_copies, failed_copies = lift.copy_data(config.get_config_prop('dropoffLocation'),
                                                              config.get_config_prop('shipTo'),
                                                              packing_slip_file,
                                                              switch.server_qualified_name)

            log.info('starting (%s)', switch.server_label)
            #: start server
            status, messages = switch.ensure('start')
            #: wait period (failover logic)
            sleep(config.get_config_prop('serverStartWaitSeconds'))
            problem_services = switch.validate_service_state()

    pallet_reports = []
    if not missing_packing_slip:
        #: get affected pallets
        pallets_to_ship = _process_packing_slip()

        for pallet in pallets_to_ship:
            slip = pallet.slip

            # check to see if copy was successful
            copy_items = [basename(item) for item in pallet.copy_data]
            for copy_item in copy_items:
                if copy_item in failed_copies.keys():
                    slip['success'] = False
                    slip['message'] += failed_copies[copy_item]

            #: run pallet lifecycle
            #: post copy process
            try:
                if slip['success'] and slip['requires_processing']:
                    log.info('post copy processing (%r)', pallet)
                    pallet.post_copy_process()
                    slip['post_copy_processed'] = True

                if slip['success']:
                    log.info('shipping (%r)', pallet)
                    pallet.ship()
                    slip['shipped'] = True
            except Exception as e:
                slip['success'] = False
                slip['message'] = e
                log.error('error for pallet: %r: %s', pallet, e, exc_info=True)

            pallet_reports.append(slip)

    #: send report?
    report = {'data_moved': successful_copies,
              'pallets': pallet_reports,
              'problem_services': problem_services}
    log.info('%r', report)

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
    log.info('git updating (in parallel)...')

    repositories = config.get_config_prop('repositories')
    num_repos = len(repositories)

    if num_repos == 0:
        log.info('no repositories to update')
        return []

    num_processes = environ.get('FORKLIFT_POOL_PROCESSES')
    swimmers = num_processes or config.default_num_processes
    if swimmers > num_repos:
        swimmers = num_repos

    with Pool(swimmers) as pool:
        results = pool.map(_clone_or_pull_repo, repositories)

    for error, info in results:
        if info is not None:
            log.info(info)
        if error is not None:
            log.error(error)

    return [error for error, info in results if error is not None]


def _build_pallets(file_path, pallet_arg=None):
    '''
    file_path: string - the file path of a python.py file
    pallet_args: string - an optional string to send to the constructor of a pallet

    Finds pallet classes in python files and instantiates them with any `pallet_arg`'s and calls build

    returns a tuple of sorted pallets and all pallets
    '''
    if file_path is not None:
        pallet_infos = set(_get_pallets_in_file(file_path) + list_pallets())
    else:
        pallet_infos = list_pallets()

    all_pallets = []
    sorted_pallets = []
    for pallet_location, PalletClass in pallet_infos:
        try:
            if pallet_arg is not None:
                pallet = PalletClass(pallet_arg)
            else:
                pallet = PalletClass()

            try:
                log.debug('building pallet: %r', pallet)
                pallet.build(config.get_config_prop('configuration'))
            except Exception as e:
                pallet.success = (False, e)
                log.error('error building pallet: %s for pallet: %r', e, pallet, exc_info=True)

            all_pallets.append(pallet)
            if pallet_location == file_path or file_path is None:
                sorted_pallets.append(pallet)
        except Exception as e:
            log.error('error creating pallet class: %s. %s', PalletClass.__name__, e, exc_info=True)

    sorted_pallets.sort(key=lambda p: p.__class__.__name__)

    return (sorted_pallets, all_pallets)


def _generate_packing_slip(status, location):
    '''
    status: report object
    location: string - the drop off location folder

    this pulls the pallet status from the report object and writes it to a file in the drop off location
    for later use by the ship command
    '''
    status = status['pallets']

    if not exists(location):
        return

    with open(join(location, packing_slip_file), 'w', encoding='utf-8') as slip:
        dump(status, slip, indent=2)


def _process_packing_slip(packing_slip=None):
    '''packing_slip: string - an optional packing slip to process otherwise the default location will be used

    returns all of the pallets referenced by the packing slip
    '''
    if packing_slip is None:
        location = join(config.get_config_prop('dropoffLocation'), packing_slip_file)

        with open(location, 'r', encoding='utf-8') as slip:
            packing_slip = load(slip)

    pallets = []
    for item in packing_slip:
        if not item['success']:
            continue

        sorted, all_pallets = _build_pallets(item['name'])
        all_pallets[0].add_packing_slip(item)

        pallets.append(all_pallets[0])

    return pallets


def _send_report_email(report_object):
    '''Create and sends the report email
    '''
    log_file = join(dirname(config.config_location), 'forklift.log')

    with open(template, 'r') as template_file:
        email_content = pystache.render(template_file.read(), report_object)

    send_email(config.get_config_prop('notify'), 'Forklift Report for {}'.format(report_object['hostname']), email_content, log_file)


def _clone_or_pull_repo(repo_name):
    '''repo_name: string - a github repository username/reponame format

    clones or pull's the repo passed in

    returns a status tuple with None being successful or a string with the error
    '''
    warehouse = config.get_config_prop('warehouse')
    log_message = None

    try:
        folder = join(warehouse, repo_name.split('/')[1])
        if not exists(folder):
            log_message = 'git cloning: {}'.format(repo_name)
            repo = Repo.clone_from(_repo_to_url(repo_name), join(warehouse, folder))
            repo.close()
        else:
            log_message = 'git updating: {}'.format(repo_name)
            repo = _get_repo(folder)
            origin = repo.remotes[0]
            fetch_infos = origin.pull()

            if len(fetch_infos) > 0:
                if fetch_infos[0].flags == 4:
                    log_message = log_message + '\nno updates to pallet'
                elif fetch_infos[0].flags in [32, 64]:
                    log_message = log_message + '\nupdated to %s', fetch_infos[0].commit.name_rev

        return (None, log_message)
    except Exception as e:
        return ('Git update error for {}: {}'.format(repo_name, e), log_message)


def _get_repo(folder):
    #: abstraction to enable mocking in tests
    return Repo(folder)


def _repo_to_url(repo):
    return 'https://github.com/{}.git'.format(repo)


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

    for root, _, files in walk(folder):
        for file_name in files:
            if pallet_file_regex.search(file_name.lower()):
                pallets.extend(_get_pallets_in_file(join(root, file_name)))

    return pallets


def _get_pallets_in_file(file_path):
    '''file_path: string - a path to a pallet.py file

    finds all python classes that inherit from Pallet

    returns an array of tuples consisting of the file path and the pallet class object
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
        return []

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

    return pallets


def _generate_console_report(pallet_reports):
    '''pallet_reports: object - the report object

    Formats the `pallet_reports` object into a string for printing to the console with colort

    returns the formatted report string
    '''
    report_str = '{3}{3}    {4}{0}{2} out of {5}{1}{2} pallets ran successfully in {6}.{3}'.format(pallet_reports['num_success_pallets'],
                                                                                                   len(pallet_reports['pallets']), Fore.RESET, linesep,
                                                                                                   Fore.GREEN, Fore.CYAN, pallet_reports['total_time'])

    if len(pallet_reports['git_errors']) > 0:
        for git_error in pallet_reports['git_errors']:
            report_str += '{}{}{}'.format(Fore.RED, git_error, linesep)

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
