#!/usr/bin/env python
# * coding: utf8 *
'''
lift.py

A module that contains methods to handle pallets
'''

import logging
import seat
import shutil
from arcgis import LightSwitch
from arcpy import Compact_management, Describe
from os import makedirs
from os import path
from os import remove
from os import walk
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
            try:
                pallet.build()
            except Exception as e:
                pallet.success = (False, e.message)
                log.error('error building pallet: %s for pallet: %r', e.message, pallet, exc_info=True)

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
    copy_workspaces = set([])
    source_to_services = {}
    lightswitch = LightSwitch()

    for pallet in pallets:
        if not pallet.requires_processing():
            continue

        copy_workspaces |= set(pallet.copy_data)  # noqa

        try:
            #: try to get arcgis_services
            services = pallet.arcgis_services

            #: loop over all the copy_data workspaces
            for workspace in pallet.copy_data:
                source_to_services.setdefault(workspace, set([]))
                #: add the service types to the workspace
                for service in services:
                    source_to_services[workspace].add(service)
        except AttributeError:
            #: pallet has no dependent services
            continue

    for source in copy_workspaces:
        if Describe(source).workspaceFactoryProgID.startswith('esriDataSourcesGDB.FileGDBWorkspaceFactory'):
            log.info('compacting %s', source)
            Compact_management(source)

        services = []
        if source in source_to_services:
            services = source_to_services[source]
            log.info('stopping %s services dependent upon %s.', len(services), source)

            for service in services:
                log.debug('stopping %s.%s', service[0], service[1])
                lightswitch.turn_off(service[0], service[1])

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
                    #: There is still a lock?
                    #: The service probably wasn't shut down
                    #: if there was a problem and the temp gdb exists
                    #: since we couln't delete it before we probably can't delete it now
                    #: so take what is in x and copy it over what it can in the original
                    #: that _should_ leave the gdb in a functioning state
                    if path.exists(destination_workspace) and path.exists(destination_workspace + 'x'):
                        log.debug('cleaning up %s', destination_workspace)
                        _copy_with_overwrite(destination_workspace + 'x', destination_workspace)
                        shutil.rmtree(destination_workspace + 'x')
                except Exception:
                    log.error('%s might be in a corrupted state', destination_workspace, exc_info=True)

                pallet.success = (False, str(e))
                log.error('there was an error copying %s to %s', source, destination_workspace, exc_info=True)

        for service in services:
            log.debug('starting %s.%s', service[0], service[1])
            lightswitch.turn_on(service[0], service[1])


def create_report_object(pallets, elapsed_time):
    reports = [pallet.get_report() for pallet in pallets]

    return {'total_pallets': len(reports),
            'num_success_pallets': len(filter(lambda p: p['success'], reports)),
            'pallets': reports,
            'total_time': elapsed_time}


def _copy_with_overwrite(source, destination):
    for src_dir, dirs, files in walk(source):
        dst_dir = src_dir.replace(source, destination, 1)

        if not path.exists(dst_dir):
            makedirs(dst_dir)

        for file_ in files:
            src_file = path.join(src_dir, file_)
            dst_file = path.join(dst_dir, file_)

            try:
                if path.exists(dst_file):
                    remove(dst_file)
            except:
                #: shouldn't matter a whole lot
                pass

            try:
                shutil.move(src_file, dst_dir)
            except:
                #: shouldn't matter a whole lot
                pass
