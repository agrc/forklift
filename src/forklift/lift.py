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
from arcpy import Compact_management
from arcpy import Describe
from forklift.models import Crate
from os import makedirs
from os import path
from os import remove
from os import walk
from time import clock

log = logging.getLogger('forklift')


def process_crates_for(pallets, update_def, configuration='Production'):
    '''
    pallets: Pallet[]
    update_def: Function. core.update
    configuration: string. Production, Staging, Dev

    Calls update_def on all crates (excluding duplicates) in pallets
    '''
    processed_crates = {}

    log.info('processing crates for %d pallets.', len(pallets))

    for pallet in pallets:
        log.info('processing crates for pallet: %s', pallet.name)
        log.debug('%r', pallet)

        try:
            log.debug('building pallet: %s', pallet.name)
            pallet.build(configuration)
        except Exception as e:
            pallet.success = (False, e.message)
            log.error('error building pallet: %s for pallet: %r', e.message, pallet, exc_info=True)
            continue

        for crate in pallet.get_crates():
            log.info('crate: %s', crate.destination_name)
            if crate.result[0] == Crate.INVALID_DATA:
                log.warn('result: %s', crate.result)
                continue

            if crate.destination not in processed_crates:
                log.debug('%r', crate)
                start_seconds = clock()

                processed_crates[crate.destination] = crate.set_result(update_def(crate, pallet.validate_crate))

                log.debug('finished crate %s', seat.format_time(clock() - start_seconds))
                log.info('result: %s', crate.result)
            else:
                log.info('skipping crate')

                crate.set_result(processed_crates[crate.destination])


def process_pallets(pallets):
    '''pallets: [Pallet]

    Loop over all pallets, check if data has changed and determine whether to call process.
    Finally, determine whether to call ship.
    '''

    log.info('processing and shipping pallets...')

    for pallet in pallets:
        if pallet.is_ready_to_ship():  #: checks for schema changes or errors
            if pallet.requires_processing() and pallet.success[0]:  #: checks for data that was updated
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


def copy_data(specific_pallets, all_pallets, config_copy_destinations):
    #: we're lifting everything
    if len(specific_pallets) == 0:
        specific_pallets = all_pallets

    #: filter out pallets whose data did not change
    specific_pallets = [pallet for pallet in specific_pallets if pallet.requires_processing() is True]

    #: no pallets to process. we are done here
    if len(specific_pallets) == 0:
        return

    lightswitch = LightSwitch()
    services_affected, data_being_moved, destination_to_pallet = _hydrate_data_structures(specific_pallets, all_pallets)

    log.info('stopping %s dependent services.', len(services_affected))
    for service in services_affected:
        log.debug('stopping %s.%s', service[0], service[1])
        status = lightswitch.turn_off(service[0], service[1])

        if not status[0]:
            log.warn('service %s did not stop: %s', service[0], status[1])

    for source in data_being_moved:
        if Describe(source).workspaceFactoryProgID.startswith('esriDataSourcesGDB.FileGDBWorkspaceFactory'):
            log.info('compacting %s', source)
            Compact_management(source)

        for destination in config_copy_destinations:
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

                if source.lower() in destination_to_pallet:
                    for pallet in destination_to_pallet[source.lower()]:
                        pallet.success = (False, str(e))

                log.error('there was an error copying %s to %s', source, destination_workspace, exc_info=True)

    for service in services_affected:
        log.debug('starting %s.%s', service[0], service[1])
        status = lightswitch.turn_on(service[0], service[1])

        if not status[0]:
            log.error('service %s did not start: %s', service[0], status[1])


def _hydrate_data_structures(specific_pallets, all_pallets):
    services_affected = set([])
    data_being_moved = set([])
    destination_to_pallet = {}

    #: get the services affected by this pallet
    for pallet in specific_pallets:
        for service in pallet.arcgis_services:
            services_affected.add(service)

        for workspace in pallet.copy_data:
            workspace = workspace.lower()
            data_being_moved.add(workspace)

    #: append the services that share datasources
    for pallet in all_pallets:
        for workspace in pallet.copy_data:
            workspace = workspace.lower()
            if workspace not in data_being_moved:
                continue

            for service in pallet.arcgis_services:
                services_affected.add(service)

            destination_to_pallet.setdefault(workspace, []).append(pallet)
            break

    return services_affected, data_being_moved, destination_to_pallet
