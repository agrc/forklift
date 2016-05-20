#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
forklift 🚜

Usage:
    forklift config --init
    forklift config --add <folder-path>
    forklift config --validate
    forklift config --list
    forklift list [<folder-path>]
    forklift update [<file-path>]
Arguments:
    folder-path     a path to a folder
    file-path       a path to a file
Examples:
    config --init:                  creates the config file.
    config --add path/to/folder:    adds a path to the config. checks for duplicates and accessibility.
    config --list:                  outputs the list of plugin folder paths in your config file.
    config --validate:              validates all config paths are reachable.
    list:                           outputs the list of plugins from the config.
    list path/to/folder:            outputs the list of plugins for the passed in path.
    update:                         the main entry for running all of plugins found in the config paths.
    update path/to/file:            run a specific plugin.
'''

import lift
import logging.config
import sys
from docopt import docopt


def main():
    args = docopt(__doc__, version='1.0.0')
    _setup_logging()

    if args['config'] and args['--init']:
        file_created = lift.init()
        print('config file created: {}'.format(file_created))
    elif args['config'] and args['--add'] and args['<folder-path>']:
        lift.add_plugin_folder(args['<folder-path>'])
        print('{} added to config file'.format(args['<folder-path>']))
    elif args['list'] and args['--plugins']:
        plugins = lift.list_plugins(args['<path>'])
        for plug in plugins:
            print(': '.join(plug))


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
