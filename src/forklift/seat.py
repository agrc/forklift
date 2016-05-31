#!/usr/bin/env python
# * coding: utf8 *
'''
seat.py

A module that contains helpful methods for other modules
'''


def format_time(seconds):
    second = 1
    minute = 60 * second
    hour = 60 * minute

    if seconds < 1 * minute:
        return '{}ms'.format(round(seconds * 1000, 2))

    if seconds < 90 * minute:
        return '{} minutes'.format(round(seconds / minute, 2))

    if seconds < 24 * hour:
        return '{} hours'.format(round(second / minute / hour, 2))
