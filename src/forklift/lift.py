#!/usr/bin/env python
# * coding: utf8 *
'''
lift.py

A module that contains methods to handle pallets
'''

import logging
import seat
import settings
from time import clock

log = logging.getLogger(settings.LOGGER)


def process_crates_for(pallets, update_def):
    '''
    pallets: Pallet[]
    update_def: Function

    Calls update_def on all crates (excluding duplicates) in pallets
    '''
    processed_crates = {}

    log.info('processing crates for all pallets.')

    for pallet in pallets:
        log.debug('processing pallet %r', pallet)
        for crate in pallet.get_crates():
            if crate.destination in processed_crates:
                log.debug('processing crate %r', crate)
                start_seconds = clock()

                crate.set_result(processed_crates[crate.destination])

                log.debug('finished crate %s',  seat.format_time(clock() - start_seconds))
            else:
                log.debug('skipping crate %r', crate)

                processed_crates[crate.destination] = crate.set_result(update_def(crate, pallet.validate_crate))


def process_pallets(pallets):
    reports = []

    log.info('processing and shipping pallets')

    for pallet in pallets:
        if pallet.is_ready_to_ship():  #: checks for schema changes or errors
            if pallet.requires_processing():  #: checks for data that was updated
                log.debug('processing pallet %r', pallet)
                start_seconds = clock()

                pallet.process()

                log.debug('processed pallet %s', seat.format_time(clock() - start_seconds))

            log.debug('shipping pallet')
            start_seconds = clock()

            pallet.ship()

            log.debug('shipped pallet %s', seat.format_time(clock() - start_seconds))

        reports.append(pallet.get_report())

    return reports
