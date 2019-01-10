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

from . import seat
from .core import hash_field
from .models import Crate

log = logging.getLogger('forklift')


def process_checklist(config):
    '''config: config module

    removes the dropoffLocation and creates the hasLocation if needed
    '''
    _remove_if_exists(config.get_config_prop('dropoffLocation'))
    _create_if_not_exists([config.get_config_prop('hashLocation'), config.get_config_prop('dropoffLocation')])


def _remove_if_exists(location):
    '''location: string - path to folder

    removes the path if it exists
    '''
    if not path.exists(location):
        return

    shutil.rmtree(location)


def _create_if_not_exists(locations):
    '''locations: string[] - array of paths

    creates all of the paths contained in locations
    '''
    for location in locations:
        if path.exists(location):
            continue

        makedirs(location)


def prepare_packaging_for_pallets(pallets):
    '''pallets: Pallet[]

    Calls prepare_packaging for pallets
    '''
    log.info('preparing packing for %d pallets', len(pallets))

    for pallet in pallets:
        try:
            log.debug('prepare packaging for: %r', pallet)
            with seat.timed_pallet_process(pallet, 'prepare_packaging'):
                pallet.prepare_packaging()
        except Exception as e:
            pallet.success = (False, str(e))
            log.error('error preparing packaging: %s for pallet: %r', e, pallet, exc_info=True)


def process_crates_for(pallets, update_def):
    '''
    pallets: Pallet[]
    update_def: Function - core.update by default

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
                    log.warning('result: %s', crate.result)
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
    '''pallets: Pallet[]

    Loop over all pallets, check if data has changed, and determine whether to process.
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
            pallet.success = (False, str(e))
            log.error('error %s pallet: %s for pallet: %r', verb, e, pallet, exc_info=True)


def dropoff_data(pallets, dropoff_location):
    '''
    pallets: Pallet[]
    config_copy_destinations: string[]

    Copies scrubbed hashed data to `dropoff_location` that is ready to go to production.
    '''
    #: filter out pallets whose data did not change
    filtered_pallets = []
    for pallet in pallets:
        try:
            if pallet.requires_processing() is True:
                filtered_pallets.append(pallet)
        except Exception:
            #: skip, we'll see the error in the report from process_pallets
            pass

    #: no pallets with data updates. we are done here
    if len(filtered_pallets) == 0:
        return

    #: data_source eg: C:\forklift\data\hashed\boundaries_utm.gdb
    destination_and_pallet = _get_locations_for_dropoff(filtered_pallets)
    _move_to_dropoff(destination_and_pallet, dropoff_location)


def gift_wrap(location):
    '''location: string

    Scrubs the hash field from all data and compacts the geodatabases
    '''
    arcpy.env.workspace = location

    workspaces = arcpy.ListWorkspaces('*', 'FileGDB')

    [_remove_hash_from_workspace(workspace) for workspace in workspaces]
    [arcpy.management.Compact(workspace) for workspace in workspaces]


def _move_to_dropoff(destination_and_pallet, dropoff_location):
    '''
    destination_and_pallet: string, pallet[]
    dropoff_location: string

    Copies data from pallet destinations to dropoff location.
    '''
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
    '''
    pallets: Pallet[]
    elapsed_time: string
    git_errors: string[]

    returns a dictionary with data formatted for use in the report
    '''
    reports = [pallet.get_report() for pallet in pallets]

    return {
        'hostname': socket.gethostname(),
        'total_pallets': len(reports),
        'pallets': reports,
        'num_success_pallets': len([p for p in reports if p['success']]),
        'git_errors': git_errors,
        'total_time': elapsed_time
    }


def _copy_with_overwrite(source, destination):
    '''
    source: string - path to folder
    destination: string - path to folder

    Recursively copies the data from source to destination.
    '''
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
    from_location: string - path to folder
    to_template: string - path with machineName template string
    packing_slip_file: string - filename
    machine_name: string

    Copies data from from_location to to_template (after machineName has been subsituted).
    If there is a problem with the copy (e.g. there are locks on existing destination data), then
    the copy is rolled back.
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
    '''workspace: String

    Removes the hash field from all datasets in the workspace
    '''
    arcpy.env.workspace = workspace

    for table in arcpy.ListFeatureClasses() + arcpy.ListTables():
        log.debug('scrubbing hash field from: %s', table)
        arcpy.DeleteField_management(table, hash_field)

    arcpy.env.workspace = None


def _get_locations_for_dropoff(pallets):
    '''pallets: Pallet[]

    returns a dictionary of destination paths and the pallets that they are associated with
    '''

    def normalize_workspace(workspace_path):
        return path.normpath(workspace_path.lower())

    destination_to_pallet = {}

    for pallet in pallets:
        if pallet.success[0] and pallet.requires_processing():
            normal_paths = [normalize_workspace(p) for p in pallet.copy_data]
            for p in normal_paths:
                destination_to_pallet.setdefault(p, []).append(pallet)

    return destination_to_pallet
