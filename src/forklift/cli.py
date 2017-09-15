#!/usr/bin/env python
# * coding: utf8 *
'''
lift.py

A module that contains the implementation of the cli commands
'''

import logging
import sys
from imp import load_source
from os import environ, linesep, makedirs, walk
from os.path import (abspath, basename, dirname, exists, join, realpath,
                     splitext)
from re import compile
from shutil import rmtree
from time import clock

from colorama import init as colorama_init
from colorama import Fore
from multiprocess import Pool

import pystache
from git import Repo
from requests import get

from . import config, core, lift, seat
from .messaging import send_email
from .models import Pallet

log = logging.getLogger('forklift')
template = join(abspath(dirname(__file__)), 'report_template.html')
speedtest_destination = join(dirname(realpath(__file__)), '..', '..', 'speedtest', 'data')
colorama_init()

pallet_file_regex = compile(r'pallet.*\.py$')


def init():
    if exists(config.config_location):
        return abspath(config.config_location)

    return config.create_default_config()


def add_repo(repo):
    try:
        _validate_repo(repo, raises=True)
    except Exception as e:
        return e

    return config.set_config_prop('repositories', repo)


def remove_repo(repo):
    repos = _get_repos()

    try:
        repos.remove(repo)
    except ValueError:
        return '{} is not in the repositories list!'.format(repo)

    config.set_config_prop('repositories', repos, override=True)

    return '{} removed'.format(repo)


def list_pallets():
    return _get_pallets_in_folder(config.get_config_prop('warehouse'))


def list_repos():
    folders = _get_repos()

    validate_results = []
    for folder in folders:
        validate_results.append(_validate_repo(folder))

    return validate_results


def start_lift(file_path=None, pallet_arg=None, skip_git=False):
    log.info('starting forklift')

    if not skip_git:
        git_errors = git_update()
    else:
        git_errors = []

    start_seconds = clock()

    pallets_to_lift, all_pallets = _sort_pallets(file_path, pallet_arg)

    start_process = clock()
    core.init(log)
    lift.process_crates_for(pallets_to_lift, core.update)
    log.info('process_crates time: %s', seat.format_time(clock() - start_process))

    start_process = clock()
    lift.process_pallets(pallets_to_lift)
    log.info('process_pallets time: %s', seat.format_time(clock() - start_process))

    start_copy = clock()
    copy_destinations = config.get_config_prop('copyDestinations')
    copy_results = lift.copy_data(pallets_to_lift, all_pallets, copy_destinations)
    log.info('copy_data time: %s', seat.format_time(clock() - start_copy))

    start_post_copy_process = clock()
    lift.process_pallets(pallets_to_lift, is_post_copy=True)
    log.info('post_copy_process time: %s', seat.format_time(clock() - start_post_copy_process))

    if len(copy_destinations) == 0:
        log.info('No `copyDestinations` defined in the config. Skipping update_static...')
        static_copy_results = ''
    else:
        start_static = clock()
        static_copy_results = lift.update_static_for(pallets_to_lift, copy_destinations, False)
        log.info('static copy time: %s', seat.format_time(clock() - start_static))

    elapsed_time = seat.format_time(clock() - start_seconds)
    report_object = lift.create_report_object(pallets_to_lift, elapsed_time, copy_results, git_errors, static_copy_results)

    _send_report_email(report_object)

    log.info('Finished in {}.'.format(elapsed_time))

    report = _format_dictionary(report_object)
    log.info('%s', report)

    return report


def _sort_pallets(file_path, pallet_arg):
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


def _send_report_email(report_object):
    '''Create and send report email
    '''
    log_file = join(dirname(config.config_location), 'forklift.log')

    with open(template, 'r') as template_file:
        email_content = pystache.render(template_file.read(), report_object)

    send_email(config.get_config_prop('notify'), 'Forklift Report for {}'.format(report_object['hostname']), email_content, log_file)


def _clone_or_pull_repo(repo_name):
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


def git_update():
    log.info('git updating (in parallel)...')
    num_processes = environ.get('FORKLIFT_POOL_PROCESSES')
    pool = Pool(num_processes or config.default_num_processes)

    results = pool.map(_clone_or_pull_repo, config.get_config_prop('repositories'))

    for error, info in results:
        if info is not None:
            log.info(info)
        if error is not None:
            log.error(error)

    return [error for error, info in results if error is not None]


def _get_repo(folder):
    #: abstraction to enable mocking in tests
    return Repo(folder)


def _repo_to_url(repo):
    return 'https://github.com/{}.git'.format(repo)


def _get_repos():
    return config.get_config_prop('repositories')


def _validate_repo(repo, raises=False):
    url = _repo_to_url(repo)
    response = get(url)
    if response.status_code == 200:
        message = '[Valid]'
    else:
        message = '[Invalid repo name or owner]'
        if raises:
            raise Exception('{}: {}'.format(repo, message))

    return ('{}: {}'.format(repo, message))


