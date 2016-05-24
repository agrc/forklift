#!/usr/bin/env python
# * coding: utf8 *
'''
forklift.py

A module that contains methods to handle pallets
'''

import core


def process_crates(pallets):
    processed_crates = {}

    for pallet in pallets:
        for crate in pallet.crates:
            if crate.name in processed_crates:
                crate.set_result(process_crates[crate.name])
            else:
                process_crates[crate.name] = crate.set_result(core.update(crate, pallet.validate_crate))
                #: core returns updated, schema change, no update needed or error during update


def process_pallets(pallets):
    reports = []
    for pallet in pallets:
        if pallet.is_ready_for_ship():  #: checks for schema changes or errors
            if pallet.requires_processing():  #: checks for data that was updated
                pallet.process()
            pallet.ship()

        reports.append(pallet.get_report())

    return reports
