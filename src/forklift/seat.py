#!/usr/bin/env python
# * coding: utf8 *
'''
seat.py

A module that contains helpful methods for other modules
'''


def format_time(seconds):
    '''seconds: number

    returns a human-friendly string describing the amount of time
    '''
    minute = 60.00
    hour = 60.00 * minute

    if seconds < 30:
        return '{} ms'.format(int(seconds * 1000))

    if seconds < 90:
        return '{} seconds'.format(round(seconds, 2))

    if seconds < 90 * minute:
        return '{} minutes'.format(round(seconds / minute, 2))

    return '{} hours'.format(round(seconds / hour, 2))


class timed_pallet_process(object):
    '''A class used to time pallet processes. For use in with statements.
    '''

    def __init__(self, pallet, name):
        self.pallet = pallet
        self.name = name

    def __enter__(self):
        self.pallet.start_timer(self.name)

    def __exit__(self, type, value, traceback):
        self.pallet.stop_timer(self.name)
