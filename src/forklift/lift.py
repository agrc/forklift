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
    update_def: Function. core.update

    Calls update_def on all crates (excluding duplicates) in pallets
    '''
    processed_crates = {}

    log.info('processing crates for all pallets.')

    for pallet in pallets:
        log.debug('processing pallet %r', pallet)
        for crate in pallet.get_crates():
            if crate.destination not in processed_crates:
                log.debug('processing crate %r', crate)
                start_seconds = clock()

                processed_crates[crate.destination] = crate.set_result(update_def(crate, pallet.validate_crate))

                log.debug('finished crate %s',  seat.format_time(clock() - start_seconds))
            else:
                log.debug('skipping crate %r', crate)

                crate.set_result(processed_crates[crate.destination])


def process_pallets(pallets):
    reports = []

    log.info('processing and shipping pallets...')

    for pallet in pallets:
        if pallet.is_ready_to_ship():  #: checks for schema changes or errors
            if pallet.requires_processing():  #: checks for data that was updated
                log.debug('processing pallet %r', pallet)
                start_seconds = clock()

                try:
                    pallet.process()
                except Exception as e:
                    log.error('error proccessing pallet: %s for pallet: %r', e.message, pallet, exc_info=True)

                log.debug('processed pallet %s', seat.format_time(clock() - start_seconds))

            log.debug('shipping pallet...')
            start_seconds = clock()

            try:
                pallet.ship()
                log.debug('shipped pallet %s', seat.format_time(clock() - start_seconds))
            except Exception as e:
                log.error('error shipping pallet: %s for pallet: %r', e.message, pallet, exc_info=True)

        reports.append(pallet.get_report())

    return reports
