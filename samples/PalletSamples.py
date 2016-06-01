#!/usr/bin/env python
# * coding: utf8 *
'''
PalletSamples.py

A module that contains a simple Pallet to test forklift
'''

from arcpy import env
from forklift.models import Pallet


class StringCratePallet(Pallet):

    def __init__(self):
        super(StringCratePallet, self).__init__()

        destination_workspace = env.scratchGDB
        source_workspace = 'Database Connections\\agrc@sgid10.sde'

        self.add_crates(['BOUNDARIES.Counties'], {'source_workspace': source_workspace,
                                                  'destination_workspace': destination_workspace})


class ExplicitCratePallet(Pallet):

    def __init__(self):
        super(ExplicitCratePallet, self).__init__()

        destination_workspace = env.scratchGDB
        source_workspace = 'Database Connections\\agrc@sgid10.sde'

        crate_info = ('SGID10.GEOSCIENCE.AvalanchePaths', source_workspace, destination_workspace, 'AvyPaths')
        self.add_crate(crate_info)
