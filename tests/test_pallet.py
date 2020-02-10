#!/usr/bin/env python
# * coding: utf8 *
'''
test_pallet.py

A module that contains tests for the pallet module.
'''

import unittest
from time import sleep

from mock import patch

from forklift.models import Crate, Pallet


class TestPallet(unittest.TestCase):

    def setUp(self):
        self.patient = Pallet()

    def test_can_use_logging(self):
        self.patient.log.info('this works')

    @patch('arcpy.Describe')
    def test_name_prop(self, describe):

        class NamePallet(Pallet):

            def __init__(self):
                super(NamePallet, self).__init__()
                self.add_crates(['fc1', 'fc2', ('fc3', 'source', 'destination'), ('fc4', 'source', 'destination', 'fc4_new')], {
                    'source_workspace': 'C:\\MapData\\UDNR.sde',
                    'destination_workspace': 'C:\\MapData\\UDNR.gdb'
                })

        self.assertIn('test_pallet.py:NamePallet', NamePallet().name)

    def test_add_crates(self):
        source = 'c:\\mapdata\\udnr.sde'
        dest = 'c:\\mapdata\\udnr.gdb'
        self.patient.add_crates(['fc1', ('fc3', 'source'), ('fc4', 'source', 'destination', 'fc4_new')], {
            'source_workspace': source,
            'destination_workspace': dest
        })

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

    def test_add_crate_default_reproject(self):
        self.patient.add_crate(('fc1', 'source1', 'destination1', 'dest_name'))
        self.patient.add_crate(('fc1', 'source1', 'destination1', 'dest_name'), {'source_workspace': 'hello', 'destination_workspace': 'blah'})

        self.assertEqual(self.patient.get_crates()[0].destination_coordinate_system.factoryCode, 3857)
        self.assertEqual(self.patient.get_crates()[0].geographic_transformation, 'NAD_1983_To_WGS_1984_5')
        self.assertEqual(self.patient.get_crates()[1].destination_coordinate_system.factoryCode, 3857)

    def test_add_crate_alternative_reproject(self):

        class ReprojectPallet(Pallet):

            def __init__(self):
                super(ReprojectPallet, self).__init__()
                self.destination_coordinate_system = 26912

        pallet = ReprojectPallet()
        pallet.add_crate(('fc1', 'source1', 'destination1', 'dest_name'))

        self.assertEqual(pallet.get_crates()[0].destination_coordinate_system.factoryCode, 26912)

    def test_is_ready_to_ship_no_crates_returns_true(self):
        self.assertTrue(self.patient.is_ready_to_ship())

    def test_is_ready_to_ship_crates_with_updates_returns_true(self):
        updated = Crate('', '', '', '')
        updated.result = (Crate.UPDATED, None)

        self.patient._crates = [updated, updated, updated]

        self.assertTrue(self.patient.is_ready_to_ship())

    def test_is_ready_to_ship_crates_with_no_changes_returns_true(self):
        no_changes = Crate('', '', '', '')
        no_changes.result = (Crate.NO_CHANGES, None)

        self.patient._crates = [no_changes, no_changes, no_changes]

        self.assertTrue(self.patient.is_ready_to_ship())

    def test_is_ready_to_ship_crates_with_updates_and_no_changes_returns_true(self):
        updated = Crate('', '', '', '')
        updated.result = (Crate.UPDATED, None)

        no_changes = Crate('', '', '', '')
        no_changes.result = (Crate.NO_CHANGES, None)

        self.patient._crates = [no_changes, updated, no_changes]

        self.assertTrue(self.patient.is_ready_to_ship())

    def test_is_ready_to_ship_crates_with_any_schema_changed_returns_false(self):
        updated = Crate('', '', '', '')
        updated.result = (Crate.UPDATED, None)

        no_changes = Crate('', '', '', '')
        no_changes.result = (Crate.NO_CHANGES, None)

        schema_change = Crate('', '', '', '')
        schema_change.result = (Crate.INVALID_DATA, None)

        self.patient._crates = [updated, no_changes, schema_change]

        self.assertFalse(self.patient.is_ready_to_ship())

    def test_is_ready_to_ship_crates_with_any_exception_returns_false(self):
        updated = Crate('', '', '', '')
        updated.result = (Crate.UPDATED, None)

        no_changes = Crate('', '', '', '')
        no_changes.result = (Crate.NO_CHANGES, None)

        unhandled_exception = Crate('', '', '', '')
        unhandled_exception.result = (Crate.UNHANDLED_EXCEPTION, None)

        self.patient._crates = [updated, no_changes, unhandled_exception]

        self.assertFalse(self.patient.is_ready_to_ship())

    def test_is_ready_to_ship_crates_with_all_returns_false(self):
        updated = Crate('', '', '', '')
        updated.result = (Crate.UPDATED, None)

        no_changes = Crate('', '', '', '')
        no_changes.result = (Crate.NO_CHANGES, None)

        schema_change = Crate('', '', '', '')
        schema_change.result = (Crate.INVALID_DATA, None)

        unhandled_exception = Crate('', '', '', '')
        unhandled_exception.result = (Crate.UNHANDLED_EXCEPTION, None)

        self.patient._crates = [updated, no_changes, unhandled_exception, schema_change]

        self.assertFalse(self.patient.is_ready_to_ship())

    def test_requires_processing_with_no_crates_returns_false(self):
        self.assertFalse(self.patient.requires_processing())

    def test_requires_processing_crates_with_updates_returns_true(self):
        updated = Crate('', '', '', '')
        updated.result = (Crate.UPDATED, None)

        self.patient._crates = [updated, updated]

        self.assertTrue(self.patient.requires_processing())

    def test_requires_processing_crates_with_updates_and_changes_returns_true(self):
        updated = Crate('', '', '', '')
        updated.result = (Crate.UPDATED, None)

        no_changes = Crate('', '', '', '')
        no_changes.result = (Crate.NO_CHANGES, None)

        self.patient._crates = [updated, no_changes, no_changes]

        self.assertTrue(self.patient.requires_processing())

    def test_requires_processing_crates_with_update_and_no_changes_returns_true(self):
        updated = Crate('', '', '', '')
        updated.result = (Crate.UPDATED, None)

        self.patient._crates = [updated, updated, updated]

        self.assertTrue(self.patient.requires_processing())

    def test_requires_processing_crates_result_created_returns_true(self):
        updated = Crate('', '', '', '')
        updated.result = (Crate.CREATED, None)

        self.patient._crates = [updated]

        self.assertTrue(self.patient.requires_processing())

    def test_requires_processing_crates_with_schema_changes_returns_false(self):
        updated = Crate('', '', '', '')
        updated.result = (Crate.UPDATED, None)

        schema_change = Crate('', '', '', '')
        schema_change.result = (Crate.INVALID_DATA, None)

        self.patient._crates = [schema_change, updated, updated]

        self.assertFalse(self.patient.requires_processing())

    def test_requires_processing_crates_with_unhandled_exception_returns_false(self):
        updated = Crate('', '', '', '')
        updated.result = (Crate.UPDATED, None)

        unhandled_exception = Crate('', '', '', '')
        unhandled_exception.result = (Crate.UNHANDLED_EXCEPTION, None)

        self.patient._crates = [updated, updated, unhandled_exception]

        self.assertFalse(self.patient.requires_processing())

    def test_requires_processing_crates_ingore_errors(self):
        updated = Crate('', '', '', '')
        updated.result = (Crate.UPDATED, None)

        unhandled_exception = Crate('', '', '', '')
        unhandled_exception.result = (Crate.UNHANDLED_EXCEPTION, None)

        self.patient._crates = [updated, updated, unhandled_exception]

        self.assertTrue(self.patient.requires_processing(ignore_errors=True))

    def test_not_implemented(self):
        self.assertEqual(self.patient.process(), NotImplemented)
        self.assertEqual(self.patient.ship(), NotImplemented)
        self.assertEqual(self.patient.validate_crate(None), NotImplemented)


