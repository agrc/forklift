#!/usr/bin/env python
# * coding: utf8 *
'''
test_plugin.py

A module that contains tests for the plugin module.
'''

import unittest
from forklift.plugin import ScheduledUpdateBase
from nose.tools import raises


class Plugin(ScheduledUpdateBase):
    '''a test class for how plugins should work
    '''

    def execute(self):
        return True


class NoExecutePlugin(ScheduledUpdateBase):
    '''a test class for how plugins should work
    '''


class TestPlugin(unittest.TestCase):
    def setUp(self):
        self.patient = Plugin()

    def test_no_execute_no_problem(self):
        self.patient = NoExecutePlugin()

        self.patient.execute()

    def test_with_execute(self):
        self.patient = Plugin()

        self.assertTrue(self.patient.execute())

    def test_defaults(self):
        self.assertEquals(self.patient.get_dependent_layers(), [])
        self.assertEquals(self.patient.get_source_location(), 'C:\\MapData\\SGID10.sde')
        self.assertEquals(self.patient.get_destination_location(), 'C:\\MapData\\SGID10.gdb')

    def test_can_use_logging(self):
        self.patient.log.info('this works')
