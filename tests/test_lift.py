#!/usr/bin/env python
# * coding: utf8 *
'''
test_lift.py

A module that contains tests for the lift.py module
'''

import unittest
from forklift import lift
from json import loads
from os import remove
from os.path import abspath, dirname, join, exists


class TestLift(unittest.TestCase):

    test_data_folder = join(dirname(abspath(__file__)), 'data')

    def setUp(self):
        if exists('config.json'):
            remove('config.json')

    def tearDown(self):
        if exists('config.json'):
            remove('config.json')

    def test_init_creates_config_file(self):
        path = lift.init()

        self.assertTrue(exists(path))

        with open(path) as config:
            self.assertEquals(['c:\\scheduled'], loads(config.read()))

    def test_list_pallets(self):
        test_pallets_folder = join(self.test_data_folder, 'list_pallets')
        pallets = lift.list_pallets(paths=[test_pallets_folder])

        self.assertEquals(len(pallets), 3)
        self.assertEquals(pallets[0][0], join(test_pallets_folder, 'multiple_pallets.py'))
        self.assertEquals(pallets[0][1], 'PalletOne')

    def test_set_config_paths_requires_list(self):
        self.assertRaises(Exception, lift._set_config_paths, 'hello')

    def test_add_pallet_folder(self):
        path = lift.init()

        lift.add_pallet_folder('another/folder')

        with open(path) as config:
            self.assertEquals(['c:\\scheduled', 'another/folder'], loads(config.read()))

    def test_add_pallet_folder_checks_for_duplicates(self):
        lift.init()

        lift.add_pallet_folder('another/folder')
        self.assertRaises(Exception, lift.add_pallet_folder, 'another/folder')

    def test_remove_pallet_folder(self):
        path = lift.init()
        test_config_path = join(self.test_data_folder, 'remove_test_config.json')

        with open(path, 'w') as json_data_file, open(test_config_path) as test_config_file:
            json_data_file.write(test_config_file.read())

        lift.remove_pallet_folder('path/one')

        with open(path) as test_config_file:
            self.assertEquals(['path/two'], loads(test_config_file.read()))

    def test_remove_pallet_folder_checks_for_existing(self):
        lift.init()

        self.assertRaises(Exception, lift.remove_pallet_folder, 'blah')
