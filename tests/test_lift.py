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

        lift.process_pallets([ready_pallet, ready_pallet])

        self.assertEqual(ready_pallet.ship.call_count, 2)

    def test_process_pallets_all_requires_processing(self):
        requires_pallet = self.PalletMock()
        requires_pallet.is_ready_to_ship.return_value = True
        requires_pallet.requires_processing.return_value = True

        lift.process_pallets([requires_pallet, requires_pallet])

        self.assertEqual(requires_pallet.process.call_count, 2)

    def test_process_pallets_mixed_bag(self):
        pallet1 = Mock(Pallet)('one')
        pallet1.is_ready_to_ship = Mock(return_value=True)
        pallet1.requires_processing = Mock(return_value=False)

        pallet2 = Mock(Pallet)('two')
        pallet2.is_ready_to_ship = Mock(return_value=False)
        pallet2.requires_processing = Mock(return_value=False)

        pallet3 = Mock(Pallet)('three')
        pallet3.is_ready_to_ship = Mock(return_value=True)
        pallet3.requires_processing = Mock(return_value=True)

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

        lift.process_pallets([pallet])

        self.assertEqual(pallet.success, (False, 'process error'))

    def test_process_pallets_handles_ship_exception(self):
        pallet = self.PalletMock()
        pallet.ship.side_effect = Exception('ship error')

        lift.process_pallets([pallet])

        self.assertEqual(pallet.success, (False, 'ship error'))

    @patch('forklift.lift.Describe')
    @patch('forklift.lift.Compact_management')
    @patch('forklift.lift.path.exists')
    @patch('shutil.move')
    @patch('shutil.copytree')
    def test_copy_data(self, copytree_mock, rmtree_mock, exists_mock, compact_mock, describe_mock):
        describe_mock.side_effect = describe_side_effect
        exists_mock.return_value = True
        three = 'C:\\MapData\\three.gdb'
        two = 'C:\\MapData\\two.gdb'

        class CopyPalletOne(Pallet):

            def __init__(self):
                super(CopyPalletOne, self).__init__()

                self.copy_data = ['C:\\MapData\\one.gdb', two]

        pallet_one = CopyPalletOne()
        pallet_one.requires_processing = Mock(return_value=True)

        class CopyPalletTwo(Pallet):

            def __init__(self):
                super(CopyPalletTwo, self).__init__()

                self.copy_data = ['C:\\MapData\\one.gdb', three]

        pallet_two = CopyPalletTwo()
        pallet_two.requires_processing = Mock(return_value=True)

        class CopyPalletThree(Pallet):

            def __init__(self):
                super(CopyPalletThree, self).__init__()

                self.copy_data = ['C:\\MapData\\four', three]

        lift.copy_data([pallet_one, pallet_two, CopyPalletThree()], ['dest1', 'dest2'])

        self.assertEqual(copytree_mock.call_count, 6)
        self.assertEqual(rmtree_mock.call_count, 6)
        self.assertEqual(compact_mock.call_count, 3)

    @patch('forklift.lift.Describe')
    @patch('forklift.lift.Compact_management')
    @patch('shutil.move')
    @patch('shutil.copytree')
    def test_copy_data_error(self, copytree_mock, rmtree_mock, compact_mock, describe_mock):
        describe_mock.side_effect = describe_side_effect
        error_message = 'there was an error'
        copytree_mock.side_effect = Exception(error_message)

        class CopyPalletOne(Pallet):

            def __init__(self):
                super(CopyPalletOne, self).__init__()

                self.copy_data = ['C:\\MapData\\one.gdb']

        pallet = CopyPalletOne()
        pallet.requires_processing = Mock(return_value=True)

        lift.copy_data([pallet], ['hello'])

        self.assertEqual(pallet.success, (False, error_message))

    @patch('forklift.lift.LightSwitch', autospec=True)
    @patch('forklift.lift.Describe')
    @patch('forklift.lift.Compact_management')
    @patch('forklift.lift.path.exists')
    @patch('shutil.move')
    @patch('shutil.copytree')
    def test_copy_data_turns_off_and_on_services(self, copytree_mock, rmtree_mock, exists_mock, compact_mock,
                                                 describe_mock, lightswitch_mock):
        describe_mock.side_effect = describe_side_effect
        exists_mock.return_value = True
        three = 'C:\\MapData\\three.gdb'
        two = 'C:\\MapData\\two.gdb'

        class CopyPalletOne(Pallet):

            def __init__(self):
                super(CopyPalletOne, self).__init__()

                self.copy_data = ['C:\\MapData\\one.gdb', two]
                self.arcgis_services = [('Pallet', 'MapServer')]

        class CopyPalletTwo(Pallet):

            def __init__(self):
                super(CopyPalletTwo, self).__init__()

                self.copy_data = ['C:\\MapData\\one.gdb', three]
                self.arcgis_services = [('Pallet', 'MapServer')]

        class CopyPalletThree(Pallet):

            def __init__(self):
                super(CopyPalletThree, self).__init__()

                self.copy_data = ['C:\\MapData\\four', three]

        pallet_one = CopyPalletOne()
        pallet_one.requires_processing = Mock(return_value=True)

        pallet_two = CopyPalletTwo()
        pallet_two.requires_processing = Mock(return_value=True)

        lift.copy_data([pallet_one, pallet_two, CopyPalletThree()], ['dest1', 'dest2'])

        self.assertEqual(copytree_mock.call_count, 6)
        self.assertEqual(rmtree_mock.call_count, 6)
        self.assertEqual(compact_mock.call_count, 3)
        self.assertEqual(len(lightswitch_mock().turn_on.mock_calls), 3)
        self.assertEqual(len(lightswitch_mock().turn_off.mock_calls), 3)

    def test_create_report_object(self):
        p1 = Pallet()
        p1.success = (False, '')

        p2 = Pallet()
        p3 = Pallet()

        report = lift.create_report_object([p1, p2, p3], 10)

        self.assertEqual(report['total_pallets'], 3)
        self.assertEqual(report['num_success_pallets'], 2)
