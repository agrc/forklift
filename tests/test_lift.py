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
from forklift import core, lift
from forklift.models import Crate, Pallet

fgd_describe = Mock()
fgd_describe.workspaceFactoryProgID = 'esriDataSourcesGDB.FileGDBWorkspaceFactory'
non_fgd_describe = Mock()
non_fgd_describe.workspaceFactoryProgID = 'not a fgd'
current_folder = path.dirname(path.abspath(__file__))
check_for_changes_gdb = path.join(current_folder, 'data', 'checkForChanges.gdb')


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
        crate1 = Crate('DNROilGasWells', check_for_changes_gdb, check_for_changes_gdb, 'a')
        crate2 = Crate('DNROilGasWells', check_for_changes_gdb, check_for_changes_gdb, 'b')
        pallet = Pallet()
        pallet._crates = [crate1, crate2]
        update_def = Mock(return_value=(Crate.UPDATED, 'message'))
        lift.process_crates_for([pallet], update_def)

        self.assertEqual(update_def.call_count, 2)
        self.assertEqual(crate1.result[0], Crate.UPDATED)
        self.assertEqual(crate2.result[0], Crate.UPDATED)

    def test_process_crate_doesnt_call_update_def_on_duplicate_crates(self):
        crate1 = Crate('DNROilGasWells', check_for_changes_gdb, check_for_changes_gdb, 'a')
        crate2 = Crate('DNROilGasWells', check_for_changes_gdb, check_for_changes_gdb, 'a')
        pallet = Pallet()
        pallet._crates = [crate1, crate2]
        update_def = Mock(return_value=(Crate.UPDATED, 'message'))
        lift.process_crates_for([pallet], update_def)

        self.assertEqual(update_def.call_count, 1)
        self.assertEqual(crate1.result[0], Crate.UPDATED)
        self.assertEqual(crate2.result[0], Crate.UPDATED)

    def test_process_pallets_all_ready_to_ship(self):
        ready_pallet = self.PalletMock()
        ready_pallet.is_ready_to_ship.return_value = True
        ready_pallet.success = (True,)

        lift.process_pallets([ready_pallet, ready_pallet])

        self.assertEqual(ready_pallet.ship.call_count, 2)

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

        pallet1.ship.assert_called_once()
        pallet1.process.assert_not_called()
        pallet2.ship.assert_not_called()
        pallet2.process.assert_not_called()
        pallet3.ship.assert_called_once()
        pallet3.process.assert_called_once()

        pallet = self.PalletMock()
        process_error = Exception('process error')
        pallet.process.side_effect = process_error
        pallet.success = (True,)

        lift.process_pallets([pallet])

        self.assertEqual(pallet.success, (False, process_error))

    def test_process_pallets_handles_ship_exception(self):
        pallet = self.PalletMock()
        ship_error = Exception('ship error')
        pallet.ship.side_effect = ship_error
        pallet.success = (True,)

        lift.process_pallets([pallet])

        self.assertEqual(pallet.success, (False, ship_error))

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

    def test_process_pallets_post_copy(self):
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

        lift.process_pallets([pallet1, pallet2, pallet3], is_post_copy=True)

        pallet1.post_copy_process.assert_not_called()
        pallet2.post_copy_process.assert_not_called()
        pallet3.post_copy_process.assert_called_once()

    @patch('arcpy.Describe', autospec=True)
    @patch('arcpy.Compact_management', autospec=True)
    @patch('forklift.lift.path.exists', autospec=True)
    @patch('shutil.move', autospec=True)
    @patch('shutil.rmtree', autospec=True)
    @patch('shutil.copytree', autospec=True)
    def test_copy_data(self, copytree_mock, rmtree_mock, move, exists_mock, compact_mock, describe_mock):
        describe_mock.side_effect = describe_side_effect
        exists_mock.return_value = True
        three = 'C:\\MapData\\three.gdb'
        two = 'C:\\MapData\\two.gdb'

        pallet_one = Pallet()
        pallet_one.copy_data = ['C:\\MapData\\one.gdb', two]
        pallet_one.requires_processing = Mock(return_value=True)

        pallet_two = Pallet()
        pallet_two.copy_data = ['C:\\MapData\\one.gdb', three]
        pallet_two.requires_processing = Mock(return_value=True)

        pallet_three = Pallet()
        pallet_three.copy_data = ['C:\\MapData\\four', three]

        lift.copy_data([pallet_one, pallet_two, pallet_three], [pallet_one, pallet_two, pallet_three], ['dest1', 'dest2'])

        self.assertEqual(copytree_mock.call_count, 6)
        self.assertEqual(rmtree_mock.call_count, 6)
        self.assertEqual(compact_mock.call_count, 3)

    @patch('arcpy.Describe', autospec=True)
    @patch('arcpy.Compact_management', autospec=True)
    @patch('shutil.move', autospec=True)
    @patch('shutil.rmtree', autospec=True)
    @patch('shutil.copytree', autospec=True)
    def test_copy_data_error(self, copytree_mock, rmtree_mock, move, compact_mock, describe_mock):
        describe_mock.side_effect = describe_side_effect
        error_message = 'there was an error'
        copytree_mock.side_effect = Exception(error_message)

        pallet = Pallet()
        pallet.copy_data = ['C:\\MapData\\one.gdb']
        pallet.requires_processing = Mock(return_value=True)

        lift.copy_data([pallet], [pallet], ['hello'])

        self.assertEqual(pallet.success, (False, error_message))

    # @patch('forklift.lift.LightSwitch', autospec=True)
    # @patch('arcpy.Describe', autospec=True)
    # @patch('arcpy.Compact_management', autospec=True)
    # @patch('forklift.lift.path.exists', autospec=True)
    # @patch('shutil.move', autospec=True)
    # @patch('shutil.rmtree', autospec=True)
    # @patch('shutil.copytree', autospec=True)
    # def test_copy_data_turns_off_and_on_services(self, copytree_mock, rmtree_mock, move, exists_mock, compact_mock,
    #                                              describe_mock, lightswitch_mock):
    #     describe_mock.side_effect = describe_side_effect
    #     exists_mock.return_value = True
    #     lightswitch_mock().ensure.return_value = (True, [])
    #     three = 'C:\\MapData\\three.gdb'
    #     two = 'C:\\MapData\\two.gdb'
    #
    #     pallet_one = Pallet()
    #     pallet_one.copy_data = ['C:\\MapData\\one.gdb', two]
    #     pallet_one.arcgis_services = [('Pallet', 'MapServer')]
    #     pallet_one.requires_processing = Mock(return_value=True)
    #
    #     pallet_two = Pallet()
    #     pallet_two.copy_data = ['C:\\MapData\\one.gdb', three]
    #     pallet_two.arcgis_services = [('Pallet', 'MapServer')]
    #     pallet_two.requires_processing = Mock(return_value=True)
    #
    #     pallet_three = Pallet()
    #     pallet_three.copy_data = ['C:\\MapData\\four', three]
    #
    #     lift.copy_data([pallet_one, pallet_two, pallet_three], [pallet_one, pallet_two, pallet_three], ['dest1', 'dest2'])
    #
    #     self.assertEqual(copytree_mock.call_count, 6)
    #     self.assertEqual(rmtree_mock.call_count, 6)
    #     self.assertEqual(compact_mock.call_count, 3)
    #     lightswitch_mock().ensure.assert_has_calls([call('off', set([('Pallet', 'MapServer')])), call('on', set([('Pallet', 'MapServer')]))])

    def test_copy_data_scrub_hash_field(self):
        copy_data_fgdb_name = 'CopyData.gdb'
        copied_data = path.join(current_folder, copy_data_fgdb_name)

        def cleanup():
            print('cleaning up')
            if arcpy.Exists(copied_data):
                arcpy.Delete_management(copied_data)

        cleanup()

        pallet = Pallet()
        pallet.copy_data = [path.join(current_folder, 'data', copy_data_fgdb_name)]
        pallet.requires_processing = Mock(return_value=True)

        lift.copy_data([pallet], [pallet], [current_folder])

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

        report = lift.get_lift_status([p1, p2, p3], 10, git_errors)

        self.assertEqual(report['total_pallets'], 3)
        self.assertEqual(report['num_success_pallets'], 2)
        self.assertEqual(report['git_errors'], git_errors)

    def test_hydrate_data_structures_with_empty_is_ok(self):
        pallets = [Pallet(), Pallet()]
        pallets[0].requires_processing = Mock(return_value=True)
        pallets[1].requires_processing = Mock(return_value=True)

        lift._hydrate_data_structures([], pallets)

    def test_hydrate_data_structures_unions_arcgis_services(self):
        pallets = [Pallet(), Pallet()]

        pallets[0].requires_processing = Mock(return_value=True)
        pallets[1].requires_processing = Mock(return_value=True)

        pallets[0].copy_data = ['location']
        pallets[1].copy_data = ['location']

        pallets[0].arcgis_services = [('a', 'a'), ('b', 'b')]
        pallets[1].arcgis_services = [('a', 'a'), ('c', 'c')]

        affected_services, data_being_moved, destination_to_pallet = lift._hydrate_data_structures(pallets, pallets)
        self.assertEqual(affected_services, set([('a', 'a'), ('b', 'b'), ('c', 'c')]))

    def test_hydrate_data_structures_unions_all_copy_data_locations(self):
        pallets = [Pallet(), Pallet(), Pallet()]

        pallets[0].requires_processing = Mock(return_value=True)
        pallets[1].requires_processing = Mock(return_value=True)
        pallets[2].requires_processing = Mock(return_value=True)

        pallets[0].copy_data = ['location']
        pallets[1].copy_data = ['location']
        pallets[2].copy_data = ['location2']

        affected_services, data_being_moved, destination_to_pallet = lift._hydrate_data_structures(pallets, pallets)
        self.assertEqual(data_being_moved, set(['location', 'location2']))

    def test_hydrate_data_structures_creates_destination_dictionary(self):
        pallets = [Pallet(), Pallet(), Pallet()]

        pallets[0].requires_processing = Mock(return_value=True)
        pallets[1].requires_processing = Mock(return_value=True)
        pallets[2].requires_processing = Mock(return_value=True)

        pallets[0].copy_data = ['location']
        pallets[1].copy_data = ['location']
        pallets[2].copy_data = ['location2']

        affected_services, data_being_moved, destination_to_pallet = lift._hydrate_data_structures(pallets, pallets)
        self.assertEqual(destination_to_pallet['location'], [pallets[0], pallets[1]])
        self.assertEqual(destination_to_pallet['location2'], [pallets[2]])

    def test_hydrate_data_structures_prevents_duplicate_copy_datas(self):
        pallets = [Pallet(), Pallet(), Pallet()]

        pallets[0].requires_processing = Mock(return_value=True)
        pallets[1].requires_processing = Mock(return_value=True)
        pallets[2].requires_processing = Mock(return_value=True)

        pallets[0].copy_data = ['location']
        pallets[1].copy_data = ['Location']
        pallets[2].copy_data = ['location2']

        affected_services, data_being_moved, destination_to_pallet = lift._hydrate_data_structures(pallets, pallets)
        data_being_moved = list(data_being_moved)

        self.assertEqual(len(data_being_moved), 2)
        self.assertIn('location', data_being_moved)
        self.assertIn('location2', data_being_moved)

    def test_hydrate_data_structures_only_includes_copy_data_in_specific_pallets(self):
        pallets = [Pallet(), Pallet(), Pallet()]

        pallets[0].requires_processing = Mock(return_value=True)
        pallets[0].copy_data = ['C:\location']
        pallets[0].arcgis_services = ['service1']

        pallets[1].copy_data = ['C:\Location']
        pallets[1].arcgis_services = ['service2']

        pallets[2].copy_data = ['C:\location2']

        affected_services, data_being_moved, destination_to_pallet = lift._hydrate_data_structures(pallets[:1], pallets)
        data_being_moved = list(data_being_moved)

        self.assertEqual(data_being_moved[0], 'c:\location')
        self.assertEqual(len(data_being_moved), 1)
        self.assertEqual(destination_to_pallet['c:\\location'], [pallets[0], pallets[1]])
        self.assertEqual(affected_services, set(['service2', 'service1']))

    def test_hydrate_data_structures_normalizes_paths(self):
        pallets = [Pallet(), Pallet()]

        pallets[0].requires_processing = Mock(return_value=True)
        pallets[0].copy_data = ['C:\\\\Scheduled\\staging\\political_utm.gdb']
        pallets[0].arcgis_services = ['service1']

        pallets[1].copy_data = ['C:\\Scheduled\\staging\\political_utm.gdb']
        pallets[1].arcgis_services = ['service2']

        affected_services, data_being_moved, destination_to_pallet = lift._hydrate_data_structures(pallets[:1], pallets)

        self.assertEqual(affected_services, set(['service2', 'service1']))
