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
    forklift list-pallets
    forklift git-update
    forklift lift [<file-path>] --pallet-arg <arg>

Arguments:
    repo            The name of a GitHub repository in <owner>/<name> format.
    file-path       A path to a file that defines a pallet.
    arg             A string to set as the FORKLIFT_PALLET_ARGUMENT environment variable.

Examples:
    python -m forklift config init                               Creates the config file.
    python -m forklift config set --key <key> --value <value>    Sets a key in the config with a value.
    python -m forklift config repos --add agrc/ugs-chemistry     Adds a path to the config. Checks for duplicates.
    python -m forklift config repos --remove agrc/ugs-chemistry  Removes a path from the config.
    python -m forklift config repos --list                       Outputs the list of pallet folder paths in your config file.
    python -m forklift list-pallets                              Outputs the list of pallets from the config.
    python -m forklift git-update                                Pulls the latest updates to all git repositories.
    python -m forklift lift                                      The main entry for running all of pallets found in the warehouse folder.
    python -m forklift lift path/to/file                         Run a specific pallet.
    python -m forklift lift path/to/file --pallet-arg arg        Run a specific pallet setting "arg" as the FORKLIFT_PALLET_ARGUMENT environment variable.
'''

import cli
import logging.config
import sys
from docopt import docopt
from os import environ


detailed_formatter = logging.Formatter(fmt='%(levelname).4s %(asctime)s %(module)10s:%(lineno)5s %(message)s', datefmt='%m-%d %H:%M:%S')


def main():
    args = docopt(__doc__, version='1.0.0')
    _setup_logging()

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
            message = cli.set_config_prop(args['<key>'], args['<value>'])
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
                environ['FORKLIFT_PALLET_ARGUMENT'] = args['<arg>']
            cli.start_lift(args['<file-path>'])
        else:
            cli.start_lift()


def _setup_logging():
    log = logging.getLogger('forklift')

    log.logThreads = 0
    log.logProcesses = 0

    file_handler = logging.handlers.TimedRotatingFileHandler('forklift.log', when='D', interval=1, backupCount=7)
    file_handler.setFormatter(detailed_formatter)
    file_handler.setLevel('DEBUG')

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(detailed_formatter)
    console_handler.setLevel('INFO')

    log.addHandler(file_handler)
    log.addHandler(console_handler)
    log.setLevel('DEBUG')


if __name__ == '__main__':
    sys.exit(main())
