#!/usr/bin/env python
# * coding: utf8 *
'''
test_seat.py

A module that tests seat.py
'''

import unittest
from forklift import seat


class TestSeat(unittest.TestCase):
    def test_format_time_milliseconds(self):
        self.assertEquals(seat.format_time(5.5), '5500 ms')

    def test_format_time_seconds(self):
        self.assertEquals(seat.format_time(80), '80 seconds')
        self.assertEquals(seat.format_time(50), '50 seconds')

    def test_format_time_minutes(self):
        self.assertEquals(seat.format_time(91), '1.52 minutes')
        self.assertEquals(seat.format_time(1800), '30.0 minutes')

    def test_format_time_hours(self):
        self.assertEquals(seat.format_time(7200), '2.0 hours')
        self.assertEquals(seat.format_time(5410), '1.5 hours')
