#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Usage:
  forklift config --init
  forklift list (--plugins | --config) [path]
  forklift config --add <path>
  forklift config --validate
  forklift update
  forklift update-specific <path>
Arguments:
  <path>   a file path

forklift 🚜

Examples:
    list: outputs the list of plugins from the config or the config paths. specify a path to get a list of plugins
        in that location.
    config init: creates the config file.
    config add: adds a path to the config. checks for duplicates and accessibility.
    config validate: validates all config paths are reachable.
    update: the main entry for running all of plugins found in the config paths.
    update-specific: run a specific plugin.
'''

import lift
import logging.config
import sys
from docopt import docopt


def main():
    arguments = docopt(__doc__, version='1.0.0', options_first=True)
    _setup_logging()

    if arguments['update']:
        pass
    elif arguments['update-specific']:
        pass


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
