#!/usr/bin/env python
# * coding: utf8 *
'''
lift.py

A module that contains methods to handle pallets
'''

import logging
import seat
import shutil
from os import path
from time import clock

log = logging.getLogger('forklift')


def process_crates_for(pallets, update_def):
    '''
    pallets: Pallet[]
    update_def: Function. core.update

    Calls update_def on all crates (excluding duplicates) in pallets
    '''
    processed_crates = {}

    log.info('processing crates for %d pallets.', len(pallets))

    for pallet in pallets:
        log.info('processing crates for pallet: %s', pallet.name)
        log.debug('%r', pallet)
        for crate in pallet.get_crates():
            if crate.destination not in processed_crates:
                log.info('crate: %s', crate.destination_name)
                log.debug('%r', crate)
                start_seconds = clock()

                processed_crates[crate.destination] = crate.set_result(update_def(crate, pallet.validate_crate))

                log.debug('finished crate %s', seat.format_time(clock() - start_seconds))
                log.info('result: %s', crate.result)
            else:
                log.debug('skipping crate %r', crate)

                crate.set_result(processed_crates[crate.destination])


def process_pallets(pallets):
    '''pallets: [Pallet]

    Loop over all pallets, check if data has changed and determine whether to call process.
    Finally, determine whether to call ship.
    '''
    reports = []

    log.info('processing and shipping pallets...')

    for pallet in pallets:
        if pallet.is_ready_to_ship():  #: checks for schema changes or errors
            if pallet.requires_processing():  #: checks for data that was updated
                log.info('processing pallet: %s', pallet.name)
                log.debug('%r', pallet)
                start_seconds = clock()

                try:
                    pallet.process()
                except Exception as e:
                    pallet.success = (False, e.message)
                    log.error('error proccessing pallet: %s for pallet: %r', e.message, pallet, exc_info=True)

                log.debug('processed pallet %s', seat.format_time(clock() - start_seconds))

            log.debug('shipping pallet...')
            start_seconds = clock()

            try:
                log.info('shipping pallet: %s', pallet.name)
                pallet.ship()
                log.debug('shipped pallet %s', seat.format_time(clock() - start_seconds))
            except Exception as e:
                pallet.success = (False, e.message)
                log.error('error shipping pallet: %s for pallet: %r', e.message, pallet, exc_info=True)

        reports.append(pallet.get_report())

    return reports


def copy_data(pallets, copy_destinations):
    '''pallets: Pallets[]

    Loop over all of the pallets and extra the distinct copy_data workspaces.
    Loop over all of the copy_data workspaces and copy them to copy_destinations as defined in the config.'''
    copy_workspaces = []
    for pallet in pallets:
        if pallet.is_ready_to_ship():
            copy_workspaces = copy_workspaces + pallet.copy_data
    copy_workspaces = set(copy_workspaces)

    for source in copy_workspaces:
        for destination in copy_destinations:
            destination_workspace = path.join(destination, path.basename(source))

            shutil.rmtree(destination_workspace)
            shutil.copytree(source, destination_workspace)


def create_report_object(pallet_reports, elapsed_time):
    return {'total_pallets': len(pallet_reports),
            'num_success_pallets': len(filter(lambda p: p['success'], pallet_reports)),
            'pallets': pallet_reports,
            'total_time': elapsed_time}
