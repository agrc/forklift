#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Usage:
  forklift update
  forklift update-specific <path>
Options:
  --config     the path to some cfg or text file or something where we keep paths to places where there are update plugins.
               defaults to some relative or static path.
  --plugin     the name of the plugin used to filter execution. maybe a partial match or glob or exact match?
Arguments:
  <path>       an optional path to pass in so you can run a certain directory
🚜 forklift 🚜
'''

import sys
from docopt import docopt


def main():
    arguments = docopt(__doc__, version='1.0.0')

    if arguments['update']:
        pass
    elif arguments['update-specific']:
        pass

if __name__ == '__main__':
    sys.exit(main())