class TestPalletGetReport(unittest.TestCase):

    def test_successful_pallet(self):
        pallet = Pallet()
        pallet.add_crates(['fc1', 'fc2', 'fc3'], {
            'source_workspace': 'Z:\\a\\path\\to\\database.sde',
            'destination_workspace': 'Z:\\a\\path\\to\\database.gdb'
        })
        pallet.success = (True, None)
        pallet.name = 'name'
        pallet._crates[0].result = (Crate.CREATED, None)
        pallet._crates[1].result = (Crate.UPDATED, None)
        pallet._crates[2].result = (Crate.NO_CHANGES, None)
        report = pallet.get_report()

        self.assertEqual(report['name'], 'name')
        self.assertEqual(report['success'], True)
        self.assertEqual(len(report['crates']), 2)
        self.assertEqual(report['crates'][0]['result'], Crate.CREATED, None)
        self.assertEqual(report['crates'][0]['name'], 'fc1')

    def test_failed_pallet(self):
        pallet = Pallet()
        pallet.add_crates(['fc4', 'fc5', 'fc6'], {
            'source_workspace': 'Z:\\a\\path\\to\\database.sde',
            'destination_workspace': 'Z:\\a\\path\\to\\database.gdb'
        })
        pallet.success = (False, 'Failed message')
        pallet._crates[0].result = (Crate.UPDATED, None)
        pallet._crates[1].result = (Crate.INVALID_DATA, 'Invalid data message')
        pallet._crates[2].result = (Crate.UNHANDLED_EXCEPTION, None)

        report = pallet.get_report()

        self.assertEqual(report['success'], False)
        self.assertEqual(report['message'], 'Failed message')
        self.assertEqual(len(report['crates']), 3)
        self.assertEqual(report['crates'][1]['result'], Crate.INVALID_DATA)
        self.assertEqual(report['crates'][1]['crate_message'], 'Invalid data message')

    def test_processing_time(self):
        pallet = Pallet()
        first = 'first'
        second = 'second'

        pallet.start_timer(first)
        sleep(2)
        pallet.stop_timer(first)

        pallet.start_timer(second)
        sleep(3)
        pallet.stop_timer(second)

        self.assertEqual(round(pallet.total_processing_time), 5)
        self.assertEqual(round(pallet.processing_times[first]), 2)
        self.assertEqual(round(pallet.processing_times[second]), 3)


