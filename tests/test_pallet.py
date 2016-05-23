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


class Testpallet(unittest.TestCase):

    def setUp(self):
        self.patient = Pallet()

    def test_no_execute_no_problem(self):
        self.patient = NoExecutePallet()

        self.patient.execute()

    def test_with_execute(self):
        self.patient = Pallet()

        self.assertTrue(self.patient.execute())

    def test_defaults(self):
        self.assertEquals(self.patient.get_dependent_layers(), [])
        self.assertEquals(self.patient.get_source_location(), 'C:\\MapData\\SGID10.sde')
        self.assertEquals(self.patient.get_destination_location(), 'C:\\MapData\\SGID10.gdb')

    def test_can_use_logging(self):
        self.patient.log.info('this works')

    def test_overrides_class_variables(self):
        class OnePallet(Pallet):
            def __init__(self):
                super(OnePallet, self).__init__()
                self.dependencies = ['a', 'b']

        class AnotherPallet(Pallet):
            def __init__(self):
                super(AnotherPallet, self).__init__()
                self.dependencies = ['c', 'd']

        class EmptyPallet(Pallet):
            pass

        one = OnePallet()
        another = AnotherPallet()
        empty = EmptyPallet()
        one.dependencies = ['a', 'b']

        self.assertEquals(one.dependencies, ['a', 'b'])
        self.assertEquals(another.dependencies, ['c', 'd'])
        self.assertEquals(empty.dependencies, [])
