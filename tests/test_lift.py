#!/usr/bin/env python
# * coding: utf8 *
'''
test_forklift.py

A module for testing lift.py
'''

import unittest
from os import path

from mock import Mock, patch

import arcpy
from forklift import core, engine, lift
from forklift.models import Crate, Pallet

fgd_describe = Mock()
fgd_describe.workspaceFactoryProgID = 'esriDataSourcesGDB.FileGDBWorkspaceFactory'
non_fgd_describe = Mock()
non_fgd_describe.workspaceFactoryProgID = 'not a fgd'
current_folder = path.dirname(path.abspath(__file__))
test_gdb = path.join(current_folder, 'data', 'test_lift', 'data.gdb')


def describe_side_effect(workspace):
    if workspace.endswith('.gdb'):
        return fgd_describe
    else:
        return non_fgd_describe


class TestLift(unittest.TestCase):

    def setUp(self):
        self.PalletMock = Mock(Pallet)

    def test_prepare_packaging_for_pallets(self):
        pallet_good = Pallet()

        pallet_bad = Pallet()
        pallet_bad.prepare_packaging = lambda: 1 + 't'

        lift.prepare_packaging_for_pallets([pallet_good, pallet_bad])

        self.assertTrue(pallet_good.success[0])
        self.assertFalse(pallet_bad.success[0])

    def test_process_crate_for_set_results(self):
        crate1 = Crate('DNROilGasWells', test_gdb, test_gdb, 'a')
        crate2 = Crate('DNROilGasWells', test_gdb, test_gdb, 'b')
        pallet = Pallet()
        pallet._crates = [crate1, crate2]
        update_def = Mock(return_value=(Crate.UPDATED, 'message'))
        lift.process_crates_for([pallet], update_def)

        self.assertEqual(update_def.call_count, 2)
        self.assertEqual(crate1.result[0], Crate.UPDATED)
        self.assertEqual(crate2.result[0], Crate.UPDATED)

    def test_process_crate_doesnt_call_update_def_on_duplicate_crates(self):
        crate1 = Crate('DNROilGasWells', test_gdb, test_gdb, 'a')
        crate2 = Crate('DNROilGasWells', test_gdb, test_gdb, 'a')
        pallet = Pallet()
        pallet._crates = [crate1, crate2]
        update_def = Mock(return_value=(Crate.UPDATED, 'message'))
        lift.process_crates_for([pallet], update_def)

        self.assertEqual(update_def.call_count, 1)
        self.assertEqual(crate1.result[0], Crate.UPDATED)
        self.assertEqual(crate2.result[0], Crate.UPDATED)

    def test_process_pallets_all_requires_processing(self):
        requires_pallet = self.PalletMock()
        requires_pallet.is_ready_to_ship.return_value = True
        requires_pallet.requires_processing.return_value = True
        requires_pallet.success = (True,)

        lift.process_pallets([requires_pallet, requires_pallet])

        self.assertEqual(requires_pallet.process.call_count, 2)

    def test_process_pallets_mixed_bag(self):
        pallet1 = Mock(Pallet)('one')
        pallet1.is_ready_to_ship = Mock(return_value=True)
        pallet1.requires_processing = Mock(return_value=False)
        pallet1.success = (True,)

        pallet2 = Mock(Pallet)('two')
        pallet2.is_ready_to_ship = Mock(return_value=False)
        pallet2.requires_processing = Mock(return_value=False)
        pallet2.success = (True,)

        pallet3 = Mock(Pallet)('three')
        pallet3.is_ready_to_ship = Mock(return_value=True)
        pallet3.requires_processing = Mock(return_value=True)
        pallet3.success = (True,)

        lift.process_pallets([pallet1, pallet2, pallet3])

        pallet1.process.assert_not_called()
        pallet2.process.assert_not_called()
        pallet3.process.assert_called_once()

        pallet = self.PalletMock()
        process_error = Exception('process error')
        pallet.process.side_effect = process_error
        pallet.success = (True,)

        lift.process_pallets([pallet])

        self.assertEqual(pallet.success, (False, str(process_error)))

    def test_process_pallets_resets_arcpy(self):
        pallet = self.PalletMock()
        pallet2 = Mock(Pallet)

        import arcpy

        def modify_workspace(value):
            arcpy.env.workspace = value

        pallet.ship.side_effect = modify_workspace('forklift')
        pallet.success = (True,)

        self.assertEqual(arcpy.env.workspace, 'forklift')

        pallet2.success = (True,)

        lift.process_pallets([pallet, pallet2])

        self.assertEqual(arcpy.env.workspace, None)

    @patch('forklift.lift.listdir', return_value=['testfile'])
    @patch('arcpy.Describe', autospec=True)
    @patch('arcpy.Compact_management', autospec=True)
    @patch('shutil.move', autospec=True)
    @patch('shutil.rmtree', autospec=True)
    @patch('shutil.copytree', autospec=True)
    def test_copy_data_error(self, copytree_mock, rmtree_mock, move, compact_mock, describe_mock, listdir_mock):
        describe_mock.side_effect = describe_side_effect
        error_message = 'there was an error'
        copytree_mock.side_effect = Exception(error_message)

        pallet = Pallet()
        pallet.copy_data = ['C:\\MapData\\one.gdb']
        pallet.requires_processing = Mock(return_value=True)

        success, failed = lift.copy_data('from_location', 'to_location', engine.packing_slip_file)

        self.assertTrue(failed['testfile'].startswith(error_message))

    def test_copy_data_scrub_hash_field(self):
        copy_data_fgdb_name = 'CopyData.gdb'
        from_folder = path.join(current_folder, 'data', 'copy_data')
        to_folder = path.join(current_folder, 'data', 'pickup')
        copied_data = path.join(to_folder, copy_data_fgdb_name)

        def cleanup():
            print('cleaning up')
            if arcpy.Exists(to_folder):
                arcpy.Delete_management(to_folder)

        cleanup()

        lift.copy_data(from_folder, to_folder, engine.packing_slip_file)
        lift.gift_wrap(to_folder)

        feature_class_fields = [field.name for field in arcpy.Describe(path.join(copied_data, 'DNROilGasWells_adds')).fields]
        table_fields = [field.name for field in arcpy.Describe(path.join(copied_data, 'Providers_adds')).fields]

        self.assertNotIn(core.hash_field, feature_class_fields)
        self.assertNotIn(core.hash_field, table_fields)

        cleanup()

    def test_get_lift_status(self):
        git_errors = ['a', 'b']
        p1 = Pallet()
        p1.success = (False, '')

        p2 = Pallet()
        p3 = Pallet()

        report = lift.get_lift_status([p1, p2, p3], 10, git_errors, [])

        self.assertEqual(report['total_pallets'], 3)
        self.assertEqual(report['num_success_pallets'], 2)
        self.assertEqual(report['git_errors'], git_errors)
