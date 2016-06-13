#!/usr/bin/env python
# * coding: utf8 *
'''
test_lift.py

A module that contains tests for the cli.py module
'''

import unittest
from forklift import cli, config
from forklift.models import Crate
from json import loads
from mock import patch, Mock
from os import remove
from os.path import abspath, dirname, join, exists

test_data_folder = join(dirname(abspath(__file__)), 'data')
test_pallets_folder = join(test_data_folder, 'list_pallets')
config.config_location = config_location = join(abspath(dirname(__file__)), 'config.json')


class TestConfigInit(unittest.TestCase):

    def setUp(self):
        if exists(config_location):
            remove(config_location)

    def tearDown(self):
        if exists(config_location):
            remove(config_location)

    def test_init_creates_default_config_file(self):
        path = cli.init()

        self.assertTrue(exists(path))

        with open(path) as config:
            config_dict = loads(config.read())
            self.assertEqual(config_dict, {u"warehouse": u"c:\\scheduled",
                                           u"repositories": [],
                                           u"notify": [u"stdavis@utah.gov", u"sgourley@utah.gov"],
                                           u"sendEmails": False,
                                           u"copyDestinations": []})

    def test_init_returns_path_for_existing_config_file(self):
        self.assertEqual(cli.init(), cli.init())


class TestRepos(unittest.TestCase):

    def setUp(self):
        if exists(config_location):
            remove(config_location)

        self.path = cli.init()

    def tearDown(self):
        if exists(config_location):
            remove(config_location)

    def test_add_repo(self):
        path = cli.init()

        cli.add_repo('agrc/forklift')

        with open(path) as config:
            self.assertEqual(['agrc/forklift'], loads(config.read())['repositories'])

    def test_add_repo_invalid(self):
        result = cli.add_repo('bad/repo')

        self.assertIn('[Invalid repo name or owner]', result)

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
        config.set_config_prop('repositories', ['blah', 'blah2'], override=True)

        result = cli.list_repos()

        self.assertEqual(result, ['blah: [Invalid repo name or owner]', 'blah2: [Invalid repo name or owner]'])


class TestListPallets(unittest.TestCase):

    def setUp(self):
        if exists(config_location):
            remove(config_location)

        cli.init()

    def tearDown(self):
        if exists(config_location):
            remove(config_location)

    def test_list_pallets(self):
        test_pallets_folder = join(test_data_folder, 'list_pallets')
        pallets = cli._get_pallets_in_folder(test_pallets_folder)

        self.assertEqual(len(pallets), 4)
        self.assertEqual(pallets[0][0], join(test_pallets_folder, 'multiple_pallets.py'))
        self.assertEqual(pallets[0][1], 'PalletOne')
        self.assertEqual(pallets[3][1], 'NestedPallet')

    def test_list_pallets_from_config(self):
        config.set_config_prop('warehouse', test_pallets_folder, override=True)
        pallets = cli.list_pallets()

        self.assertEqual(len(pallets), 4)
        self.assertEqual(pallets[0][0], join(test_pallets_folder, 'multiple_pallets.py'))
        self.assertEqual(pallets[0][1], 'PalletOne')

    def test_list_pallets_order(self):
        pallets = cli._get_pallets_in_file(join(test_data_folder, 'pallet_order.py'))

        self.assertEqual(pallets[0][1], 'PalletA')
        self.assertEqual(pallets[1][1], 'PalletB')
        self.assertEqual(pallets[2][1], 'PalletC')


@patch('forklift.lift.process_crates_for')
@patch('forklift.lift.process_pallets')
class TestCliStartLift(unittest.TestCase):

    def setUp(self):
        if exists(config_location):
            remove(config_location)

        cli.init()

    def tearDown(self):
        if exists(config_location):
            remove(config_location)

    def test_lift_with_path(self, process_pallets, process_crates_for):
        cli.start_lift(join(test_pallets_folder, 'multiple_pallets.py'))

        self.assertEqual(len(process_crates_for.call_args[0][0]), 2)
        self.assertEqual(len(process_pallets.call_args[0][0]), 2)

    def test_lift_with_out_path(self, process_pallets, process_crates_for):
        config.set_config_prop('warehouse', test_pallets_folder, override=True)
        cli.start_lift()

        self.assertEqual(len(process_crates_for.call_args[0][0]), 4)
        self.assertEqual(len(process_pallets.call_args[0][0]), 4)

    def test_lift_pallet_arg(self, process_pallets, process_crates_for):
        cli.start_lift(join(test_data_folder, 'pallet_argument.py'), 'test')

        pallet = process_crates_for.call_args[0][0][0]
        self.assertEqual(pallet.arg, 'test')

        cli.start_lift(join(test_data_folder, 'pallet_argument.py'))

        pallet = process_crates_for.call_args[0][0][0]
        self.assertEqual(pallet.arg, None)


class TestCliGeneral(unittest.TestCase):

    def test_repo_to_url(self):
        self.assertEqual(cli._repo_to_url('repo'), 'https://github.com/repo.git')


class TestGitUpdate(unittest.TestCase):

    def setUp(self):
        if exists(config_location):
            remove(config_location)

    def tearDown(self):
        if exists(config_location):
            remove(config_location)

    @patch('git.Repo.clone_from')
    @patch('forklift.cli._get_repo')
    @patch('forklift.cli._validate_repo')
    def test_git_update(self, _validate_repo_mock, _get_repo_mock, clone_from_mock):
        remote_mock = Mock()
        remote_mock.pull = Mock()
        repo_mock = Mock()
        repo_mock.remotes = [remote_mock]
        _get_repo_mock.return_value = repo_mock
        _validate_repo_mock.return_value = ''
        cli.init()
        config.set_config_prop('warehouse', test_pallets_folder, override=True)
        config.set_config_prop('repositories', ['agrc/nested', 'agrc/forklift'])

        cli.git_update()

        clone_from_mock.assert_called_once()
        remote_mock.pull.assert_called_once()


class TestReport(unittest.TestCase):

    def test_format_dictionary(self):
        #: run with --nocapture and look at tox console output
        good_crate = {'name': 'Good-Crate', 'result': Crate.CREATED, 'crate_message': None}
        bad_crate = {'name': 'Bad-Crate', 'result': Crate.UNHANDLED_EXCEPTION, 'crate_message': 'This thing blew up.'}

        success = {'name': 'Successful Pallet', 'success': True, 'message': None, 'crates': [good_crate, good_crate]}
        fail = {'name': 'Fail Pallet', 'success': False, 'message': 'What Happened?!', 'crates': [bad_crate, good_crate]}

        report = {'total_pallets': 2, 'num_success_pallets': 1, 'pallets': [success, fail], 'total_time': '5 minutes'}

        print(cli._format_dictionary(report))
