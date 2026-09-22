"""
seat.py

A module that contains helpful methods for other modules
"""

import json
import logging
import subprocess
from pathlib import Path

from forklift import config


def format_time(seconds):
    """seconds: number

    returns a human-friendly string describing the amount of time
    """
    minute = 60.00
    hour = 60.00 * minute

    if seconds < 30:
        return f"{int(seconds * 1000)} ms"

    if seconds < 90:
        return f"{round(seconds, 2)} seconds"

    if seconds < 90 * minute:
        return f"{round(seconds / minute, 2)} minutes"

    return f"{round(seconds / hour, 2)} hours"


class timed_pallet_process:
    """A class used to time pallet processes. For use in with statements."""

    def __init__(self, pallet, name):
        self.pallet = pallet
        self.name = name

    def __enter__(self):
        self.pallet.start_timer(self.name)

    def __exit__(self, type, value, traceback):
        self.pallet.stop_timer(self.name)


def map_network_drive(name, drive_letter):
    with Path(Path(config.config_location).parent, "share", f"{name}.json").open("r") as parameters_file:
        parameters = json.load(parameters_file)
    path = parameters["path"]
    username = parameters["username"]
    password = parameters["password"]
    logger = logging.getLogger("forklift")
    if not drive_letter.endswith(":"):
        drive_letter += ":"
    logger.debug(f"Mapping network drive: {path} to {drive_letter}")
    try:
        result = subprocess.run(
            ["net", "use", drive_letter, path, password, f"/user:{username}", "/persistent:yes"],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info(f"Network share mounted successfully: {result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        if "85" in e.stderr or "1219" in e.stderr:
            logger.debug("ignoring error 85, drive already mapped")
        else:
            raise Exception(f"Error mounting network share: {e.stderr.strip()}") from e
