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
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from git import Repo
from imp import load_source
from models import Pallet
from os.path import abspath, exists, join, splitext, basename, dirname, isfile
from os import walk
from os import linesep
from re import compile
from requests import get
from time import clock

log = logging.getLogger('forklift')
template = join(abspath(dirname(__file__)), 'report_template.html')
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

    git_update()

    start_seconds = clock()

    if file_path is not None:
        pallet_infos = set(_get_pallets_in_file(file_path) + list_pallets())
    else:
        pallet_infos = list_pallets()

    all_pallets = []
    pallets_to_lift = []
    for info in pallet_infos:
        PalletClass = info[1]

        try:
            if pallet_arg is not None:
                pallet = PalletClass(pallet_arg)
            else:
                pallet = PalletClass()

            all_pallets.append(pallet)
            if info[0] == file_path or file_path is None:
                pallets_to_lift.append(pallet)
        except Exception as e:
            log.error('error creating pallet class: %s. %s', class_name, e.message, exc_info=True)

    start_process = clock()
    lift.process_crates_for(pallets_to_lift, core.update, config.get_config_prop('configuration'))
    log.info('process_crates time: %s', seat.format_time(clock() - start_process))

    start_process = clock()
    lift.process_pallets(pallets_to_lift)
    log.info('process_pallets time: %s', seat.format_time(clock() - start_process))

    start_copy = clock()
    lift.copy_data(pallets_to_lift, all_pallets, config.get_config_prop('copyDestinations'))
    log.info('copy_data time: %s', seat.format_time(clock() - start_copy))

    elapsed_time = seat.format_time(clock() - start_seconds)
    report_object = lift.create_report_object(pallets_to_lift, elapsed_time)

    _send_report_email(report_object)

    print('Finished in {}.'.format(elapsed_time))

    log.info('%s', _format_dictionary(report_object))


def _send_report_email(report_object):
    '''Create and send report email
    '''
    with open(template, 'r') as template_file:
        email_content = pystache.render(template_file.read(), report_object)

    message = MIMEMultipart()
    message.attach(MIMEText(email_content, 'html'))

    log_file = join(dirname(config.config_location), 'forklift.log')
    if isfile(log_file):
        message.attach(MIMEText(file(log_file).read()))

    send_email(config.get_config_prop('notify'), 'Forklift Report', message)


def git_update():
    warehouse = config.get_config_prop('warehouse')
    for repo_name in config.get_config_prop('repositories'):
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
        if name in sys.modules.keys():
            del(sys.modules[name])

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
    str = '{3}{3}    {4}{0}{2} out of {5}{1}{2} pallets ran successfully in {6}.{3}'.format(
        pallet_reports['num_success_pallets'], len(pallet_reports['pallets']), Fore.RESET, linesep, Fore.GREEN,
        Fore.CYAN, pallet_reports['total_time'])

    for report in pallet_reports['pallets']:
        color = Fore.GREEN
        if not report['success']:
            color = Fore.RED

        str += '{}{}{}{}'.format(color, report['name'], Fore.RESET, linesep)

        if report['message'] is not None:
            str += 'pallet message: {}{}{}{}'.format(Fore.YELLOW, report['message'], Fore.RESET, linesep)

        for crate in report['crates']:
            str += '{0:>40}{3} - {1}{4}{2}'.format(crate['name'], crate['result'], linesep, Fore.CYAN, Fore.RESET)

            if crate['crate_message'] is None:
                continue

            str += 'crate message: {0}{1}{2}{3}'.format(Fore.MAGENTA, crate['crate_message'], Fore.RESET, linesep)

    return str
