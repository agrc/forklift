#!/usr/bin/env python
# * coding: utf8 *
'''
lift.py

A module that contains the implementation of the cli commands
'''

import core
import lift
import logging
import pystache
import seat
import secrets
import sys
from colorama import init, Fore, Back, Style
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from git import Repo
from importlib import import_module
from json import dumps, loads
from models import Pallet
from os.path import abspath, exists, join, splitext, basename, dirname, isfile
from os import walk
from os import linesep
from requests import get
from smtplib import SMTP
from time import clock

log = logging.getLogger('forklift')
template = join(abspath(dirname(__file__)), 'report_template.html')
default_warehouse_location = 'c:\\scheduled'
init()


def init():
    if exists('config.json'):
        return abspath('config.json')

    return _create_default_config(default_warehouse_location)


def add_repo(repo):
    try:
        _validate_repo(repo, raises=True)
    except Exception as e:
        return e.message

    return set_config_prop('repositories', repo)


def remove_repo(repo):
    repos = _get_repos()

    try:
        repos.remove(repo)
    except ValueError:
        return '{} is not in the repositories list!'.format(repo)

    set_config_prop('repositories', repos, override=True)

    return '{} removed'.format(repo)


def list_pallets():
    return _get_pallets_in_folder(get_config_prop('warehouse'))


def list_repos():
    folders = _get_repos()

    validate_results = []
    for folder in folders:
        validate_results.append(_validate_repo(folder))

    return validate_results


def get_config():
    #: write default config if the file does not exist
    if not exists('config.json'):
        return _create_default_config(default_warehouse_location)

    with open('config.json', 'r') as json_config_file:
        return loads(json_config_file.read())


def get_config_prop(key):
    return get_config()[key]


def set_config_prop(key, value, override=False):
    config = get_config()

    if key not in config:
        return '{} not found in config.'.format(key)

    if not override:
        try:
            if not isinstance(value, list):
                if value not in config[key]:
                    config[key].append(value)
                else:
                    return '{} already contains {}'.format(key, value)
            else:
                for item in value:
                    if item not in config[key]:
                        config[key].append(item)
        except AttributeError:
            #: prop is not an array set value instead of append
            config[key] = value
    else:
        config[key] = value

    with open('config.json', 'w') as json_config_file:
        json_config_file.write(dumps(config))

    return 'Added {} to {}'.format(value, key)


def start_lift(file_path=None):
    log.info('starting forklift')

    git_update()

    start_seconds = clock()

    if file_path is not None:
        pallet_infos = _get_pallets_in_file(file_path)
    else:
        pallet_infos = list_pallets()

    pallets = []
    for info in pallet_infos:
        module_name = splitext(basename(info[0]))[0]
        class_name = info[1]
        PalletClass = getattr(__import__(module_name), class_name)
        pallets.append(PalletClass())

    lift.process_crates_for(pallets, core.update)

    elapsed_time = seat.format_time(clock() - start_seconds)
    log.info('elapsed time: %s', elapsed_time)

    pallet_reports = lift.process_pallets(pallets)
    report_object = lift.create_report_object(pallet_reports, elapsed_time)

    email = get_config_prop('sendEmails')
    if email:
        _send_report_email(report_object)

    print('Finished in %s. General email notification: %s', elapsed_time, email)

    def format_dictionary(pallet_reports):
        str = '{7}{8}{0}{1}{2}{9}{3}{4} out of {5} pallets ran successfully.{6}{3}{7}'.format(
            Fore.GREEN, Back.WHITE, pallet_reports['num_success_pallets'], Fore.RESET, Fore.BLACK,
            len(pallet_reports['pallets']), Back.RESET, linesep, Style.DIM, Style.NORMAL)

        for report in pallet_reports['pallets']:
            color = Fore.GREEN
            if not report['success']:
                color = Fore.RED

            str += '{}{}{}{}'.format(color, report['name'], Fore.RESET, linesep)

            if not report['success']:
                str += '  pallet message: {}{}{}{}'.format(Fore.YELLOW, report['message'], Fore.RESET, linesep)

            for crate in report['crates']:
                str += '    {0:40}{1}{2}'.format(crate['name'], crate['crate_message'], linesep)

        return str

    log.info('%s', format_dictionary(report_object))


def _send_report_email(report_object):
    '''Create and send report email
    '''
    with open(template, 'r') as template_file:
        email_content = pystache.render(template_file.read(), report_object)

    to_addresses = ','.join(get_config_prop('notify'))
    message = MIMEMultipart()
    message['Subject'] = 'Forklift report'
    message['From'] = secrets.from_address
    message['To'] = to_addresses
    message.attach(MIMEText(email_content, 'html'))

    log_file = 'forklift.log'
    if isfile(log_file):
        message.attach(MIMEText(file(log_file).read()))

    smtp = SMTP(secrets.smtp_server, secrets.smtp_port)
    smtp.sendmail(secrets.from_address, to_addresses, message.as_string())
    smtp.quit()


def git_update():
    warehouse = get_config_prop('warehouse')
    for repo_name in get_config_prop('repositories'):
        folder = join(warehouse, repo_name.split('/')[1])
        if not exists(folder):
            log.info('git cloning: {}'.format(repo_name))
            Repo.clone_from(_repo_to_url(repo_name), join(warehouse, folder))
        else:
            log.info('git updating: {}'.format(repo_name))
            repo = _get_repo(folder)
            origin = repo.remotes[0]
            origin.pull()


def _get_repo(folder):
    #: abstraction to enable mocking in tests
    return Repo(folder)


def _repo_to_url(repo):
    return 'https://github.com/{}.git'.format(repo)


def _create_default_config(folder):
    with open('config.json', 'w') as json_config_file:
        data = {
            'warehouse': folder,
            'repositories': [],
            'notify': ['stdavis@utah.gov', 'sgourley@utah.gov'],
            'sendEmails': False
        }

        json_config_file.write(dumps(data))

        return abspath(json_config_file.name)


def _get_repos():
    return get_config_prop('repositories')


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
            if file_name.endswith('.py'):
                pallets.extend(_get_pallets_in_file(join(root, file_name)))
    return pallets


def _get_pallets_in_file(file_path):
    pallets = []
    name = splitext(basename(file_path))[0]
    folder = dirname(file_path)

    if folder not in sys.path:
        sys.path.append(folder)

    try:
        mod = import_module(name)
    except:
        # skip modules that fail to import
        return []

    for member in dir(mod):
        try:
            potential_class = getattr(mod, member)
            if issubclass(potential_class, Pallet) and potential_class != Pallet:
                pallets.append((file_path, member))
        except:
            #: member was likely not a class
            pass

    return pallets
