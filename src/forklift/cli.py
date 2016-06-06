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
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from json import dumps, loads
from models import Pallet
from os.path import abspath, exists, join, splitext, basename, dirname, isfile
from os import walk
from smtplib import SMTP
from time import clock

log = logging.getLogger('forklift')
default_pallet_locations = ['c:\\scheduled']
template = join(abspath(__file__), 'report_template.html')


def init():
    if exists('config.json'):
        return abspath('config.json')

    return _create_default_config(default_pallet_locations)


def add_config_folder(folder):
    try:
        _validate_config_folder(folder, raises=True)
    except Exception as e:
        return e.message

    return set_config_prop('paths', folder)


def remove_config_folder(folder):
    folders = _get_config_folders()

    try:
        folders.remove(folder)
    except ValueError:
        return '{} is not in the config folders list!'.format(folder)

    set_config_prop('paths', folders, override=True)

    return '{} removed'.format(folder)


def list_pallets(folders=None):
    if folders is None:
        folders = _get_config_folders()

    return _get_pallets_in_folders(folders)


def list_config_folders():
    folders = _get_config_folders()

    validate_results = []
    for folder in folders:
        validate_results.append(_validate_config_folder(folder))

    return validate_results


def get_config():
    #: write default config if the file does not exist
    if not exists('config.json'):
        return _create_default_config(default_pallet_locations)

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

    log.info('elapsed time: %s', seat.format_time(clock() - start_seconds))

    pallet_reports = lift.process_pallets(pallets)

    _send_report_email(pallet_reports)


def _send_report_email(pallet_reports):
    '''Create and send report email'''
    report_dict = {'total_pallets': len(pallet_reports),
                   'num_success_pallets': len(filter(lambda p: p['success'], pallet_reports)),
                   'pallets': pallet_reports}
    with open(template, 'r') as template_file:
        email_content = pystache.render(template_file.read(), report_dict)

    if get_config_prop('sendEmails'):
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
    else:
        print('`sendEmails` is false. No email sent. Email content:')
        print(email_content)


def _create_default_config(folders):
    with open('config.json', 'w') as json_config_file:
        data = {
            'paths': folders,
            'logLevel': 'INFO',
            'logger': '',
            'notify': ['stdavis@utah.gov', 'sgourley@utah.gov'],
            'sendEmails': False
        }

        json_config_file.write(dumps(data))

        return abspath(json_config_file.name)


def _get_config_folders():
    return get_config_prop('paths')


def _validate_config_folder(folder, raises=False):
    if exists(folder):
        message = '[Valid]'
    else:
        message = '[Folder not found]'
        if raises:
            raise Exception('{}: {}'.format(folder, message))

    return ('{}: {}'.format(folder, message))


def _get_pallets_in_folders(folders):
    pallets = []

    for folder in folders:
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

    mod = __import__(name)

    for member in dir(mod):
        try:
            potential_class = getattr(mod, member)
            if issubclass(potential_class, Pallet) and potential_class != Pallet:
                pallets.append((file_path, member))
        except:
            #: member was likely not a class
            pass

    return pallets
