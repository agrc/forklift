#!/usr/bin/env python
# * coding: utf8 *
'''
lift.py

A module that contains methods to handle pallets
'''

import logging
import shutil
import socket
from os import makedirs, path, remove, walk
from time import clock

import arcpy
from forklift.models import Crate

from . import seat
from .core import hash_field

log = logging.getLogger('forklift')


def process_checklist(config):
    _remove_if_exists(config.get_config_prop('dropoffLocation'))
    _create_if_not_exists([config.get_config_prop('hashLocation'), config.get_config_prop('dropoffLocation')])


def _remove_if_exists(location):
    if not path.exists(location):
        return

    shutil.rmtree(location)


def _create_if_not_exists(locations):
    for location in locations:
        if path.exists(location):
            continue

        makedirs(location)


def prepare_packaging_for_pallets(pallets):
    '''
    pallets: Pallet[]

    Calls prepare_packaging for pallets
    '''
    log.info('preparing packing for %d pallets', len(pallets))

    for pallet in pallets:
        try:
            log.debug('prepare packaging for: %r', pallet)
            with seat.timed_pallet_process(pallet, 'prepare_packaging'):
                pallet.prepare_packaging()
        except Exception as e:
            pallet.success = (False, e)
            log.error('error preparing packaging: %s for pallet: %r', e, pallet, exc_info=True)


def process_crates_for(pallets, update_def):
    '''
    pallets: Pallet[]
    update_def: Function. core.update

    Calls update_def on all crates (excluding duplicates) in pallets
    '''
    processed_crates = {}

    log.info('processing crates for %d pallets.', len(pallets))

    for pallet in pallets:
        with seat.timed_pallet_process(pallet, 'process_crates'):
            log.info('processing crates for pallet: %r', pallet)

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


def process_pallets(pallets, is_post_copy=False):
    '''
    pallets: Pallet[]
    is_post_copy: Boolean

    Loop over all pallets, check if data has changed and determine whether to process.
    Call `process` if this is not the post copy. Otherwise call `post_copy_process`.
    Finally, call ship.
    '''

    if not is_post_copy:
        verb = 'processing'
    else:
        verb = 'post copy processing'

    log.info('%s pallets...', verb)

    for pallet in pallets:
        try:
            if pallet.is_ready_to_ship():  #: checks for schema changes or errors
                if pallet.requires_processing() and pallet.success[0]:  #: checks for data that was updated
                    log.info('%s pallet: %r', verb, pallet)
                    start_seconds = clock()

                    arcpy.ResetEnvironments()
                    arcpy.ClearWorkspaceCache_management()
                    if not is_post_copy:
                        with seat.timed_pallet_process(pallet, 'process'):
                            pallet.process()
                    else:
                        with seat.timed_pallet_process(pallet, 'post_copy_process'):
                            pallet.post_copy_process()

                    log.debug('%s pallet %s', verb.replace('ing', 'ed'), seat.format_time(clock() - start_seconds))

                # if not is_post_copy:
                #     start_seconds = clock()
                #
                #     log.info('shipping pallet: %r', pallet)
                #     arcpy.ResetEnvironments()
                #     arcpy.ClearWorkspaceCache_management()
                #     with seat.timed_pallet_process(pallet, 'ship'):
                #         pallet.ship()
                #     log.debug('shipped pallet %s', seat.format_time(clock() - start_seconds))
        except Exception as e:
            pallet.success = (False, e)
            log.error('error %s pallet: %s for pallet: %r', verb, e, pallet, exc_info=True)


def dropoff_data(specific_pallets, all_pallets, dropoff_location):
    '''
    specific_pallets: Pallet[]
    all_pallets: Pallet[]
    config_copy_destinations: string[]

    Copies scrubbed hashed data to `dropoff_location` that is ready to go to production.
    '''
    #: we're acting on all pallets
    if len(specific_pallets) == 0:
        specific_pallets = all_pallets

    #: filter out pallets whose data did not change
    filtered_specific_pallets = []
    for pallet in specific_pallets:
        try:
            if pallet.requires_processing() is True:
                filtered_specific_pallets.append(pallet)
        except Exception:
            #: skip, we'll see the error in the report from process_pallets
            pass

    #: no pallets with data updates. we are done here
    if len(filtered_specific_pallets) == 0:
        return

    #: data_source eg: C:\forklift\data\hashed\boundaries_utm.gdb
    destination_and_pallet = _get_locations_for_dropoff(filtered_specific_pallets, all_pallets)
    _move_to_dropoff(destination_and_pallet, dropoff_location)


def gift_wrap(location):
    arcpy.env.workspace = location

    workspaces = arcpy.ListWorkspaces('*', 'FileGDB')

    [_remove_hash_from_workspace(workspace) for workspace in workspaces]
    [arcpy.management.Compact(workspace) for workspace in workspaces]


def _move_to_dropoff(destination_and_pallet, dropoff_location):
    '''
    destination_and_pallet: string, pallet[]
    dropoff_location: string'''
    for data_source in destination_and_pallet:
        gdb_name = path.basename(data_source)
        log.info('copying {} to {}...'.format(data_source, path.join(dropoff_location, gdb_name)))
        start_seconds = clock()
        try:
            log.debug('copying source to destination')
            shutil.copytree(data_source, path.join(dropoff_location, gdb_name), ignore=shutil.ignore_patterns('*.lock'))
            log.info('copy successful in %s', seat.format_time(clock() - start_seconds))
        except Exception as e:
            if data_source.lower() in destination_and_pallet:
                for pallet in destination_and_pallet[data_source.lower()]:
                    pallet.success = (False, str(e))

            log.error('there was an error copying %s to %s', data_source, path.join(dropoff_location, gdb_name), exc_info=True)


