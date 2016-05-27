#!/usr/bin/env python
# * coding: utf8 *
'''
lift.py

A module that contains methods to handle pallets
'''


def process_crates_for(pallets, update_def):
    '''
    pallets: Pallet[]
    update_def: Function

    Calls update_def on all crates (excluding duplicates) in pallets
    '''
    processed_crates = {}

    for pallet in pallets:
        for crate in pallet.get_crates():
            if crate.destination in processed_crates:
                crate.set_result(processed_crates[crate.destination])
            else:
                processed_crates[crate.destination] = crate.set_result(update_def(crate, pallet.validate_crate))


def process_pallets(pallets):
    reports = []
    for pallet in pallets:
        if pallet.is_ready_to_ship():  #: checks for schema changes or errors
            if pallet.requires_processing():  #: checks for data that was updated
                pallet.process()
            pallet.ship()

        reports.append(pallet.get_report())

    return reports
