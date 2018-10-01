#!/usr/bin/env python
# * coding: utf8 *
'''
test_cli.py

A module that contains tests for the cli.py module
'''

import unittest
from json import loads
from os import makedirs, remove
from os.path import abspath, dirname, exists, join

from mock import Mock, mock_open, patch

from forklift import cli, config, core
from forklift.models import Crate

from .mocks import PoolMock

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
            self.assertEqual(
                config_dict, {
                    u'configuration': u'Production',
                    u'dropoffLocation': u'c:\\forklift\\data\\receiving',
                    u'email': {
                        u'smtpServer': u'send.state.ut.us',
                        u'smtpPort': 25,
                        u'fromAddress': u'noreply@utah.gov'
                    },
                    u'hashLocation': u'c:\\forklift\\data\\hashed',
                    u'notify': [u'stdavis@utah.gov', u'sgourley@utah.gov'],
                    u'poolProcesses': 20,
                    u'repositories': [],
                    u'sendEmails': False,
                    u'servers': {
                        u'options': {
                            u'protocol': u'http',
                            u'port': 6080
                        },
                        u'primary': {
                            u'machineName': u'machine.name.here'
                        }
                    },
                    u'shipTo': [u'c:\\forklift\\data\\production'],
                    u"warehouse": u"c:\\scheduled\\warehouse",
                })

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

        self.assertIn('[Invalid repo name or owner]', str(result))

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
        self.assertEqual(pallets[0][1].__name__, 'PalletOne')
        self.assertEqual(pallets[3][1].__name__, 'NestedPallet')

    def test_list_pallets_from_config(self):
        config.set_config_prop('warehouse', test_pallets_folder, override=True)
        pallets = cli.list_pallets()

        self.assertEqual(len(pallets), 4)
        self.assertEqual(pallets[0][0], join(test_pallets_folder, 'multiple_pallets.py'))
        self.assertEqual(pallets[0][1].__name__, 'PalletOne')

    def test_list_pallets_order(self):
        pallets = cli._get_pallets_in_file(join(test_data_folder, 'pallet_order.py'))

        self.assertEqual(pallets[0][1].__name__, 'PalletA')
        self.assertEqual(pallets[1][1].__name__, 'PalletB')
        self.assertEqual(pallets[2][1].__name__, 'PalletC')

    def test_get_specific_pallet_in_file(self):
        pallets = cli._get_pallets_in_file(join(test_data_folder, 'pallet_order.py:PalletB'))
        self.assertEqual(len(pallets), 1)
        self.assertEqual(pallets[0][1].__name__, 'PalletB')

    def test_get_pallets_in_file_same_pallet_twice(self):
        #: we should be able to import a pallet more than once from the same file
        #: use case is when you run a specific pallet that is located in the warehouse
        pallets = cli._get_pallets_in_file(join(test_data_folder, 'duplicate_import.py'))
        pallets2 = cli._get_pallets_in_file(join(test_data_folder, 'duplicate_import.py'))

        try:
            #: does not raise
            for info in pallets:
                info[1]()
            for info in pallets2:
                info[1]()
        except Exception as e:
            self.fail(e)

    def test_handles_build_errors(self):
        pallets, all_pallets = cli._build_pallets(join(test_data_folder, 'BuildErrorPallet.py'), None)

        self.assertEqual(len([p for p in pallets if p.success[0]]), 1)
        self.assertEqual(len([p for p in pallets if not p.success[0]]), 2)


