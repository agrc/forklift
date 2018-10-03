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
        self.assertEqual(seat.format_time(5.5), '5500 ms')

    def test_format_time_seconds(self):
        self.assertEqual(seat.format_time(80.0), '80.0 seconds')
        self.assertEqual(seat.format_time(50.0), '50.0 seconds')

    def test_format_time_minutes(self):
        self.assertEqual(seat.format_time(91.0), '1.52 minutes')
        self.assertEqual(seat.format_time(1800.0), '30.0 minutes')

    def test_format_time_hours(self):
        self.assertEqual(seat.format_time(7200.0), '2.0 hours')
        self.assertEqual(seat.format_time(5410.0), '1.5 hours')
