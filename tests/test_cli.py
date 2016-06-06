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
            self.assertEqual(config_dict, {u"warehouse": u"c:\\scheduled",
                                           u"repositories": [],
                                           u"notify": [u"stdavis@utah.gov", u"sgourley@utah.gov"],
                                           u"sendEmails": False})

    def test_init_returns_path_for_existing_config_file(self):
        self.assertEqual(cli.init(), cli.init())


class TestConfigSet(unittest.TestCase):

    def setUp(self):
        if exists('config.json'):
            remove('config.json')

        cli.init()

    def tearDown(self):
        if exists('config.json'):
            remove('config.json')

    def test_set_config_prop_overrides_all_values(self):
        folder = 'blah'
        cli.set_config_prop('warehouse', folder, override=True)

        self.assertEqual(cli.get_config_prop('warehouse'), folder)

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

        self.assertEqual(message, 'this was not found in config.')

    @patch('forklift.cli.get_config')
    def test_set_config_prop_appends_items_from_list_if_not_overriding(self, mock_obj):
        mock_obj.return_value = {'test': []}

        message = cli.set_config_prop('test', [1, 2, 3])

        self.assertEqual(message, 'Added [1, 2, 3] to test')

    @patch('forklift.cli.get_config')
    def test_set_config_prop_sets_value(self, mock_obj):
        mock_obj.return_value = {'test': ''}

        message = cli.set_config_prop('test', 'value')

        self.assertEqual(message, 'Added value to test')


class TestRepos(unittest.TestCase):

    def setUp(self):
        if exists('config.json'):
            remove('config.json')

        self.path = cli.init()

    def tearDown(self):
        if exists('config.json'):
            remove('config.json')

    def test_add_repo(self):
        path = cli.init()

        cli.add_repo('agrc/forklift')

        with open(path) as config:
            self.assertEqual(['agrc/forklift'], loads(config.read())['repositories'])

    def test_add_repo_invalid(self):
        result = cli.add_repo('bad/repo')

        self.assertIn('[Invalid URL]', result)

    @patch('forklift.cli._validate_repo')
    def test_add_repo_checks_for_duplicates(self, _validate_repo_mock):
        _validate_repo_mock.return_value = ''
        cli.add_repo('tests/data')
        cli.add_repo('tests/data')

        with open(self.path) as config:
            self.assertEqual(loads(config.read())['repositories'], ['tests/data'])

    def test_remove_repo(self):
        test_config_path = join(test_data_folder, 'remove_test_config.json')

        with open(self.path, 'w') as json_data_file, open(test_config_path) as test_config_file:
            json_data_file.write(test_config_file.read())

        cli.remove_repo('path/one')

        with open(self.path) as test_config_file:
            self.assertEqual(['path/two'], loads(test_config_file.read())['repositories'])

    def test_remove_repo_checks_for_existing(self):
        self.assertEqual('{} is not in the repositories list!'.format('blah'), cli.remove_repo('blah'))

    def test_list_repos(self):
        cli.set_config_prop('repositories', ['blah', 'blah2'], override=True)

        result = cli.list_repos()

        self.assertEqual(result, ['blah: [Invalid URL]', 'blah2: [Invalid URL]'])


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
        pallets = cli._get_pallets_in_folder(test_pallets_folder)

        self.assertEqual(len(pallets), 4)
        self.assertEqual(pallets[0][0], join(test_pallets_folder, 'multiple_pallets.py'))
        self.assertEqual(pallets[0][1], 'PalletOne')
        self.assertEqual(pallets[3][1], 'NestedPallet')

    def test_list_pallets_from_config(self):
        cli.set_config_prop('warehouse', test_pallets_folder, override=True)
        pallets = cli.list_pallets()

        self.assertEqual(len(pallets), 4)
        self.assertEqual(pallets[0][0], join(test_pallets_folder, 'multiple_pallets.py'))
        self.assertEqual(pallets[0][1], 'PalletOne')


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
        cli.set_config_prop('warehouse', test_pallets_folder, override=True)
        cli.start_lift()

        self.assertEqual(len(process_crates_for.call_args[0][0]), 4)
        self.assertEqual(len(process_pallets.call_args[0][0]), 4)


class TestCliGeneral(unittest.TestCase):
    def testrepo_to_url(self):
        self.assertEqual(cli._repo_to_url('repo'), 'https://github.com/repo.git')
