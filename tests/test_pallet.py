#!/usr/bin/env python
# * coding: utf8 *
'''
test_pallet.py

A module that contains tests for the pallet module.
'''

import unittest
from forklift.models import Pallet, Crate


class TestPallet(unittest.TestCase):

    def setUp(self):
        self.patient = Pallet()

    def test_can_use_logging(self):
        self.patient.log.info('this works')

    def test_name_prop(self):
        class NamePallet(Pallet):
            def __init__(self):
                super(NamePallet, self).__init__()
                self.add_crates(['fc1',
                                 'fc2',
                                 ('fc3', 'source', 'destination'),
                                 ('fc4', 'source', 'destination', 'fc4_new')],
                                {'source_workspace': 'C:\\MapData\\UDNR.sde',
                                 'destination_workspace': 'C:\\MapData\\UDNR.gdb'})
        self.assertIn('test_pallet.py:NamePallet', NamePallet().name)

    def test_add_crates(self):
        source = 'C:\\MapData\\UDNR.sde'
        dest = 'C:\\MapData\\UDNR.gdb'
        self.patient.add_crates(
            ['fc1', ('fc3', 'source'), ('fc4', 'source', 'destination', 'fc4_new')], {'source_workspace': source,
                                                                                      'destination_workspace': dest})

        self.assertEqual(len(self.patient.get_crates()), 3)

        #: single source_name with defaults
        self.assertEqual(self.patient.get_crates()[0].source_name, 'fc1')
        self.assertEqual(self.patient.get_crates()[0].source_workspace, source)
        self.assertEqual(self.patient.get_crates()[0].destination_workspace, dest)
        self.assertEqual(self.patient.get_crates()[0].destination_name, 'fc1')

        self.assertEqual(self.patient.get_crates()[1].source_workspace, 'source')
        self.assertEqual(self.patient.get_crates()[1].destination_workspace, dest)

        self.assertEqual(self.patient.get_crates()[2].destination_name, 'fc4_new')

    def test_add_crates_empty_defaults(self):
        self.patient.add_crates([('fc1', 'source1', 'destination1'), ('fc2', 'source2', 'destination2', 'fc2_new')])

        self.assertEqual(len(self.patient.get_crates()), 2)

        #: single source_name with defaults
        self.assertEqual(self.patient.get_crates()[0].source_name, 'fc1')
        self.assertEqual(self.patient.get_crates()[0].source_workspace, 'source1')
        self.assertEqual(self.patient.get_crates()[0].destination_workspace, 'destination1')
        self.assertEqual(self.patient.get_crates()[0].destination_name, 'fc1')

        self.assertEqual(self.patient.get_crates()[1].source_workspace, 'source2')
        self.assertEqual(self.patient.get_crates()[1].destination_workspace, 'destination2')
        self.assertEqual(self.patient.get_crates()[1].destination_name, 'fc2_new')

    def test_add_crate_with_string(self):
        self.patient.add_crate('fc1', {'source_workspace': 'source1', 'destination_workspace': 'destination1'})

        self.assertEqual(len(self.patient.get_crates()), 1)

        #: single source_name with defaults
        self.assertEqual(self.patient.get_crates()[0].source_name, 'fc1')
        self.assertEqual(self.patient.get_crates()[0].destination_name, 'fc1')
        self.assertEqual(self.patient.get_crates()[0].source_workspace, 'source1')
        self.assertEqual(self.patient.get_crates()[0].destination_workspace, 'destination1')

    def test_add_crate_with_tuple_one_value(self):
        self.patient.add_crate(('fc1'), {'source_workspace': 'source1', 'destination_workspace': 'destination1'})

        self.assertEqual(len(self.patient.get_crates()), 1)

        #: single source_name with defaults
        self.assertEqual(self.patient.get_crates()[0].source_name, 'fc1')
        self.assertEqual(self.patient.get_crates()[0].destination_name, 'fc1')
        self.assertEqual(self.patient.get_crates()[0].source_workspace, 'source1')
        self.assertEqual(self.patient.get_crates()[0].destination_workspace, 'destination1')

    def test_add_crate_with_tuple_two_values(self):
        self.patient.add_crate(('fc1', 'source1'), {'source_workspace': 'source2', 'destination_workspace': 'destination1'})

        self.assertEqual(len(self.patient.get_crates()), 1)

        #: single source_name with defaults
        self.assertEqual(self.patient.get_crates()[0].source_name, 'fc1')
        self.assertEqual(self.patient.get_crates()[0].destination_name, 'fc1')
        self.assertEqual(self.patient.get_crates()[0].source_workspace, 'source1')
        self.assertEqual(self.patient.get_crates()[0].destination_workspace, 'destination1')

    def test_add_crate_with_tuple_three_values(self):
        self.patient.add_crate(('fc1', 'source1', 'destination1'))

        self.assertEqual(len(self.patient.get_crates()), 1)

        #: single source_name with defaults
        self.assertEqual(self.patient.get_crates()[0].source_name, 'fc1')
        self.assertEqual(self.patient.get_crates()[0].destination_name, 'fc1')
        self.assertEqual(self.patient.get_crates()[0].source_workspace, 'source1')
        self.assertEqual(self.patient.get_crates()[0].destination_workspace, 'destination1')

    def test_add_crate_with_tuple_four_values(self):
        self.patient.add_crate(('fc1', 'source1', 'destination1', 'dest_name'))

        self.assertEqual(len(self.patient.get_crates()), 1)

        #: single source_name with defaults
        self.assertEqual(self.patient.get_crates()[0].source_name, 'fc1')
        self.assertEqual(self.patient.get_crates()[0].destination_name, 'dest_name')
        self.assertEqual(self.patient.get_crates()[0].source_workspace, 'source1')
        self.assertEqual(self.patient.get_crates()[0].destination_workspace, 'destination1')

    def test_is_ready_to_ship_no_crates_returns_true(self):
        self.assertTrue(self.patient.is_ready_to_ship())

    def test_is_ready_to_ship_crates_with_updates_returns_true(self):
        updated = Crate('', '', '', '')
        updated.result = Crate.UPDATED

        self.patient._crates = [updated, updated, updated]

        self.assertTrue(self.patient.is_ready_to_ship())

    def test_is_ready_to_ship_crates_with_no_changes_returns_true(self):
        no_changes = Crate('', '', '', '')
        no_changes.result = Crate.NO_CHANGES

        self.patient._crates = [no_changes, no_changes, no_changes]

        self.assertTrue(self.patient.is_ready_to_ship())

    def test_is_ready_to_ship_crates_with_updates_and_no_changes_returns_true(self):
        updated = Crate('', '', '', '')
        updated.result = Crate.UPDATED

        no_changes = Crate('', '', '', '')
        no_changes.result = Crate.NO_CHANGES

        self.patient._crates = [no_changes, updated, no_changes]

        self.assertTrue(self.patient.is_ready_to_ship())

    def test_is_ready_to_ship_crates_with_any_schema_changed_returns_false(self):
        updated = Crate('', '', '', '')
        updated.result = Crate.UPDATED

        no_changes = Crate('', '', '', '')
        no_changes.result = Crate.NO_CHANGES

        schema_change = Crate('', '', '', '')
        schema_change.result = Crate.INVALID_DATA

        self.patient._crates = [updated, no_changes, schema_change]

        self.assertFalse(self.patient.is_ready_to_ship())

    def test_is_ready_to_ship_crates_with_any_exception_returns_false(self):
        updated = Crate('', '', '', '')
        updated.result = Crate.UPDATED

        no_changes = Crate('', '', '', '')
        no_changes.result = Crate.NO_CHANGES

        unhandled_exception = Crate('', '', '', '')
        unhandled_exception.result = Crate.UNHANDLED_EXCEPTION

        self.patient._crates = [updated, no_changes, unhandled_exception]

        self.assertFalse(self.patient.is_ready_to_ship())

    def test_is_ready_to_ship_crates_with_all_returns_false(self):
        updated = Crate('', '', '', '')
        updated.result = Crate.UPDATED

        no_changes = Crate('', '', '', '')
        no_changes.result = Crate.NO_CHANGES

        schema_change = Crate('', '', '', '')
        schema_change.result = Crate.INVALID_DATA

        unhandled_exception = Crate('', '', '', '')
        unhandled_exception.result = Crate.UNHANDLED_EXCEPTION

        self.patient._crates = [updated, no_changes, unhandled_exception, schema_change]

        self.assertFalse(self.patient.is_ready_to_ship())

    def test_requires_processing_with_no_crates_returns_false(self):
        self.assertFalse(self.patient.requires_processing())

    def test_requires_processing_crates_with_updates_returns_true(self):
        updated = Crate('', '', '', '')
        updated.result = Crate.UPDATED

        self.patient._crates = [updated, updated]

        self.assertTrue(self.patient.requires_processing())

    def test_requires_processing_crates_with_updates_and_changes_returns_true(self):
        updated = Crate('', '', '', '')
        updated.result = Crate.UPDATED

        no_changes = Crate('', '', '', '')
        no_changes.result = Crate.NO_CHANGES

        self.patient._crates = [updated, no_changes, no_changes]

        self.assertTrue(self.patient.requires_processing())

    def test_requires_processing_crates_with_update_and_no_changes_returns_true(self):
        updated = Crate('', '', '', '')
        updated.result = Crate.UPDATED

        self.patient._crates = [updated, updated, updated]

        self.assertTrue(self.patient.requires_processing())

    def test_requires_processing_crates_with_schema_changes_returns_false(self):
        updated = Crate('', '', '', '')
        updated.result = Crate.UPDATED

        schema_change = Crate('', '', '', '')
        schema_change.result = Crate.INVALID_DATA

        self.patient._crates = [schema_change, updated, updated]

        self.assertFalse(self.patient.requires_processing())

    def test_requires_processing_crates_with_unhandled_exception_returns_false(self):
        updated = Crate('', '', '', '')
        updated.result = Crate.UPDATED

        unhandled_exception = Crate('', '', '', '')
        unhandled_exception.result = Crate.UNHANDLED_EXCEPTION

        self.patient._crates = [updated, updated, unhandled_exception]

        self.assertFalse(self.patient.requires_processing())

    def test_not_implemented(self):
        self.assertEqual(self.patient.process(), NotImplemented)
        self.assertEqual(self.patient.ship(), NotImplemented)
        self.assertEqual(self.patient.validate_crate(None), NotImplemented)


