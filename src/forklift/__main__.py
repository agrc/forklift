#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
forklift

Usage:
    forklift config init
    forklift config repos --add <repo>
    forklift config repos --list
    forklift config repos --remove <repo>
    forklift config set --key <key> --value <value>
    forklift garage open
    forklift git-update
    forklift lift [<file-path>] [--pallet-arg <arg>] [--skip-copy] [--verbose]
    forklift list-pallets
    forklift scorched-earth
    forklift speedtest
    forklift update-static <file-path>

Arguments:
    repo            The name of a GitHub repository in <owner>/<name> format.
    file-path       A path to a file that defines one or multiple pallets.
    pallet-arg      A string to be used as an optional initialization parameter to the pallet.

Examples:
    forklift config init                                    Creates the config file.
    forklift config repos --add agrc/ugs-chemistry          Adds a path to the config. Checks for duplicates.
    forklift config repos --list                            Outputs the list of pallet folder paths in your config file.
    forklift config repos --remove agrc/ugs-chemistry       Removes a path from the config.
    forklift config set --key <key> --value <value>         Sets a key in the config with a value.
    forklift garage open                                    Opens the garage folder with explorer.
    forklift git-update                                     Pulls the latest updates to all git repositories.
    forklift lift                                           The main entry for running all of pallets found in the warehouse folder.
    forklift lift --verbose                                 Print DEBUG statements to the console.
    forklift lift --skip-copy                               Skip copying to `copyDestinations`.
    forklift lift path/to/pallet_file.py                    Run a specific pallet.
    forklift lift path/to/pallet_file.py --pallet-arg arg   Run a specific pallet with "arg" as an initialization parameter.
    forklift list-pallets                                   Outputs the list of pallets from the config.
    forklift scorched-earth                                 WARNING!!! Deletes all data in `config.stagingDestination` as well as the
                                                            `hashes.gdb` & `scratch.gdb` file geodatabases.
    forklift speedtest                                      Test the speed on a predefined pallet.
    forklift update-static path/to/pallet_file.py           Updates the static data defined in the specified pallet.
'''

import faulthandler
import logging.config
import sys
from logging import shutdown
from os import linesep, makedirs, startfile
from os.path import abspath, dirname, join, realpath

from docopt import docopt

from . import cli, config
from .messaging import send_email

log_location = join(abspath(dirname(__file__)), '..', 'forklift-garage', 'forklift.log')
detailed_formatter = logging.Formatter(fmt='%(levelname)-7s %(asctime)s %(module)10s:%(lineno)5s %(message)s',
                                       datefmt='%m-%d %H:%M:%S')
speedtest = join(dirname(realpath(__file__)), '..', '..', 'speedtest', 'SpeedTestPallet.py')


def main():
    if sys.version_info.major != 3:
        log = logging.getLogger('forklift')
        print('please activate the conda package and run on python3')
        log.error('activate the python 3 proenv to use forklift')

        return

    args = docopt(__doc__, version='8.4.1')
    _setup_logging(args['--verbose'])
    _add_global_error_handler()

    if args['config']:
        if args['init']:
            message = cli.init()
            print(('config file: {}'.format(message)))

        if args['repos'] and args['<repo>']:
            if args['--add']:
                message = cli.add_repo(args['<repo>'])

            if args['--remove']:
                message = cli.remove_repo(args['<repo>'])

            print(message)

        if args['set'] and args['<key>'] and args['<value>']:
            message = config.set_config_prop(args['<key>'], args['<value>'])
            print(message)

        if args['repos'] and args['--list']:
            for folder in cli.list_repos():
                print(folder)
    elif args['garage'] and args['open']:
        startfile(dirname(cli.init()))
    elif args['git-update']:
        cli.git_update()
    elif args['lift']:
        if args['<file-path>']:
            if args['--pallet-arg']:
                cli.start_lift(args['<file-path>'], args['<arg>'], skip_copy=args['--skip-copy'])
            else:
                cli.start_lift(args['<file-path>'], skip_copy=args['--skip-copy'])
        else:
            cli.start_lift(skip_copy=args['--skip-copy'])
    elif args['list-pallets']:
        pallets = cli.list_pallets()

        if len(pallets) == 0:
            print('No pallets found!')
        else:
            for path, pallet_class in pallets:
                print((': '.join([path, str(pallet_class)])))
    elif args['scorched-earth']:
        cli.scorched_earth()
    elif args['speedtest']:
        cli.speedtest(speedtest)
    elif args['update-static']:
        cli.update_static(args['<file-path>'])

    shutdown()


def global_exception_handler(ex_cls, ex, tb):
    import traceback

    log = logging.getLogger('forklift')

    last_traceback = (traceback.extract_tb(tb))[-1]
    line_number = last_traceback[1]
    file_name = last_traceback[0].split(".")[0]
    error = linesep.join(traceback.format_exception(ex_cls, ex, tb))

    log.error(('global error handler line: %s (%s)' % (line_number, file_name)))
    log.error(error)

    log_file = join(dirname(config.config_location), 'forklift.log')
    send_email(config.get_config_prop('notify'), 'Forklift Error', error, log_file)


def _add_global_error_handler():
    sys.excepthook = global_exception_handler


def _setup_logging(verbose):
    log = logging.getLogger('forklift')

    log.logThreads = 0
    log.logProcesses = 0

    debug = 'DEBUG'
    info = 'INFO'

    if verbose:
        info = debug

    try:
        makedirs(dirname(log_location))
    except:
        pass

    file_handler = logging.handlers.RotatingFileHandler(log_location, backupCount=18)
    file_handler.doRollover()
    file_handler.setFormatter(detailed_formatter)
    file_handler.setLevel(debug)

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(detailed_formatter)
    console_handler.setLevel(info)

    log.addHandler(file_handler)
    log.addHandler(console_handler)
    log.setLevel(debug)

    faulthandler.enable(file_handler.stream)

    return log


if __name__ == '__main__':
    sys.exit(main())
