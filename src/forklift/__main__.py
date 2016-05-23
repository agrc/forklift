#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
forklift 🚜

Usage:
    forklift config --init
    forklift config --add <folder-path>
    forklift config --remove <folder-path>
    forklift config --list
    forklift list-pallets [<folder-path>]
    forklift lift [<file-path>]

Arguments:
    folder-path     a path to a folder
    file-path       a path to a file

Examples:
    config --init                  creates the config file.
    config --add path/to/folder    adds a path to the config. Checks for duplicates.
    config --remove path/to/folder removes a path from the config.
    config --list                  outputs the list of pallet folder paths in your config file.
    list-pallets                           outputs the list of pallets from the config.
    list-pallets path/to/folder            outputs the list of pallets for the passed in path.
    lift                           the main entry for running all of pallets found in the config paths.
    lift path/to/file              run a specific pallet.
'''

import cli
import logging.config
import sys
from docopt import docopt


def main():
    args = docopt(__doc__, version='1.0.0')
    _setup_logging()

    if args['config']:
        if args['--init']:
            message = cli.init()
            print('config file created: {}'.format(message))

        if args['--add'] and args['<folder-path>']:
            message = cli.add_config_folder(args['<folder-path>'])
            print(message)

        if args['--remove'] and args['<folder-path>']:
            message = cli.remove_config_folder(args['<folder-path>'])
            print(message)

        if args['--list']:
            for folder in cli.list_config_folders():
                print(folder)
    elif args['list-pallets']:
        if args['<folder-path>']:
            pallets = cli.list_pallets(args['<path>'])
        else:
            pallets = cli.list_pallets()

        if len(pallets) == 0:
            print('No pallets found!')
        else:
            for plug in pallets:
                print(': '.join(plug))
    elif args['lift']:
        if args['<file-path>']:
            cli.start_lift(args['<file-path>'])
        else:
            cli.start_lift()


def _setup_logging():
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed_formatter': {
                'format': '%(levelname).4s %(asctime)s %(module)s:%(lineno)-4s %(message)s',
                'datefmt': '%m-%d %H:%M:%S'
            },
            'plain_formatter': {
                'format': '%(message)s'
            }
        },
        'handlers': {
            'detailed_console_handler': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'detailed_formatter',
                'stream': 'ext://sys.stdout'
            },
            'detailed_file_handler': {
                'level': 'DEBUG',
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'filename': 'forklift.log',
                'when': 'D',
                'interval': 1,
                'backupCount': 7,
                'formatter': 'detailed_formatter'
            }
        },
        'loggers': {
            'console': {
                'handlers': ['detailed_console_handler'],
                'level': 'DEBUG',
            },
            'file': {
                'handlers': ['detailed_file_handler'],
                'level': 'INFO'
            }
        }
    })

if __name__ == '__main__':
    sys.exit(main())