@patch('forklift.cli.git_update')
@patch('forklift.lift.process_crates_for')
@patch('forklift.lift.process_pallets')
class TestLiftPallets(unittest.TestCase):

    def setUp(self):
        if exists(config_location):
            remove(config_location)

        cli.init()

    def tearDown(self):
        if exists(config_location):
            remove(config_location)

    def test_lift_pallets_with_path(self, process_pallets, process_crates_for, git_update):
        cli.lift_pallets(join(test_pallets_folder, 'multiple_pallets.py'))

        self.assertEqual(len(process_crates_for.call_args[0][0]), 2)
        self.assertEqual(len(process_pallets.call_args[0][0]), 2)

    def test_lift_pallets_with_out_path(self, process_pallets, process_crates_for, git_update):
        config.set_config_prop('warehouse', test_pallets_folder, override=True)
        cli.lift_pallets()

        self.assertEqual(len(process_crates_for.call_args[0][0]), 4)
        self.assertEqual(len(process_pallets.call_args[0][0]), 4)

    def test_lift_pallets_pallet_arg(self, process_pallets, process_crates_for, git_update):
        cli.lift_pallets(join(test_data_folder, 'pallet_argument.py'), 'test')

        pallet = process_crates_for.call_args[0][0][0]
        self.assertEqual(pallet.arg, 'test')

        cli.lift_pallets(join(test_data_folder, 'pallet_argument.py'))

        pallet = process_crates_for.call_args[0][0][0]
        self.assertEqual(pallet.arg, None)

    def test_lift_pallets_alphebetical_order(self, process_pallets, process_crates_for, git_update):
        cli.lift_pallets(join(test_data_folder, 'alphabetize', 'pallet.py'))

        order = [p.__class__.__name__ for p in process_crates_for.call_args[0][0]]

        self.assertEqual(order, ['Pallet1', 'Pallet2', 'Pallet3'])

    @patch('forklift.lift.prepare_packaging_for_pallets')
    def test_lift_pallets_prepare_packaging(self, prepare_mock, process_pallets, process_crates_for, git_update):
        cli.lift_pallets(join(test_data_folder, 'pallet_argument.py'))

        prepare_mock.assert_called_once()


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

    @patch('forklift.cli.Pool', return_value=PoolMock())
    @patch('git.Repo.clone_from')
    @patch('forklift.cli._get_repo')
    @patch('forklift.cli._validate_repo')
    def test_git_update(self, _validate_repo_mock, _get_repo_mock, clone_from_mock, poolmock):
        remote_mock = Mock()
        remote_mock.pull = Mock()
        remote_mock.pull.return_value = []
        repo_mock = Mock()
        repo_mock.remotes = [remote_mock]
        _get_repo_mock.return_value = repo_mock
        _validate_repo_mock.return_value = ''
        cli.init()
        config.set_config_prop('warehouse', test_pallets_folder, override=True)
        config.set_config_prop('repositories', ['agrc/nested', 'agrc/forklift'])

        results = cli.git_update()

        clone_from_mock.assert_called_once()
        remote_mock.pull.assert_called_once()
        self.assertEqual(len(results), 0)


class TestPackingSlip(unittest.TestCase):

    def test_format_ticket_for_report(self):
        #: run with --nocapture and look at console output
        good_crate = {'name': 'Good-Crate', 'result': Crate.CREATED, 'crate_message': None}
        bad_crate = {'name': 'Bad-Crate', 'result': Crate.UNHANDLED_EXCEPTION, 'crate_message': 'This thing blew up.', 'message_level': 'error'}
        warn_crate = {'name': 'Warn-Crate', 'result': Crate.WARNING, 'crate_message': 'This thing almost blew up.', 'message_level': 'warning'}

        success = {
            'name': 'Successful Pallet',
            'success': True,
            'message': None,
            'crates': [good_crate, good_crate, warn_crate],
            'total_processing_time': '1 hr'
        }
        fail = {'name': 'Fail Pallet', 'success': False, 'message': 'What Happened?!', 'crates': [bad_crate, good_crate], 'total_processing_time': '2 hrs'}

        report = {
            'total_pallets': 2,
            'num_success_pallets': 1,
            'git_errors': ['a git error'],
            'pallets': [success, fail],
            'total_time': '5 minutes',
        }

        print(cli._generate_console_report(report))

    @patch('forklift.cli.dump')
    @patch('builtins.open', mock_open(read_data='1'))
    def test_generate_packing_slip_file(self, dump):
        good_crate = {'name': 'Good-Crate', 'result': Crate.CREATED, 'crate_message': None}
        bad_crate = {'name': 'Bad-Crate', 'result': Crate.UNHANDLED_EXCEPTION, 'crate_message': 'This thing blew up.', 'message_level': 'error'}
        warn_crate = {'name': 'Warn-Crate', 'result': Crate.WARNING, 'crate_message': 'This thing almost blew up.', 'message_level': 'warning'}

        success = {
            'name': 'Successful Pallet',
            'success': True,
            'message': None,
            'crates': [good_crate, good_crate, warn_crate],
            'total_processing_time': '1 hr'
        }
        fail = {'name': 'Fail Pallet', 'success': False, 'message': 'What Happened?!', 'crates': [bad_crate, good_crate], 'total_processing_time': '2 hrs'}

        report = {'total_pallets': 2, 'num_success_pallets': 1, 'git_errors': ['a git error'], 'pallets': [success, fail], 'total_time': '5 minutes'}

        cli._generate_packing_slip(report, test_data_folder)

        open.assert_called_with(join(test_data_folder, cli.packing_slip_file), 'w', encoding='utf-8')
        dump.assert_called_once()


