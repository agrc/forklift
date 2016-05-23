#!/usr/bin/env python
# * coding: utf8 *
'''
test_forklift.py

A module for testing lift.py
'''

import unittest
from forklift import lift
from forklift.models import Pallet, Crate
from mock import Mock


class TestLift(unittest.TestCase):

    def setUp(self):
        self.PalletMock = Mock(Pallet)

    def test_process_crate_for_set_results(self):
        crate1 = Crate('', '', 'a', '')
        crate2 = Crate('', '', 'b', '')
        pallet = Pallet()
        pallet._crates = [crate1, crate2]
        update_def = Mock(return_value=Crate.UPDATED)
        lift.process_crates_for([pallet], update_def)

        self.assertEquals(update_def.call_count, 2)
        self.assertEquals(crate1.result, Crate.UPDATED)
        self.assertEquals(crate2.result, Crate.UPDATED)

    def test_process_crate_doesnt_call_update_def_on_duplicate_crates(self):
        crate1 = Crate('', '', 'a', '')
        crate2 = Crate('', '', 'a', '')
        pallet = Pallet()
        pallet._crates = [crate1, crate2]
        update_def = Mock(return_value=Crate.UPDATED)
        lift.process_crates_for([pallet], update_def)

        self.assertEquals(update_def.call_count, 1)
        self.assertEquals(crate1.result, Crate.UPDATED)
        self.assertEquals(crate2.result, Crate.UPDATED)

    def test_process_pallets_all_ready_to_ship(self):
        ready_pallet = self.PalletMock()
        ready_pallet.is_ready_to_ship.return_value = True

        lift.process_pallets([ready_pallet, ready_pallet])

        self.assertEquals(ready_pallet.ship.call_count, 2)

    def test_process_pallets_all_requires_processing(self):
        requires_pallet = self.PalletMock()
        requires_pallet.is_ready_to_ship.return_value = True
        requires_pallet.requires_processing.return_value = True

        lift.process_pallets([requires_pallet, requires_pallet])

        self.assertEquals(requires_pallet.process.call_count, 2)

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

    def test_process_pallets_returns_reports(self):
        reports_pallet = self.PalletMock()
        reports_pallet.get_report.return_value = 'hello'

        result = lift.process_pallets([reports_pallet, reports_pallet])

        self.assertEquals(result, ['hello', 'hello'])
