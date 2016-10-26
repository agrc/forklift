#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
forklift 🚜

Usage:
    forklift config init
    forklift config set --key <key> --value <value>
    forklift config repos --add <repo>
    forklift config repos --remove <repo>
    forklift config repos --list
    forklift garage open
    forklift list-pallets
    forklift git-update
    forklift lift [<file-path>] [--pallet-arg <arg>] [--verbose]

Arguments:
    repo            The name of a GitHub repository in <owner>/<name> format.
    file-path       A path to a file that defines a pallet.
    arg             A string to be used as an optional initialization parameter to the pallet.

Examples:
    forklift config init                               Creates the config file.
    forklift config set --key <key> --value <value>    Sets a key in the config with a value.
    forklift config repos --add agrc/ugs-chemistry     Adds a path to the config. Checks for duplicates.
    forklift config repos --remove agrc/ugs-chemistry  Removes a path from the config.
    forklift config repos --list                       Outputs the list of pallet folder paths in your config file.
    forklift garage open                               Opens the garage folder with explorer.
    forklift list-pallets                              Outputs the list of pallets from the config.
    forklift git-update                                Pulls the latest updates to all git repositories.
    forklift lift                                      The main entry for running all of pallets found in the warehouse folder.
    forklift lift --verbose                            Print DEBUG statements to the console.
    forklift lift path/to/file                         Run a specific pallet.
    forklift lift path/to/file --pallet-arg arg        Run a specific pallet with "arg" as an initialization parameter.
'''

import config
import cli
import logging.config
import sys
from docopt import docopt
from logging import shutdown
from os import makedirs
from os import startfile
from os.path import abspath
from os.path import dirname
from os.path import join

log_location = join(abspath(dirname(__file__)), '..', 'forklift-garage', 'forklift.log')
detailed_formatter = logging.Formatter(fmt='%(levelname)-7s %(asctime)s %(module)10s:%(lineno)5s %(message)s',
                                       datefmt='%m-%d %H:%M:%S')


def main():
    args = docopt(__doc__, version='3.3.5')
    _setup_logging(args['--verbose'])
    _add_global_error_handler()

    if args['garage'] and args['open']:
        startfile(dirname(cli.init()))

    if args['config']:
        if args['init']:
            message = cli.init()
            print('config file: {}'.format(message))

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
    elif args['list-pallets']:
        pallets = cli.list_pallets()

        if len(pallets) == 0:
            print('No pallets found!')
        else:
            for plug in pallets:
                print(': '.join(plug))
    elif args['git-update']:
        cli.git_update()
    elif args['lift']:
        if args['<file-path>']:
            if args['--pallet-arg']:
                cli.start_lift(args['<file-path>'], args['<arg>'])
            else:
                cli.start_lift(args['<file-path>'])
        else:
            cli.start_lift()

    shutdown()


def global_exception_handler(ex_cls, ex, tb):
    import traceback

    log = logging.getLogger('forklift')

    last_traceback = (traceback.extract_tb(tb))[-1]
    line_number = last_traceback[1]
    file_name = last_traceback[0].split(".")[0]

    log.error(('global error handler line: %s (%s)' % (line_number, file_name)))
    log.error(traceback.format_exception(ex_cls, ex, tb))


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

    return log


if __name__ == '__main__':
    sys.exit(main())
