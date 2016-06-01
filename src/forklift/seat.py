#!/usr/bin/env python
# * coding: utf8 *
'''
seat.py

A module that contains helpful methods for other modules
'''


def format_time(seconds):
    minute = 60.00
    hour = 60.00 * minute

    if seconds < 30:
        return '{} ms'.format(int(seconds * 1000))

    if seconds < 90:
        return '{} seconds'.format(seconds)

    if seconds < 90 * minute:
        return '{} minutes'.format(round(seconds / minute, 2))

    else:
        return '{} hours'.format(round(seconds / hour, 2))
