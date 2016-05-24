#!/usr/bin/env python
# * coding: utf8 *
'''
test_pallet.py

A module that contains tests for the pallet module.
'''

import unittest
from forklift.models import Pallet


class Pallet(Pallet):
    '''a test class for how pallets should work
    '''

    def execute(self):
        return True


class NoExecutePallet(Pallet):
    '''a test class for how pallets should work
    '''


class TestPallet(unittest.TestCase):

    def setUp(self):
        self.patient = Pallet('a_pallet')

    def test_no_execute_no_problem(self):
        self.patient = NoExecutePallet('blah')

        self.patient.execute()

    def test_with_execute(self):
        self.patient = Pallet('hello')

        self.assertTrue(self.patient.execute())

    def test_can_use_logging(self):
        self.patient.log.info('this works')

    def test_add_crates(self):
        source = 'C:\\MapData\\UDNR.sde'
        dest = 'C:\\MapData\\UDNR.gdb'
        self.patient.add_crates(
            ['fc1', ('fc3', 'source'), ('fc4', 'source', 'destination', 'fc4_new')], {'source': source,
                                                                                      'destination': dest})

        self.assertEquals(len(self.patient.crates), 3)

        #: single source_name with defaults
        self.assertEquals(self.patient.crates[0].source_name, 'fc1')
        self.assertEquals(self.patient.crates[0].source, source)
        self.assertEquals(self.patient.crates[0].destination, dest)
        self.assertEquals(self.patient.crates[0].destination_name, 'fc1')

        self.assertEquals(self.patient.crates[1].source, 'source')
        self.assertEquals(self.patient.crates[1].destination, dest)

        self.assertEquals(self.patient.crates[2].destination_name, 'fc4_new')

    def test_add_crates_empty_defaults(self):
        self.patient.add_crates([('fc1', 'source1', 'destination1'), ('fc2', 'source2', 'destination2', 'fc2_new')])

        self.assertEquals(len(self.patient.crates), 2)

        #: single source_name with defaults
        self.assertEquals(self.patient.crates[0].source_name, 'fc1')
        self.assertEquals(self.patient.crates[0].source, 'source1')
        self.assertEquals(self.patient.crates[0].destination, 'destination1')
        self.assertEquals(self.patient.crates[0].destination_name, 'fc1')

        self.assertEquals(self.patient.crates[1].source, 'source2')
        self.assertEquals(self.patient.crates[1].destination, 'destination2')
        self.assertEquals(self.patient.crates[1].destination_name, 'fc2_new')
