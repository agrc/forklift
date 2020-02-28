#!/usr/bin/env python
# * coding: utf8 *
'''
ChangeDetectionPallet.py
A module containing an sample of a pallet that uses change detection.j

Note: In order for this pallet to use change detection, the `changeDetectionTables` config prop needs to
have `UPDATE_TESTS.sde\\ChangeDetection` in it's array.
'''
from os.path import join

import arcpy
from forklift.models import Pallet


class ChangeDetectionPallet(Pallet):
    def build(self, configuration):
        self.add_crate(('ChangeDetectionPallet', join(self.garage, 'UPDATE_TESTS.sde'), arcpy.env.scratchGDB))
