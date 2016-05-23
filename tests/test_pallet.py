#!/usr/bin/env python
# * coding: utf8 *
'''
test_pallet.py

A module that contains tests for the pallet module.
'''

import unittest
from forklift.pallet import Pallet


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
        self.patient = Pallet()

    def test_no_execute_no_problem(self):
        self.patient = NoExecutePallet()

        self.patient.execute()

    def test_with_execute(self):
        self.patient = Pallet()

        self.assertTrue(self.patient.execute())

    def test_can_use_logging(self):
        self.patient.log.info('this works')

    def test_add_crates(self):
        source = 'C:\\MapData\\UDNR.sde'
        dest = 'C:\\MapData\\UDNR.gdb'
        self.patient.add_crates(['fc1',
                                 ('fc3', 'source'),
                                 ('fc4', 'source', 'destination', 'fc4_new')],
                                {'source': source,
                                 'destination': dest})

        self.assertEquals(len(self.crates), 3)

        #: single source_name with defaults
        self.assertEquals(self.crates[0].source_name, 'fc1')
        self.assertEquals(self.crates[0].source, source)
        self.assertEquals(self.crates[0].source, dest)
        self.assertEquals(self.crates[0].destination_name, 'fc1')

        self.assertEquals(self.crates[1].source, 'source')
        self.assertEquals(self.crates[1].source, dest)

        self.assertEquals(self.crates[2].destination_name, 'fc4_new')
