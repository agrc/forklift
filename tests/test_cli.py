#!/usr/bin/env python
# * coding: utf8 *
'''
test_lift.py

A module that contains tests for the cli.py module
'''

import unittest
from forklift import cli
from json import loads
from mock import patch
from os import remove
from os.path import abspath, dirname, join, exists

test_data_folder = join(dirname(abspath(__file__)), 'data')
test_pallets_folder = join(test_data_folder, 'list_pallets')


class TestConfigInit(unittest.TestCase):

    def setUp(self):
        if exists('config.json'):
            remove('config.json')

    def tearDown(self):
        if exists('config.json'):
            remove('config.json')

    def test_init_creates_default_config_file(self):
        path = cli.init()

        self.assertTrue(exists(path))

        with open(path) as config:
            config_dict = loads(config.read())
            self.assertEquals(config_dict, {u"logLevel": u"INFO",
                                            u"paths": [u"c:\\scheduled"],
                                            u"logger": u"",
                                            u"notify": [u"stdavis@utah.gov", u"sgourley@utah.gov"],
                                            u"sendEmails": False})

    def test_init_returns_path_for_existing_config_file(self):
        self.assertEquals(cli.init(), cli.init())


class TestConfigSet(unittest.TestCase):

    def setUp(self):
        if exists('config.json'):
            remove('config.json')

        cli.init()

    def tearDown(self):
        if exists('config.json'):
            remove('config.json')

    def test_set_config_prop_overrides_all_values(self):
        folders = ['blah', 'blah2']
        cli.set_config_prop('paths', folders, override=True)

        self.assertEquals(cli.get_config_prop('paths'), folders)

    @patch('forklift.cli._create_default_config')
    def test_get_config_creates_default_config(self, mock_obj):
        if exists('config.json'):
            remove('config.json')

        cli.get_config()

        mock_obj.assert_called_once()

    @patch('forklift.cli.get_config')
    def test_set_config_prop_returns_message_if_not_found(self, mock_obj):
        mock_obj.return_value = {}

        message = cli.set_config_prop('this was', 'not found')

        self.assertEquals(message, 'this was not found in config.')

    @patch('forklift.cli.get_config')
    def test_set_config_prop_appends_items_from_list_if_not_overriding(self, mock_obj):
        mock_obj.return_value = {'test': []}

        message = cli.set_config_prop('test', [1, 2, 3])

        self.assertEquals(message, 'Added [1, 2, 3] to test')

    @patch('forklift.cli.get_config')
    def test_set_config_prop_sets_value(self, mock_obj):
        mock_obj.return_value = {'test': ''}

        message = cli.set_config_prop('test', 'value')

        self.assertEquals(message, 'Added value to test')


class TestConfigFolder(unittest.TestCase):

    def setUp(self):
        if exists('config.json'):
            remove('config.json')

        self.path = cli.init()

    def tearDown(self):
        if exists('config.json'):
            remove('config.json')

    def test_add_config_folder_invalid(self):
        result = cli.add_config_folder('bad folder')

        self.assertIn('[Folder not found]', result)

    def test_add_config_folder_checks_for_duplicates(self):
        cli.add_config_folder(abspath('tests\data'))
        cli.add_config_folder(abspath('tests\data'))

        with open(self.path) as config:
            self.assertEquals(['c:\\scheduled', abspath('tests\data')], loads(config.read())['paths'])

    def test_remove_config_folder(self):
        test_config_path = join(test_data_folder, 'remove_test_config.json')

        with open(self.path, 'w') as json_data_file, open(test_config_path) as test_config_file:
            json_data_file.write(test_config_file.read())

        cli.remove_config_folder('path/one')

        with open(self.path) as test_config_file:
            self.assertEquals(['path/two'], loads(test_config_file.read())['paths'])

    def test_remove_config_folder_checks_for_existing(self):
        self.assertEquals('{} is not in the config folders list!'.format('blah'), cli.remove_config_folder('blah'))

    def test_list_config_folders(self):
        cli.set_config_prop('paths', ['blah', 'blah2'], override=True)

        result = cli.list_config_folders()

        self.assertEquals(result, ['blah: [Folder not found]', 'blah2: [Folder not found]'])


class TestListPallets(unittest.TestCase):

    def setUp(self):
        if exists('config.json'):
            remove('config.json')

        cli.init()

    def tearDown(self):
        if exists('config.json'):
            remove('config.json')

    def test_list_pallets(self):
        test_pallets_folder = join(test_data_folder, 'list_pallets')
        pallets = cli.list_pallets(folders=[test_pallets_folder])

        self.assertEquals(len(pallets), 4)
        self.assertEquals(pallets[0][0], join(test_pallets_folder, 'multiple_pallets.py'))
        self.assertEquals(pallets[0][1], 'PalletOne')
        self.assertEquals(pallets[3][1], 'NestedPallet')

    def test_list_pallets_from_config(self):
        cli.set_config_prop('paths', [test_pallets_folder], override=True)
        pallets = cli.list_pallets()

        self.assertEquals(len(pallets), 4)
        self.assertEquals(pallets[0][0], join(test_pallets_folder, 'multiple_pallets.py'))
        self.assertEquals(pallets[0][1], 'PalletOne')

    def test_add_config_folder(self):
        path = cli.init()

        cli.add_config_folder(abspath('tests\data'))

        with open(path) as config:
            self.assertEquals(['c:\\scheduled', abspath('tests\data')], loads(config.read())['paths'])


@patch('forklift.lift.process_crates_for')
@patch('forklift.lift.process_pallets')
class TestCliStartLift(unittest.TestCase):
    def setUp(self):
        if exists('config.json'):
            remove('config.json')

        cli.init()

    def tearDown(self):
        if exists('config.json'):
            remove('config.json')

    def test_lift_with_path(self, process_pallets, process_crates_for):
        cli.start_lift(join(test_pallets_folder, 'multiple_pallets.py'))

        self.assertEqual(len(process_crates_for.call_args[0][0]), 2)
        self.assertEqual(len(process_pallets.call_args[0][0]), 2)

    def test_lift_with_out_path(self, process_pallets, process_crates_for):
        cli.set_config_prop('paths', [test_pallets_folder], override=True)
        cli.start_lift()

        self.assertEqual(len(process_crates_for.call_args[0][0]), 4)
        self.assertEqual(len(process_pallets.call_args[0][0]), 4)
