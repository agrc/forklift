#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Usage:
  forklift update
  forklift update-specific
Options:
  --config     the path to some cfg or text file or something where we keep paths to places where there are update plugins.
               defaults to some relative or static path.
  --plugin     the name of the plugin used to filter execution. maybe a partial match or glob or exact match?
Arguments:
  <path>       an optional path to pass in so you can run a certain directory
forklift 🚜
'''

import logging.config
import sys
from docopt import docopt


def main():
    arguments = docopt(__doc__, version='1.0.0')
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
            'detailed_handler': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'detailed_formatter',
                'stream': 'ext://sys.stdout'
            }
        },
        'loggers': {
            '': {
                'handlers': ['detailed_handler'],
                'level': 'DEBUG',
            }
        }
    })

if __name__ == '__main__':
    sys.exit(main())