class TestPalletGetReport(unittest.TestCase):
    def test_successful_pallet(self):
        pallet = Pallet()
        pallet.add_crates(['fc1', 'fc2', 'fc3'], {'source_workspace': 'Z:\\a\\path\\to\\database.sde',
                                                  'destination_workspace': 'Z:\\a\\path\\to\\database.gdb'})
        pallet.success = (True, None)
        pallet.name = 'name'
        pallet._crates[0].result = (Crate.CREATED, None)
        pallet._crates[1].result = (Crate.UPDATED, None)
        pallet._crates[2].result = (Crate.NO_CHANGES, None)

        report = pallet.get_report()

        self.assertEqual(report['name'], 'name')
        self.assertEqual(report['success'], True)
        self.assertEqual(report['crates'][0]['result'], Crate.CREATED)
        self.assertEqual(report['crates'][0]['name'], 'fc1')

    def test_failed_pallet(self):
        pallet = Pallet()
        pallet.add_crates(['fc4', 'fc5', 'fc6'], {'source_workspace': 'Z:\\a\\path\\to\\database.sde',
                                                  'destination_workspace': 'Z:\\a\\path\\to\\database.gdb'})
        pallet.success = (False, 'Failed message')
        pallet._crates[0].result = (Crate.UPDATED, None)
        pallet._crates[1].result = (Crate.INVALID_DATA, 'Invalid data message')
        pallet._crates[2].result = (Crate.UNHANDLED_EXCEPTION, None)

        report = pallet.get_report()

        self.assertEqual(report['success'], False)
        self.assertEqual(report['message'], 'Failed message')
        self.assertEqual(report['crates'][1]['result'], Crate.INVALID_DATA)
        self.assertEqual(report['crates'][1]['crate_message'], 'Invalid data message')