def get_lift_status(pallets, elapsed_time, git_errors):
    reports = [pallet.get_report() for pallet in pallets]

    return {'hostname': socket.gethostname(),
            'total_pallets': len(reports),
            'num_success_pallets': len([p for p in reports if p['success']]),
            'git_errors': git_errors,
            'pallets': reports,
            'total_time': elapsed_time}


def _copy_with_overwrite(source, destination):
    log.info('copying with overwrite: %s to %s', source, destination)
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
            except Exception:
                #: shouldn't matter a whole lot
                pass

            try:
                shutil.copy2(src_file, dst_dir)
            except Exception:
                #: shouldn't matter a whole lot
                pass


def copy_data(specific_pallets, all_pallets, config_copy_destinations):
    '''
    specific_pallets: Pallet[]
    all_pallets: Pallet[]
    config_copy_destinations: string[]

    Copies databases from either `copy_data` or `static_data` to `config_copy_destinations`.
    '''
    #: we're lifting everything
    if len(specific_pallets) == 0:
        specific_pallets = all_pallets

    #: filter out pallets whose data did not change
    filtered_specific_pallets = []
    for pallet in specific_pallets:
        try:
            if pallet.requires_processing() is True:
                filtered_specific_pallets.append(pallet)
        except Exception:
            #: skip, we'll see the error in the report from process_pallets
            pass

    #: no pallets to process. we are done here
    if len(filtered_specific_pallets) == 0:
        return ''

    services_affected, data_being_moved, destination_to_pallet = _hydrate_data_structures(filtered_specific_pallets, all_pallets)

    #: compact before shutting down services to minimize downtime
    for source in data_being_moved:
        if arcpy.Describe(source).workspaceFactoryProgID.startswith('esriDataSourcesGDB.FileGDBWorkspaceFactory'):
            log.info('compacting %s', source)
            arcpy.Compact_management(source)

    # results = _stop_services(servers)

    for source in data_being_moved:
        for destination in config_copy_destinations:
            destination_workspace = path.join(destination, path.basename(source))

            log.info('copying {} to {}...'.format(source, destination_workspace))
            start_seconds = clock()
            try:
                if path.exists(destination_workspace):
                    log.debug('%s exists moving', destination_workspace)
                    shutil.move(destination_workspace, destination_workspace + 'x')

                log.debug('copying source to destination')
                shutil.copytree(source, destination_workspace, ignore=shutil.ignore_patterns('*.lock'))

                _remove_hash_from_workspace(destination_workspace)

                if path.exists(destination_workspace + 'x'):
                    log.debug('removing temporary gdb: %s', destination_workspace + 'x')
                    shutil.rmtree(destination_workspace + 'x')

                log.info('copy successful in %s', seat.format_time(clock() - start_seconds))
            except Exception as e:
                try:
                    #: There is still a lock?
                    #: The service probably wasn't shut down
                    #: if there was a problem and the temp gdb exists
                    #: since we couldn't delete it before we probably can't delete it now
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

    # results += _start_services(services_affected)

    # return results


def _remove_hash_from_workspace(workspace):
    '''
    workspace: String

    removes the hash field from all datasets in the workspace'''
    arcpy.env.workspace = workspace

    for table in arcpy.ListFeatureClasses() + arcpy.ListTables():
        log.debug(table)
        arcpy.DeleteField_management(table, hash_field)

    arcpy.env.workspace = None


def _hydrate_data_structures(specific_pallets, all_pallets):
    services_affected = set([])
    data_being_moved = set([])
    destination_to_pallet = {}

    def normalize_workspace(workspace_path):
        return path.normpath(workspace_path.lower())

    #: get the services affected by this pallet
    for pallet in specific_pallets:
        for service in pallet.arcgis_services:
            services_affected.add(service)

        for workspace in pallet.copy_data:
            data_being_moved.add(normalize_workspace(workspace))

    #: append the services that share datasources
    for pallet in all_pallets:
        for workspace in pallet.copy_data:
            workspace = normalize_workspace(workspace)
            if workspace not in data_being_moved:
                continue

            for service in pallet.arcgis_services:
                services_affected.add(service)

            destination_to_pallet.setdefault(workspace, []).append(pallet)
            break

    return services_affected, data_being_moved, destination_to_pallet


def _get_locations_for_dropoff(specific_pallets, all_pallets):
    def normalize_workspace(workspace_path):
        return path.normpath(workspace_path.lower())

    destination_to_pallet = {}

    for pallet in set(specific_pallets + all_pallets):
        if not pallet.success[0]:
            continue

        for crate in pallet.get_crates():
            if crate.result[0] in [Crate.UPDATED, Crate.CREATED, Crate.UPDATED_OR_CREATED_WITH_WARNINGS]:
                normal_paths = [normalize_workspace(p) for p in pallet.copy_data]
                for p in normal_paths:
                    destination_to_pallet.setdefault(p, []).append(pallet)

                break

    return destination_to_pallet
