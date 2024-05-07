#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
forklift

Usage:
    forklift build [<file-path>] [--profile] [--pallet-arg <arg>] [--verbose]
    forklift config init
    forklift config repos --add <repo>
    forklift config repos --list
    forklift config repos --remove <repo>
    forklift config set --key <key> --value <value>
    forklift garage open
    forklift gift-wrap --output <folder-path> [--input <fgdb-path>|--pallet <file-path>] [--verbose]
    forklift git-update
    forklift lift [<file-path>] [--pallet-arg <arg>] [--verbose] [--skip-emails|--send-emails] [--preserve-drop-off-data]
    forklift list-pallets
    forklift scorched-earth
    forklift ship [--verbose] [--pallet-arg <arg>] [--skip-emails|--send-emails] [--by-service]
    forklift special-delivery <file-path> [--pallet-arg <arg>] [--verbose]
    forklift speedtest

Arguments:
    repo            The name of a GitHub repository in <owner>/<name> format.
    file-path       A path to a file that defines one or multiple pallets.
    fgdb-path       A path to a file geodatabase.
    folder-path     A path to a folder.
    pallet-arg      A string to be used as an optional initialization parameter to the pallet.

Examples:
    forklift build                                                          Builds pallets without lifting or shipping. This is used for testing
                                                                            and finding missing packages in your conda environment.
    forklift config init                                                    Creates the config file.
    forklift config repos --add agrc/ugs-chemistry                          Adds a path to the config. Checks for duplicates.
    forklift config repos --list                                            Outputs the list of pallet folder paths in your config file.
    forklift config repos --remove agrc/ugs-chemistry                       Removes a path from the config.
    forklift config set --key <key> --value <value>                         Sets a key in the config with a value.
    forklift garage open                                                    Opens the garage folder with explorer.
    forklift gift-wrap --output path/to/folder                              Gift wraps everything in `config.hashLocation`
    forklift gift-wrap --output path/to/folder --input path/to/fgdb.gdb     Gift wraps `path\to\fgdb.gdb`
    forklift gift-wrap --output path/to/folder --pallet pallet_file.py      Gift wraps all data (as defined by `copy_data`) in pallets defined in pallet_file.py
    forklift git-update                                                     Pulls the latest updates to all git repositories.
    forklift lift                                                           The main entry for running all of pallets found in the warehouse folder.
    forklift lift --preserve-drop-off-data                                  Does not clear out existing data in `dropoffLocation`. [not yet implemented]
    forklift lift --send-emails                                             Force sending emails. Overrides `sendEmails` config as True.
    forklift lift --skip-emails                                             Skip sending emails. Overrides `sendEmails` config as False.
    forklift lift --verbose                                                 Print DEBUG statements to the console.
    forklift lift path/to/pallet_file.py                                    Run a specific pallet.
    forklift lift path/to/pallet_file.py --pallet-arg arg                   Run a specific pallet with "arg" as an initialization parameter.
    forklift list-pallets                                                   Outputs the list of pallets from the config.
    forklift scorched-earth                                                 WARNING!!! Deletes all data in `config.stagingDestination` as well as the
                                                                            `hashes.gdb` & `scratch.gdb` file geodatabases.
    forklift ship                                                           Moves data from the drop off location to the ship to location.
    forklift ship --by-service path/to/pallet_file.py                       Shuts down only those services that are related to the data that was changed related
                                                                            to the pallet(s) in the passed in file rather than shutting down the entire server
                                                                            before pushing data. [not yet implemented]
    forklift special-delivery path/to/pallet_file.py                        Lifts and ships a single file's worth of pallets without messing with any existing
                                                                            data in `dropoffLocation`. During shipping, it also shuts down only the services that
                                                                            use the data that was updated rather than the entire ArcGIS Server instance. Note: this
                                                                            will only work for pallets that are in the warehouse.
    forklift speedtest                                                      Test the speed on a predefined pallet.