def _get_pallets_in_folder(folder):
    pallets = []

    for root, dirs, files in walk(folder):
        for file_name in files:
            if pallet_file_regex.search(file_name.lower()):
                pallets.extend(_get_pallets_in_file(join(root, file_name)))
    return pallets


def _get_pallets_in_file(file_path):
    pallets = []
    name = splitext(basename(file_path))[0]
    folder = dirname(file_path)

    if folder not in sys.path:
        sys.path.append(folder)

    try:
        try:
            mod = sys.modules[name]
        except KeyError:
            mod = load_source(name, file_path)
    except Exception as e:
        # skip modules that fail to import
        log.error('%s failed to import: %s', file_path, e, exc_info=True)
        return []

    for member in dir(mod):
        try:
            potential_class = getattr(mod, member)
            if issubclass(potential_class, Pallet) and potential_class != Pallet:
                pallets.append((file_path, potential_class))
        except:
            #: member was likely not a class
            pass

    return pallets


def _format_dictionary(pallet_reports):
    report_str = '{3}{3}    {4}{0}{2} out of {5}{1}{2} pallets ran successfully in {6}.{3}'.format(
        pallet_reports['num_success_pallets'], len(pallet_reports['pallets']), Fore.RESET, linesep, Fore.GREEN,
        Fore.CYAN, pallet_reports['total_time'])

    if pallet_reports['copy_results'] not in [None, '']:
        report_str += '{}{}{}{}'.format(Fore.RED, pallet_reports['copy_results'], Fore.RESET, linesep)

    if pallet_reports['static_copy_results'] not in [None, '']:
        report_str += '{}{}{}{}'.format(Fore.RED, pallet_reports['static_copy_results'], Fore.RESET, linesep)

    if len(pallet_reports['git_errors']) > 0:
        for git_error in pallet_reports['git_errors']:
            report_str += '{}{}{}'.format(Fore.RED, git_error, linesep)

    for report in pallet_reports['pallets']:
        color = Fore.GREEN
        if not report['success']:
            color = Fore.RED

        report_str += '{3}{0}{1}{2}{3}'.format(color, report['name'], Fore.RESET, linesep)

        if report['message']:
            report_str += 'pallet message: {}{}{}{}'.format(Fore.RED, report['message'], Fore.RESET, linesep)

        for crate in report['crates']:
            report_str += '{0:>40} - {1}{3}{2}'.format(crate['name'], crate['result'], linesep, Fore.RESET)

            if crate['crate_message'] is None:
                continue

            if crate['message_level'] == 'warning':
                color = Fore.YELLOW
            else:
                color = Fore.RED
            report_str += 'crate message: {0}{1}{2}{3}'.format(color, crate['crate_message'], Fore.RESET, linesep)

    return report_str


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


def speedtest(pallet_location):
    print(('{0}{1}Setting up speed test...{0}'.format(Fore.RESET, Fore.MAGENTA)))

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

    arcpy.Copy_management(join(speedtest_destination, 'SourceData.gdb'),
                          join(speedtest_destination, 'ChangeSourceData.gdb'))
    _prep_change_data(join(speedtest_destination, 'ChangeSourceData.gdb', 'AddressPoints'))

    if arcpy.Exists(core.scratch_gdb_path):
        arcpy.Delete_management(core.scratch_gdb_path)

    print(('{0}{1}Tests ready starting dry run...{0}'.format(Fore.RESET, Fore.MAGENTA)))

    start_seconds = clock()
    dry_report = start_lift(pallet_location, skip_git=True)
    dry_run = seat.format_time(clock() - start_seconds)

    print(('{0}{1}Changing data...{0}'.format(Fore.RESET, Fore.MAGENTA)))
    _change_data(join(speedtest_destination, 'ChangeSourceData.gdb', 'AddressPoints'))

    print(('{0}{1}Repeating test...{0}'.format(Fore.RESET, Fore.MAGENTA)))
    start_seconds = clock()
    repeat_report = start_lift(pallet_location, skip_git=True)
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


def update_static(file_path):
    log.info('updating/creating static data for pallet(s) in %s', file_path)

    start_seconds = clock()

    git_errors = git_update()

    pallets = [PalletClass() for location, PalletClass in _get_pallets_in_file(file_path)]
    for pallet in pallets:
        pallet.build(config.get_config_prop('configuration'))

    copy_destinations = config.get_config_prop('copyDestinations')
    if len(copy_destinations) == 0:
        log.error('No `copyDestinations` defined in the config!')
        return ''

    static_copy_results = lift.update_static_for(pallets, copy_destinations, True)

    elapsed_time = seat.format_time(clock() - start_seconds)
    report_object = lift.create_report_object(pallets, elapsed_time, '', git_errors, static_copy_results)
    report = _format_dictionary(report_object)
    log.info('%s', report)

    return report


def scorched_earth():
    staging = config.get_config_prop('stagingDestination')
    for folder in [staging, core.scratch_gdb_path]:
        if exists(folder):
            log.info('deleting: %s', folder)
            rmtree(folder)

    log.info('recreating: %s', staging)
    makedirs(staging)
