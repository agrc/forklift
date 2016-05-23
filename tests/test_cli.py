#!/usr/bin/env python
# * coding: utf8 *
'''
test_lift.py

A module that contains tests for the cli.py module
'''

import unittest
from forklift import cli
from json import loads
from os import remove
from os.path import abspath, dirname, join, exists
from mock import patch


test_data_folder = join(dirname(abspath(__file__)), 'data')
test_pallets_folder = join(test_data_folder, 'list_pallets')


class TestCli(unittest.TestCase):

    def setUp(self):
        if exists('config.json'):
            remove('config.json')

    def tearDown(self):
        if exists('config.json'):
            remove('config.json')

    def test_init_creates_config_file(self):
        path = cli.init()

        self.assertTrue(exists(path))

        with open(path) as config:
            self.assertEquals(['c:\\scheduled'], loads(config.read()))

    def test_init_returns_if_existing_config_file(self):
        cli._set_config_folders(['blah'])

        self.assertEquals(cli.init(), 'config file already created.')

    def test_list_pallets(self):
        test_pallets_folder = join(test_data_folder, 'list_pallets')
        pallets = cli.list_pallets(folders=[test_pallets_folder])

        self.assertEquals(len(pallets), 3)
        self.assertEquals(pallets[0][0], join(test_pallets_folder, 'multiple_pallets.py'))
        self.assertEquals(pallets[0][1], 'PalletOne')

    def test_list_config_folders(self):
        cli._set_config_folders(['blah', 'blah2'])

        result = cli.list_config_folders()

        self.assertEquals(result, ['blah: invalid!', 'blah2: invalid!'])

    def get_config_folders(self):
        folders = ['blah', 'blah2']
        cli.init()
        cli._set_config_folders(folders)

        self.assertEquals(cli.get_config_folders, folders)

    def get_config_folders_checks_for_existing_config_file(self):
        self.assertRaises(Exception('config file not found.'), cli.get_config_folders)

    def test_list_pallets_from_config(self):
        cli.init()
        cli.add_config_folder(test_pallets_folder)
        pallets = cli.list_pallets()

        self.assertEquals(len(pallets), 3)
        self.assertEquals(pallets[0][0], join(test_pallets_folder, 'multiple_pallets.py'))
        self.assertEquals(pallets[0][1], 'PalletOne')

    def test_set_config_paths_requires_list(self):
        self.assertRaises(Exception, cli._set_config_folders, 'hello')

    def test_add_config_folder(self):
        path = cli.init()

        cli.add_config_folder(abspath('tests\data'))

        with open(path) as config:
            self.assertEquals(['c:\\scheduled', abspath('tests\data')], loads(config.read()))

    def test_add_config_folder_invalid(self):
        cli.init()

        result = cli.add_config_folder('bad folder')

        self.assertIn('invalid!', result)

    def test_add_config_folder_checks_for_duplicates(self):
        path = cli.init()

        cli.add_config_folder(abspath('tests\data'))
        cli.add_config_folder(abspath('tests\data'))

        with open(path) as config:
            self.assertEquals(['c:\\scheduled', abspath('tests\data')], loads(config.read()))

    def test_remove_config_folder(self):
        path = cli.init()
        test_config_path = join(test_data_folder, 'remove_test_config.json')

        with open(path, 'w') as json_data_file, open(test_config_path) as test_config_file:
            json_data_file.write(test_config_file.read())

        cli.remove_config_folder('path/one')

        with open(path) as test_config_file:
            self.assertEquals(['path/two'], loads(test_config_file.read()))

    def test_remove_config_folder_checks_for_existing(self):
        cli.init()

        self.assertEquals('{} is not in the config folders list!'.format('blah'), cli.remove_config_folder('blah'))


@patch('forklift.lift.process_crates_for')
@patch('forklift.lift.process_pallets')
class TestCliStartLift(unittest.TestCase):

    def test_lift_with_path(self, process_pallets, process_crates_for):
        cli.start_lift(join(test_pallets_folder, 'multiple_pallets.py'))

        self.assertEqual(len(process_crates_for.call_args[0][0]), 2)
        self.assertEqual(len(process_pallets.call_args[0][0]), 2)

    def test_lift_with_out_path(self, process_pallets, process_crates_for):
        cli._set_config_folders([test_pallets_folder])
        cli.start_lift()

        self.assertEqual(len(process_crates_for.call_args[0][0]), 3)
        self.assertEqual(len(process_pallets.call_args[0][0]), 3)