class TestScorchedEarth(unittest.TestCase):
    scratch_patch = join(test_data_folder, 'scratch.gdb')

    @patch('forklift.core.scratch_gdb_path', scratch_patch)
    def test_deletes_folders(self):
        test_hash_location = join(test_data_folder, 'hashLocation')
        test_folder = join(test_hash_location, 'test')
        makedirs(test_folder)
        config.set_config_prop('hashLocation', test_hash_location)

        cli.scorched_earth()

        self.assertFalse(exists(core.scratch_gdb_path))
        self.assertFalse(exists(test_folder))


class TestShipData(unittest.TestCase):
    sample_slip = '''[
  {
    "name": "c:\\Projects\\GitHub\\forklift\\samples\\TypicalPallet.py:TypicalPallet",
    "success": true,
    "message": "",
    "crates": [
      {
        "name": "Counties",
        "result": "Created table successfully.",
        "crate_message": "",
        "message_level": ""
      }
    ],
    "total_processing_time": "4780 ms"
  }
]'''

    @patch('forklift.cli.listdir', return_value=[])
    def test_ship_exits_if_no_files_or_slip(self, listdir):
        shipped = cli.ship_data()

        self.assertFalse(shipped)

    @patch('forklift.cli.exists', return_value=True)
    @patch('forklift.cli._process_packing_slip')
    @patch('forklift.config.get_config_prop')
    @patch('forklift.lift.copy_data')
    @patch('forklift.cli.listdir', return_value=[cli.packing_slip_file])
    def test_ship_only_ships_if_only_slip_found(self, listdir, copy_data, config_prop, packing_slip, exists):
        def mock_props(value):
            if value == 'servers':
                return [{
                    'machineName': '0-host',
                    'username': 'username',
                    'password': 'password',
                    'port': 0
                }]

            return 'whatever'

        config_prop.side_effect = mock_props

        report = cli.ship_data()

        self.assertEqual(report, [])
        copy_data.assert_not_called()
        packing_slip.assert_called_once()

    @patch('forklift.cli.exists', return_value=True)
    @patch('forklift.cli._process_packing_slip')
    @patch('forklift.lift.copy_data')
    @patch('forklift.cli.listdir', return_value=[cli.packing_slip_file])
    def test_post_process_if_success(self, listdir, copy_data, packing_slip, exists):
        slip = {
            'success': True,
            'requires_processing': True
        }
        pallet = Mock(slip=slip)
        pallet.ship.return_value = None
        pallet.post_copy_process.return_value = None
        packing_slip.return_value = [pallet]

        cli.ship_data()

        pallet.ship.assert_called_once()
        pallet.post_copy_process.assert_called_once()

    @patch('forklift.cli.exists', return_value=True)
    @patch('forklift.cli._process_packing_slip')
    @patch('forklift.lift.copy_data')
    @patch('forklift.cli.listdir', return_value=[cli.packing_slip_file])
    def test_post_process_if_not_success(self, listdir, copy_data, packing_slip, exists):
        slip = {
            'success': False,
            'requires_processing': True
        }
        pallet = Mock(slip=slip)
        pallet.ship.return_value = None
        pallet.post_copy_process.return_value = None
        packing_slip.return_value = [pallet]

        cli.ship_data()

        pallet.ship.assert_not_called()
        pallet.post_copy_process.assert_not_called()
