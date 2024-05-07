#!/usr/bin/env python
# * coding: utf8 *
"""
test_slack.py

A module that tests slack blocks
"""

import unittest

from forklift import slack


class TestSlack(unittest.TestCase):
    def test_ship_with_error(self):
        messages = slack.ship_report_to_blocks(
            {
                "num_success_pallets": 10,
                "total_pallets": 10,
                "hostname": "testing",
                "total_time": "1 second",
                "server_reports": [
                    {
                        "name": "machineone",
                        "problem_services": [],
                        "successful_copies": ["test.gdb", "test2.gdb"],
                        "success": True,
                        "message": Exception("ship message is an error"),
                        "has_service_issues": False,
                    }
                ],
                "pallets": [
                    {
                        "name": "Z:\\forklift\\samples\\PalletSamples.py:StringCratePallet",
                        "success": True,
                        "message": Exception("pallet message is an error"),
                        "total_processing_time": "1 hour",
                        "post_copy_processed": True,
                        "shipped": True,
                        "crates": [
                            {"name": "FeatureClassOne", "result": Exception("crate result is an error")},
                            {"name": "FeatureClassTwo", "result": "Created table successfully."},
                        ],
                    }
                ],
            }
        )

        self.assertTrue(len(messages) == 1)

    def test_lift_with_error(self):
        messages = slack.lift_report_to_blocks(
            {
                "hostname": "SomeMachineName",
                "num_success_pallets": 3,
                "total_pallets": 3,
                "total_time": "4.5 hours",
                "git_errors": [],
                "import_errors": [],
                "pallets": [
                    {
                        "name": "c:\\forklift\\warehouse\\warehouse\\sgid\\AGOLPallet.py:AGOLPallet",
                        "success": True,
                        "is_ready_to_ship": True,
                        "requires_processing": True,
                        "ship_on_fail": True,
                        "message": Exception("pallet message is an error"),
                        "crates": [
                            {
                                "name": "OilGasWells",
                                "result": Exception("crate result is an error"),
                                "crate_message": Exception("crate message is an error"),
                                "message_level": "warning",
                                "source": "c:\\program files\\arcgis\\pro\\bin\\python\\envs\\forklift\\lib\\site-packages\\forklift\\..\\forklift-garage\\sgid.sde\\SGID.ENERGY.OilGasWells",
                                "destination": "c:\\forklift\\data\\hashed\\energy.gdb\\OilGasWells",
                                "was_updated": True,
                            }
                        ],
                    }
                ],
            }
        )

        self.assertTrue(len(messages) == 1)