class TestPalletAddPackingSlip(unittest.TestCase):
    def test_successful_crate(self):
        slip = {
            "name": "c:\\forklift\\warehouse\\warehouse\\sgid\\AGOLPallet.py:AGOLPallet",
            "success": True,
            "is_ready_to_ship": True,
            "requires_processing": True,
            "message": "",
            "crates": [
                {
                    "name": "fc5",
                    "result": "Data updated successfully.",
                    "crate_message": "",
                    "message_level": "",
                    "source": "C:\\\\forklift-garage\\sgid10.sde\\SGID10.BOUNDARIES.ZipCodes",
                    "destination": "\\\\123.456.789.123\\agrc\\sgid_to_agol\\sgid10mercator.gdb\\ZipCodes",
                    "was_updated": True
                }
            ],
            "total_processing_time": "55.06 seconds"
        }
        pallet = Pallet()
        pallet.add_crates(['fc4', 'fc5', 'fc6'], {
            'source_workspace': 'Z:\\a\\path\\to\\database.sde',
            'destination_workspace': 'Z:\\a\\path\\to\\database.gdb'
        })

        self.assertFalse(pallet.get_crates()[1].was_updated())

        pallet.add_packing_slip(slip)

        self.assertTrue(pallet.get_crates()[1].was_updated())
        self.assertEqual(pallet.get_crates()[1].result[0], Crate.UPDATED)
