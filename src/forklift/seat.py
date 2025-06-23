#!/usr/bin/env python
# * coding: utf8 *
"""
seat.py

A module that contains helpful methods for other modules
"""
import subprocess
import logging
import json
from pathlib import Path
from forklift import config


def format_time(seconds):
    """seconds: number

    returns a human-friendly string describing the amount of time
    """
    minute = 60.00
    hour = 60.00 * minute

    if seconds < 30:
        return "{} ms".format(int(seconds * 1000))

    if seconds < 90:
        return "{} seconds".format(round(seconds, 2))

    if seconds < 90 * minute:
        return "{} minutes".format(round(seconds / minute, 2))

    return "{} hours".format(round(seconds / hour, 2))


class timed_pallet_process(object):
    """A class used to time pallet processes. For use in with statements."""

    def __init__(self, pallet, name):
        self.pallet = pallet
        self.name = name

    def __enter__(self):
        self.pallet.start_timer(self.name)

    def __exit__(self, type, value, traceback):
        self.pallet.stop_timer(self.name)


def map_network_drive(name, drive_letter):
    parameters = json.load(Path(Path(config.config_location).parent, 'share', f'{name}.json').open('r'))
    path = parameters['path']
    username = parameters['username']
    password = parameters['password']
    logger = logging.getLogger('forklift')
    if not drive_letter.endswith(':'):
        drive_letter += ':'
    logger.debug(f"Mapping network drive: {path} to {drive_letter}")
    try:
        result = subprocess.run(
            ["net", "use", drive_letter, path, password, f"/user:{username}", '/persistent:yes'],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        logger.info(f"Network share mounted successfully: {result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        if '85' in e.stderr or '1219' in e.stderr:
            logger.debug('ignoring error 85, drive already mapped')
        else:
            raise Exception(f"Error mounting network share: {e.stderr.strip()}") from e
