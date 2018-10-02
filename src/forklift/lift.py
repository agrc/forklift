#!/usr/bin/env python
# * coding: utf8 *
'''
lift.py

A module that contains methods to handle pallets
'''

import logging
import shutil
import socket
from os import listdir, makedirs, path, remove, walk
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


def process_pallets(pallets):
    '''
    pallets: Pallet[]

    Loop over all pallets, check if data has changed and determine whether to process.
    Call `process` if this is not the post copy. Otherwise call `post_copy_process`.
    Finally, call ship.
    '''

    verb = 'processing'

    log.info('%s pallets...', verb)

    for pallet in pallets:
        try:
            if pallet.is_ready_to_ship():  #: checks for schema changes or errors
                if pallet.requires_processing() and pallet.success[0]:  #: checks for data that was updated
                    log.info('%s pallet: %r', verb, pallet)
                    start_seconds = clock()

                    arcpy.ResetEnvironments()
                    arcpy.ClearWorkspaceCache_management()

                    with seat.timed_pallet_process(pallet, 'process'):
                        pallet.process()

                    log.debug('%s pallet %s', verb.replace('ing', 'ed'), seat.format_time(clock() - start_seconds))
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


def copy_data(from_location, to_template, packing_slip_file, machine_name=None):
    '''
    specific_pallets: Pallet[]
    all_pallets: Pallet[]
    config_copy_destinations: string[]

    Copies databases from either `copy_data` or `static_data` to `config_copy_destinations`.
    '''
    failed = {}
    successful = []
    data_being_moved = set(listdir(from_location)) - set([packing_slip_file])

    for source in data_being_moved:
        source_path = path.join(from_location, source)
        destination_path = path.join(to_template.format(machine_name), source)

        log.info('copying {} to {}...'.format(source, destination_path))
        start_seconds = clock()
        try:
            if path.exists(destination_path):
                log.debug('%s exists moving', destination_path)
                shutil.move(destination_path, destination_path + 'x')

            log.debug('copying source to destination')
            if path.isfile(source_path):
                shutil.copy(source_path, destination_path)
            else:
                shutil.copytree(source_path, destination_path, ignore=shutil.ignore_patterns('*.lock'))

            temp_path = destination_path + 'x'
            if path.exists(temp_path):
                log.debug('removing temporary item: %s', temp_path)
                if path.isfile(temp_path):
                    remove(temp_path)
                else:
                    shutil.rmtree(temp_path)

            successful.append(source)
            log.info('copy successful in %s', seat.format_time(clock() - start_seconds))
        except Exception:
            try:
                #: There is still a lock?
                #: The service probably wasn't shut down
                #: if there was a problem and the temp gdb exists
                #: since we couldn't delete it before we probably can't delete it now
                #: so take what is in x and copy it over what it can in the original
                #: that _should_ leave the gdb in a functioning state
                temp_path = destination_path + 'x'
                if path.exists(destination_path) and path.exists(temp_path):
                    log.debug('cleaning up %s', destination_path)
                    _copy_with_overwrite(temp_path, destination_path)
                    if path.isfile(temp_path):
                        remove(temp_path)
                    else:
                        shutil.rmtree(temp_path)
            except Exception:
                log.error('%s might be in a corrupted state', destination_path, exc_info=True)
                failed[source] = 'might be in a corrupted state'

            log.error('there was an error copying %s to %s', source, destination_path, exc_info=True)
            failed.setdefault(source, '')
            failed[source] += 'there was an error copying {} to {}'.format(source, destination_path)

    return successful, failed


def _remove_hash_from_workspace(workspace):
    '''
    workspace: String

    removes the hash field from all datasets in the workspace'''
    arcpy.env.workspace = workspace

    for table in arcpy.ListFeatureClasses() + arcpy.ListTables():
        log.debug(table)
        arcpy.DeleteField_management(table, hash_field)

    arcpy.env.workspace = None


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
