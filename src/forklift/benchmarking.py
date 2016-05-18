#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
benchmarking.py
----------------------------------
benchmarking helper module
'''

from contextlib import contextmanager
from time import clock


def get_milliseconds():
    return round(clock() * 1000, 5)


@contextmanager
def measure_time(title):
    start = get_milliseconds()
    yield
    print('{}:{}{} ms'.format(title, ''.join([' ' for x in range(1, 35 - len(title))]), round(get_milliseconds() -
                                                                                              start, 5)))
