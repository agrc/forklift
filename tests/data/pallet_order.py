#!/usr/bin/env python
# * coding: utf8 *
'''
pallet_order.py

A module that contains tests for pallet execution order
'''

from forklift.models import Pallet


class PalletA(Pallet):
    pass


class PalletC(Pallet):
    pass


class PalletB(Pallet):
    pass