"""

#: check for Pro license
try:
    pass
except RuntimeError as exception:
    import socket

    from . import config, messaging

    messaging.send_emails_override = True
    messaging.send_email(config.get_config_prop("notify"), f"Forklift Error on {socket.gethostname()}", str(exception))

    print("ERROR: Cannot import arcpy! This is usually caused by ArcGIS Pro not having a valid license.")
    exit(1)


import faulthandler
import logging.config
import socket
import sys
from logging import shutdown
from os import linesep, makedirs, startfile
from os.path import abspath, dirname, join, realpath

from docopt import docopt

from . import config, engine, messaging

log_location = join(abspath(dirname(__file__)), "..", "forklift-garage", "forklift.log")
detailed_formatter = logging.Formatter(
    fmt="%(levelname)-7s %(asctime)s %(module)10s:%(lineno)5s %(message)s", datefmt="%m-%d %H:%M:%S"
)
speedtest = join(dirname(realpath(__file__)), "..", "..", "speedtest", "SpeedTestPallet.py")


def main():
    """Main entry point for program. Parse arguments and pass to engine module"""

    args = docopt(__doc__, version="9.4.1")
    _setup_logging(args["--verbose"])
    _add_global_error_handler()

    if args["--skip-emails"]:
        messaging.send_emails_override = False
    elif args["--send-emails"]:
        messaging.send_emails_override = True

    def run_build():
        if args["<file-path>"]:
            if args["--pallet-arg"]:
                pallets, import_errors = engine.build_pallets(args["<file-path>"], args["<arg>"])
            else:
                pallets, import_errors = engine.build_pallets(args["<file-path>"])
        else:
            pallets, import_errors = engine.build_pallets(None)

        print(f"pallets: {pallets}")
        print(f"import errors: {import_errors}")

    if args["build"]:
        if args["--profile"]:
            import cProfile

            cProfile.runctx("run_build()", globals(), locals(), sort="cumulative")
        else:
            run_build()
    elif args["config"]:
        if args["init"]:
            message = engine.init()
            print(("config file: {}".format(message)))

        if args["repos"] and args["<repo>"]:
            if args["--add"]:
                message = engine.add_repo(args["<repo>"])

            if args["--remove"]:
                message = engine.remove_repo(args["<repo>"])

            print(message)

        if args["repos"] and args["--list"]:
            for folder in engine.list_repos():
                print(folder)

        if args["set"] and args["<key>"] and args["<value>"]:
            message = config.set_config_prop(args["<key>"], args["<value>"])
            print(message)
    elif args["garage"] and args["open"]:
        startfile(dirname(engine.init()))
    elif args["gift-wrap"]:
        engine.gift_wrap(args["<folder-path>"], args["<fgdb-path>"], args["<file-path>"])
    elif args["git-update"]:
        engine.git_update()
    elif args["lift"]:
        if args["<file-path>"]:
            if args["--pallet-arg"]:
                engine.lift_pallets(args["<file-path>"], args["<arg>"])
            else:
                engine.lift_pallets(args["<file-path>"])
        else:
            engine.lift_pallets()
    elif args["list-pallets"]:
        pallets = engine.list_pallets()

        if len(pallets) == 0:
            print("No pallets found!")
        else:
            for path, pallet_class in pallets:
                print((": ".join([path, str(pallet_class)])))
    elif args["scorched-earth"]:
        engine.scorched_earth()
    elif args["ship"]:
        if args["--pallet-arg"]:
            engine.ship_data(args["<arg>"])
        else:
            engine.ship_data()
    elif args["special-delivery"]:
        warehouse = config.get_config_prop("warehouse").lower()

        if not abspath(args["<file-path>"]).lower().startswith(abspath(warehouse)):
            print("Pallet must be located in the warehouse!")

            return

        engine.move_dropoff_data(True)

        try:
            if args["--pallet-arg"]:
                engine.lift_pallets(args["<file-path>"], args["<arg>"])
            else:
                engine.lift_pallets(args["<file-path>"])

            engine.ship_data(args["<arg>"], True)
        finally:
            engine.move_dropoff_data(False)
    elif args["speedtest"]:
        engine.speedtest(speedtest)

    shutdown()


def global_exception_handler(ex_cls, ex, tb):
    """
    ex_cls: Class - the type of the exception
    ex: object - the exception object
    tb: Traceback

    Used to handle any uncaught exceptions. Formats an error message, logs it, and sends an email.
    """
    import traceback

    log = logging.getLogger("forklift")

    last_traceback = (traceback.extract_tb(tb))[-1]
    line_number = last_traceback[1]
    file_name = last_traceback[0].split(".")[0]
    error = linesep.join(traceback.format_exception(ex_cls, ex, tb))

    log.error(("global error handler line: %s (%s)" % (line_number, file_name)))
    log.error(error)

    log_file = join(dirname(config.config_location), "forklift.log")
    messaging.send_email(
        config.get_config_prop("notify"), f"Forklift Error on {socket.gethostname()}", error, [log_file]
    )


def _add_global_error_handler():
    """Handle all otherwise unhandled exceptions with the function above"""
    sys.excepthook = global_exception_handler


def _setup_logging(verbose):
    """verbose: boolean

    configures the logger
    """
    log = logging.getLogger("forklift")

    log.logThreads = 0
    log.logProcesses = 0

    debug = "DEBUG"
    info = "INFO"

    if verbose:
        info = debug

    try:
        makedirs(dirname(log_location))
    except Exception:
        pass

    file_handler = logging.handlers.RotatingFileHandler(log_location, backupCount=18)
    file_handler.doRollover()
    file_handler.setFormatter(detailed_formatter)
    file_handler.setLevel(debug)

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(detailed_formatter)
    console_handler.setLevel(info)

    log.addHandler(file_handler)
    log.addHandler(console_handler)
    log.setLevel(debug)

    faulthandler.enable(file_handler.stream)

    return log


if __name__ == "__main__":
    sys.exit(main())
