#!/usr/bin/env python
# * coding: utf8 *
'''
lift.py

A module that contains methods to handle pallets
'''

import logging
import seat
import shutil
from arcpy import Compact_management, Describe
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


def copy_data(pallets, copy_destinations):
    '''pallets: Pallets[]

    Loop over all of the pallets and extract the distinct copy_data workspaces.
    Then loop over all of the copy_data workspaces and copy them to copy_destinations as defined in the config.'''
    copy_workspaces = []
    for pallet in pallets:
        if pallet.is_ready_to_ship():
            copy_workspaces = copy_workspaces + pallet.copy_data
    copy_workspaces = set(copy_workspaces)

    for source in copy_workspaces:
        if Describe(source).workspaceFactoryProgID.startswith('esriDataSourcesGDB.FileGDBWorkspaceFactory'):
            log.info('compacting %s', source)
            Compact_management(source)

        for destination in copy_destinations:
            destination_workspace = path.join(destination, path.basename(source))

            log.info('copying {} to {}...'.format(source, destination_workspace))
            start_seconds = clock()
            try:
                if path.exists(destination_workspace):
                    log.debug('%s exists moving', destination_workspace)
                    shutil.move(destination_workspace, destination_workspace + 'x')

                log.debug('copying source to destination')
                shutil.copytree(source, destination_workspace)

                if path.exists(destination_workspace + 'x'):
                    log.debug('removing temporary gdb: %s', destination_workspace + 'x')
                    shutil.rmtree(destination_workspace + 'x')

                log.info('copy successful in %s', seat.format_time(clock() - start_seconds))
            except Exception as e:
                try:
                    #: if there was a problem and the temp gdb exists, put it back
                    if path.exists(destination_workspace) and path.exists(destination_workspace + 'x'):
                        log.debug('%s cleaning up.', destination_workspace)
                        shutil.rmtree(destination_workspace)
                        shutil.move(destination_workspace + 'x', destination_workspace)
                except Exception:
                    log.error('%s might be in a corrupted state', destination_workspace, exec_info=True)

                pallet.success = (False, str(e))
                log.error('there was an error copying %s to %s', source, destination_workspace, exc_info=True)


def create_report_object(pallets, elapsed_time):
    reports = [pallet.get_report() for pallet in pallets]

    return {'total_pallets': len(reports),
            'num_success_pallets': len(filter(lambda p: p['success'], reports)),
            'pallets': reports,
            'total_time': elapsed_time}
