#!/usr/bin/env python
# * coding: utf8 *
'''
test_lift.py

A module that contains tests for the lift.py module
'''

import unittest
from forklift import lift
from json import loads
from os.path import exists


class TestLift(unittest.TestCase):

    def setUp(self):
        pass

    def test_init_creates_config_file(self):
        path = lift.init()

        self.assertTrue(exists(path))

        with open(path) as config:
            self.assertEquals(['c:\\scheduled'], loads(config))
