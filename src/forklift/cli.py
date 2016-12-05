#!/usr/bin/env python
# * coding: utf8 *
'''
lift.py

A module that contains the implementation of the cli commands
'''

import config
import core
import lift
import logging
import pystache
import seat
import sys
from colorama import init as colorama_init, Fore
from messaging import send_email
from git import Repo
from imp import load_source
from models import Pallet
from os.path import abspath, basename, dirname, exists, join, splitext, realpath
from os import walk
from os import linesep
from re import compile
from requests import get
from time import clock

log = logging.getLogger('forklift')
template = join(abspath(dirname(__file__)), 'report_template.html')
speedtest_destination = join(dirname(realpath(__file__)), '..', '..', 'speedtest', 'data')
colorama_init()

pallet_file_regex = compile(ur'pallet.*\.py$')


def init():
    if exists(config.config_location):
        return abspath(config.config_location)

    return config.create_default_config()


def add_repo(repo):
    try:
        _validate_repo(repo, raises=True)
    except Exception as e:
        return e.message

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


def start_lift(file_path=None, pallet_arg=None):
    log.info('starting forklift')

    git_errors = git_update()

    start_seconds = clock()

    if file_path is not None:
        pallet_infos = set(_get_pallets_in_file(file_path) + list_pallets())
    else:
        pallet_infos = list_pallets()

    all_pallets = []
    pallets_to_lift = []
    for pallet_location, PalletClass in pallet_infos:
        try:
            if pallet_arg is not None:
                pallet = PalletClass(pallet_arg)
            else:
                pallet = PalletClass()

            all_pallets.append(pallet)
            if pallet_location == file_path or file_path is None:
                pallets_to_lift.append(pallet)
        except Exception as e:
            log.error('error creating pallet class: %s. %s', PalletClass.__name__, e.message, exc_info=True)

    pallets_to_lift.sort(key=lambda p: p.__class__.__name__)

    start_process = clock()
    core.init()
    lift.process_crates_for(pallets_to_lift, core.update, config.get_config_prop('configuration'))
    log.info('process_crates time: %s', seat.format_time(clock() - start_process))

    start_process = clock()
    lift.process_pallets(pallets_to_lift)
    log.info('process_pallets time: %s', seat.format_time(clock() - start_process))

    start_copy = clock()
    copy_results = lift.copy_data(pallets_to_lift, all_pallets, config.get_config_prop('copyDestinations'))
    log.info('copy_data time: %s', seat.format_time(clock() - start_copy))

    start_post_copy_process = clock()
    lift.process_pallets(pallets_to_lift, is_post_copy=True)
    log.info('post_copy_process time: %s', seat.format_time(clock() - start_post_copy_process))

    elapsed_time = seat.format_time(clock() - start_seconds)
    report_object = lift.create_report_object(pallets_to_lift, elapsed_time, copy_results, git_errors)

    _send_report_email(report_object)

    log.info('Finished in {}.'.format(elapsed_time))

    log.info('%s', _format_dictionary(report_object))


def _send_report_email(report_object):
    '''Create and send report email
    '''
    log_file = join(dirname(config.config_location), 'forklift.log')

    with open(template, 'r') as template_file:
        email_content = pystache.render(template_file.read(), report_object)

    send_email(config.get_config_prop('notify'), 'Forklift Report', email_content, log_file)


def git_update():
    warehouse = config.get_config_prop('warehouse')
    errors = []
    for repo_name in config.get_config_prop('repositories'):
        try:
            folder = join(warehouse, repo_name.split('/')[1])
            if not exists(folder):
                log.info('git cloning: {}'.format(repo_name))
                Repo.clone_from(_repo_to_url(repo_name), join(warehouse, folder))
            else:
                log.info('git updating: {}'.format(repo_name))
                repo = _get_repo(folder)
                origin = repo.remotes[0]
                fetch_infos = origin.pull()

                if len(fetch_infos) > 0:
                    if fetch_infos[0].flags == 4:
                        log.debug('no updates to pallet')
                    elif fetch_infos[0].flags in [32, 64]:
                        log.info('updated to %s', fetch_infos[0].commit.name_rev)
        except Exception as e:
            errors.append('Git update error for {}: {}'.format(repo_name, e))

    return errors


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
        log.error('%s failed to import: %s', file_path, e.message, exc_info=True)
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

    if len(pallet_reports['git_errors']) > 0:
        for git_error in pallet_reports['git_errors']:
            report_str += '{}{}{}'.format(Fore.RED, git_error, linesep)

    for report in pallet_reports['pallets']:
        color = Fore.GREEN
        if not report['success']:
            color = Fore.RED

        report_str += '{}{}{}{}'.format(color, report['name'], Fore.RESET, linesep)

        if report['message'] is not None:
            report_str += 'pallet message: {}{}{}{}'.format(Fore.YELLOW, report['message'], Fore.RESET, linesep)

        for crate in report['crates']:
            report_str += '{0:>40}{3} - {1}{4}{2}'.format(crate['name'], crate['result'], linesep, Fore.CYAN, Fore.RESET)

            if crate['crate_message'] is None:
                continue

            report_str += 'crate message: {0}{1}{2}{3}'.format(Fore.MAGENTA, crate['crate_message'], Fore.RESET, linesep)

    return report_str


def speedtest(pallet_location):
    print('{0}{1}Setting up speed test...{0}'.format(Fore.RESET, Fore.MAGENTA))

    #: remove logging
    log.handlers = [logging.NullHandler()]

    #: spoof hashes location so there is no caching
    core.garage = speedtest_destination
    core.hash_gdb_path = join(core.garage, core._hash_gdb)

    #: delete destination and other artifacts form prior runs
    import arcpy
    if arcpy.Exists(join(speedtest_destination, 'DestinationData.gdb')):
        arcpy.Delete_management(join(speedtest_destination, 'DestinationData.gdb'))
        arcpy.CreateFileGDB_management(speedtest_destination, 'DestinationData.gdb')
    else:
        arcpy.CreateFileGDB_management(speedtest_destination, 'DestinationData.gdb')

    if arcpy.Exists(core.hash_gdb_path):
        arcpy.Delete_management(core.hash_gdb_path)

    print('{0}{1}Tests ready starting dry run...{0}'.format(Fore.RESET, Fore.MAGENTA))

    start_seconds = clock()
    start_lift(pallet_location)
    dry_run = seat.format_time(clock() - start_seconds)

    print('{0}{1}Repeating test...{0}'.format(Fore.RESET, Fore.MAGENTA))
    start_seconds = clock()
    start_lift(pallet_location)
    repeat = seat.format_time(clock() - start_seconds)

    #: clean up so git state is unchanged
    if arcpy.Exists(join(speedtest_destination, 'DestinationData.gdb')):
        arcpy.Delete_management(join(speedtest_destination, 'DestinationData.gdb'))
    if arcpy.Exists(core.hash_gdb_path):
        arcpy.Delete_management(core.hash_gdb_path)

    print('{3}{0}{1}Speed Test Results{3}{0}{2}Dry Run:{0} {4}{3}{2}Repeat:{0} {5}'.format(Fore.RESET, Fore.GREEN, Fore.CYAN, linesep, dry_run, repeat))
