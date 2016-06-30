#!/usr/bin/env python
# * coding: utf8 *
'''
test_forklift.py

A module for testing lift.py
'''

import unittest
from forklift import lift
from forklift.models import Pallet, Crate
from mock import Mock, patch

fgd_describe = Mock()
fgd_describe.workspaceFactoryProgID = 'esriDataSourcesGDB.FileGDBWorkspaceFactory'
non_fgd_describe = Mock()
non_fgd_describe.workspaceFactoryProgID = 'not a fgd'


def describe_side_effect(workspace):
    if workspace.endswith('.gdb'):
        return fgd_describe
    else:
        return non_fgd_describe


class TestLift(unittest.TestCase):

    def setUp(self):
        self.PalletMock = Mock(Pallet)

    def test_process_crate_for_set_results(self):
        crate1 = Crate('', '', 'a', '')
        crate2 = Crate('', '', 'b', '')
        pallet = Pallet()
        pallet._crates = [crate1, crate2]
        update_def = Mock(return_value=(Crate.UPDATED, 'message'))
        lift.process_crates_for([pallet], update_def)

        self.assertEqual(update_def.call_count, 2)
        self.assertEqual(crate1.result[0], Crate.UPDATED)
        self.assertEqual(crate2.result[0], Crate.UPDATED)

    def test_process_crate_doesnt_call_update_def_on_duplicate_crates(self):
        crate1 = Crate('', '', 'a', '')
        crate2 = Crate('', '', 'a', '')
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

    def test_process_pallets_handles_process_exception(self):
        pallet = self.PalletMock()
        pallet.process.side_effect = Exception('process error')
        pallet.success = (True,)

        lift.process_pallets([pallet])

        self.assertEqual(pallet.success, (False, 'process error'))

    def test_process_pallets_handles_ship_exception(self):
        pallet = self.PalletMock()
        pallet.ship.side_effect = Exception('ship error')
        pallet.success = (True,)

        lift.process_pallets([pallet])

        self.assertEqual(pallet.success, (False, 'ship error'))

    @patch('forklift.lift.Describe', autospec=True)
    @patch('forklift.lift.Compact_management', autospec=True)
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

    @patch('forklift.lift.Describe', autospec=True)
    @patch('forklift.lift.Compact_management', autospec=True)
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

    @patch('forklift.lift.LightSwitch', autospec=True)
    @patch('forklift.lift.Describe', autospec=True)
    @patch('forklift.lift.Compact_management', autospec=True)
    @patch('forklift.lift.path.exists', autospec=True)
    @patch('shutil.move', autospec=True)
    @patch('shutil.rmtree', autospec=True)
    @patch('shutil.copytree', autospec=True)
    def test_copy_data_turns_off_and_on_services(self, copytree_mock, rmtree_mock, move, exists_mock, compact_mock,
                                                 describe_mock, lightswitch_mock):
        describe_mock.side_effect = describe_side_effect
        exists_mock.return_value = True
        three = 'C:\\MapData\\three.gdb'
        two = 'C:\\MapData\\two.gdb'

        pallet_one = Pallet()
        pallet_one.copy_data = ['C:\\MapData\\one.gdb', two]
        pallet_one.arcgis_services = [('Pallet', 'MapServer')]
        pallet_one.requires_processing = Mock(return_value=True)

        pallet_two = Pallet()
        pallet_two.copy_data = ['C:\\MapData\\one.gdb', three]
        pallet_two.arcgis_services = [('Pallet', 'MapServer')]
        pallet_two.requires_processing = Mock(return_value=True)

        pallet_three = Pallet()
        pallet_three.copy_data = ['C:\\MapData\\four', three]

        lift.copy_data([pallet_one, pallet_two, pallet_three], [pallet_one, pallet_two, pallet_three], ['dest1', 'dest2'])

        self.assertEqual(copytree_mock.call_count, 6)
        self.assertEqual(rmtree_mock.call_count, 6)
        self.assertEqual(compact_mock.call_count, 3)
        self.assertEqual(lightswitch_mock().turn_on.call_count, 3)
        self.assertEqual(lightswitch_mock().turn_off.call_count, 3)

    def test_create_report_object(self):
        p1 = Pallet()
        p1.success = (False, '')

        p2 = Pallet()
        p3 = Pallet()

        report = lift.create_report_object([p1, p2, p3], 10)

        self.assertEqual(report['total_pallets'], 3)
        self.assertEqual(report['num_success_pallets'], 2)

    def test_hydrate_copy_structures_with_empty_is_ok(self):
        pallets = [Pallet(), Pallet()]
        pallets[0].requires_processing = Mock(return_value=True)
        pallets[1].requires_processing = Mock(return_value=True)

        lift._hydrate_copy_structures([], pallets)

    def test_hydrate_copy_structures_unions_arcgis_services(self):
        pallets = [Pallet(), Pallet()]

        pallets[0].requires_processing = Mock(return_value=True)
        pallets[1].requires_processing = Mock(return_value=True)

        pallets[0].copy_data = ['location']
        pallets[1].copy_data = ['location']

        pallets[0].arcgis_services = [('a', 'a'), ('b', 'b')]
        pallets[1].arcgis_services = [('a', 'a'), ('c', 'c')]

        copy_workspaces, source_to_services, destination_to_pallet = lift._hydrate_copy_structures([], pallets)
        self.assertEqual(source_to_services['location'], set([('a', 'a'), ('b', 'b'), ('c', 'c')]))

    def test_hydrate_copy_structures_unions_all_copy_data_locations(self):
        pallets = [Pallet(), Pallet(), Pallet()]

        pallets[0].requires_processing = Mock(return_value=True)
        pallets[1].requires_processing = Mock(return_value=True)
        pallets[2].requires_processing = Mock(return_value=True)

        pallets[0].copy_data = ['location']
        pallets[1].copy_data = ['location']
        pallets[2].copy_data = ['location2']

        copy_workspaces, source_to_services, destination_to_pallet = lift._hydrate_copy_structures(pallets, pallets)
        self.assertEqual(copy_workspaces, set(['location', 'location2']))

    def test_hydrate_copy_structures_creates_destination_dictionary(self):
        pallets = [Pallet(), Pallet(), Pallet()]

        pallets[0].requires_processing = Mock(return_value=True)
        pallets[1].requires_processing = Mock(return_value=True)
        pallets[2].requires_processing = Mock(return_value=True)

        pallets[0].copy_data = ['location']
        pallets[1].copy_data = ['location']
        pallets[2].copy_data = ['location2']

        copy_workspaces, source_to_services, destination_to_pallet = lift._hydrate_copy_structures([], pallets)
        self.assertEqual(destination_to_pallet['location'], [pallets[0], pallets[1]])
        self.assertEqual(destination_to_pallet['location2'], [pallets[2]])

    def test_hydrate_copy_structures_prevents_duplicate_copy_datas(self):
        pallets = [Pallet(), Pallet(), Pallet()]

        pallets[0].requires_processing = Mock(return_value=True)
        pallets[1].requires_processing = Mock(return_value=True)
        pallets[2].requires_processing = Mock(return_value=True)

        pallets[0].copy_data = ['location']
        pallets[1].copy_data = ['Location']
        pallets[2].copy_data = ['location2']

        copy_workspaces, source_to_services, destination_to_pallet = lift._hydrate_copy_structures(pallets, pallets)
        copy_workspaces = list(copy_workspaces)

        self.assertEqual(len(copy_workspaces), 2)
        self.assertIn('location', copy_workspaces)
        self.assertIn('location2', copy_workspaces)

    def test_hydrate_copy_structures_only_includes_copy_data_in_specific_pallets(self):
        pallets = [Pallet(), Pallet(), Pallet()]

        pallets[0].requires_processing = Mock(return_value=True)

        pallets[0].copy_data = ['location']
        pallets[0].arcgis_services = ['service1']
        pallets[1].copy_data = ['Location']
        pallets[1].arcgis_services = ['service2']
        pallets[2].copy_data = ['location2']

        copy_workspaces, source_to_services, destination_to_pallet = lift._hydrate_copy_structures(pallets[:1], pallets)
        copy_workspaces = list(copy_workspaces)

        self.assertEqual(copy_workspaces[0], 'location')
        self.assertEqual(len(copy_workspaces), 1)
        self.assertEqual(destination_to_pallet['location'], [pallets[0], pallets[1]])
        self.assertEqual(destination_to_pallet['location2'], [pallets[2]])
        self.assertEqual(source_to_services['location'], set(['service2', 'service1']))
