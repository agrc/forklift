#!/usr/bin/env python
# * coding: utf8 *
'''
test_pallet.py

A module that contains tests for the pallet module.
'''

import unittest
from forklift.models import Pallet, Crate


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

    def test_is_ready_to_ship_no_crates_returns_true(self):
        self.assertTrue(self.patient.is_ready_to_ship())

    def test_is_ready_to_ship_crates_with_updates_returns_true(self):
        updated = Crate(None, None, None, None)
        updated.result = Crate.UPDATED

        self.patient._crates = [updated, updated, updated]

        self.assertTrue(self.patient.is_ready_to_ship())

    def test_is_ready_to_ship_crates_with_no_changes_returns_true(self):
        no_changes = Crate(None, None, None, None)
        no_changes.result = Crate.NO_CHANGES

        self.patient._crates = [no_changes, no_changes, no_changes]

        self.assertTrue(self.patient.is_ready_to_ship())

    def test_is_ready_to_ship_crates_with_updates_and_no_changes_returns_true(self):
        updated = Crate(None, None, None, None)
        updated.result = Crate.UPDATED

        no_changes = Crate(None, None, None, None)
        no_changes.result = Crate.NO_CHANGES

        self.patient._crates = [no_changes, updated, no_changes]

        self.assertTrue(self.patient.is_ready_to_ship())

    def test_is_ready_to_ship_crates_with_any_schema_changed_returns_false(self):
        updated = Crate(None, None, None, None)
        updated.result = Crate.UPDATED

        no_changes = Crate(None, None, None, None)
        no_changes.result = Crate.NO_CHANGES

        schema_change = Crate(None, None, None, None)
        schema_change.result = Crate.SCHEMA_CHANGED

        self.patient._crates = [updated, no_changes, schema_change]

        self.assertFalse(self.patient.is_ready_to_ship())

    def test_is_ready_to_ship_crates_with_any_exception_returns_false(self):
        updated = Crate(None, None, None, None)
        updated.result = Crate.UPDATED

        no_changes = Crate(None, None, None, None)
        no_changes.result = Crate.NO_CHANGES

        unhandled_exception = Crate(None, None, None, None)
        unhandled_exception.result = Crate.UNHANDLED_EXCEPTION

        self.patient._crates = [updated, no_changes, unhandled_exception]

        self.assertFalse(self.patient.is_ready_to_ship())

    def test_is_ready_to_ship_crates_with_all_returns_false(self):
        updated = Crate(None, None, None, None)
        updated.result = Crate.UPDATED

        no_changes = Crate(None, None, None, None)
        no_changes.result = Crate.NO_CHANGES

        schema_change = Crate(None, None, None, None)
        schema_change.result = Crate.SCHEMA_CHANGED

        unhandled_exception = Crate(None, None, None, None)
        unhandled_exception.result = Crate.UNHANDLED_EXCEPTION

        self.patient._crates = [updated, no_changes, unhandled_exception, schema_change]

        self.assertFalse(self.patient.is_ready_to_ship())

    def test_requires_processing_with_no_crates_returns_false(self):
        self.assertFalse(self.patient.requires_processing())

    def test_requires_processing_crates_with_updates_returns_true(self):
        updated = Crate(None, None, None, None)
        updated.result = Crate.UPDATED

        self.patient._crates = [updated, updated]

        self.assertTrue(self.patient.requires_processing())

    def test_requires_processing_crates_with_updates_and_changes_returns_true(self):
        updated = Crate(None, None, None, None)
        updated.result = Crate.UPDATED

        no_changes = Crate(None, None, None, None)
        no_changes.result = Crate.NO_CHANGES

        self.patient._crates = [updated, no_changes, no_changes]

        self.assertTrue(self.patient.requires_processing())

    def test_requires_processing_crates_with_update_and_no_changes_returns_true(self):
        updated = Crate(None, None, None, None)
        updated.result = Crate.UPDATED

        self.patient._crates = [updated, updated, updated]

        self.assertTrue(self.patient.requires_processing())

    def test_requires_processing_crates_with_schema_changes_returns_false(self):
        updated = Crate(None, None, None, None)
        updated.result = Crate.UPDATED

        schema_change = Crate(None, None, None, None)
        schema_change.result = Crate.SCHEMA_CHANGED

        self.patient._crates = [schema_change, updated, updated]

        self.assertFalse(self.patient.requires_processing())

    def test_requires_processing_crates_with_unhandled_exception_returns_false(self):
        updated = Crate(None, None, None, None)
        updated.result = Crate.UPDATED

        unhandled_exception = Crate(None, None, None, None)
        unhandled_exception.result = Crate.UNHANDLED_EXCEPTION

        self.patient._crates = [updated, updated, unhandled_exception]

        self.assertFalse(self.patient.requires_processing())
