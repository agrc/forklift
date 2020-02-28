#!/usr/bin/env python
# * coding: utf8 *
'''
test_engine.py

A module that contains tests for the engine.py module
'''

import unittest
from json import loads
from os import makedirs, remove, rmdir
from os.path import abspath, dirname, exists, join

import pytest
from mock import Mock, mock_open, patch

from forklift import config, core, engine
from forklift.models import Crate

test_folder = dirname(abspath(__file__))
test_data_folder = join(test_folder, 'data')
test_pallets_folder = join(test_data_folder, 'list_pallets')
config_location = config_location = join(test_folder, 'config.json')


class CleanUpAlternativeConfig(unittest.TestCase):

    def setUp(self):
        if exists(config_location):
            remove(config_location)

    def tearDown(self):
        if exists(config_location):
            remove(config_location)


class TestConfigInit(CleanUpAlternativeConfig):

    def test_init_creates_default_config_file(self):
        path = engine.init()

        self.assertTrue(exists(path))

        with open(path) as config:
            config_dict = loads(config.read())
            self.assertEqual(
                config_dict, {
                    u'changeDetectionTables': [],
                    u'configuration': u'Production',
                    u'dropoffLocation': u'c:\\forklift\\data\\receiving',
                    u'email': {
                        u'smtpServer': u'send.state.ut.us',
                        u'smtpPort': 25,
                        u'fromAddress': u'noreply@utah.gov'
                    },
                    u'hashLocation': u'c:\\forklift\\data\\hashed',
                    u'notify': [u'test@utah.gov'],
                    u'repositories': [],
                    u'sendEmails': False,
                    u'servers': {
                        u'options': {
                            u'protocol': u'http',
                            u'port': 6080,
                            u'username': u'',
                            u'password': u''
                        },
                        u'primary': {
                            u'machineName': u'machine.name.here'
                        }
                    },
                    u'shipTo': u'c:\\forklift\\data\\production',
                    u'warehouse': u'c:\\forklift\\warehouse',
                    u'serverStartWaitSeconds': 300
                }
            )

    def test_init_returns_path_for_existing_config_file(self):
        self.assertEqual(engine.init(), engine.init())


class TestRepos(CleanUpAlternativeConfig):

    def test_add_repo(self):
        engine.add_repo('agrc/forklift')

        with open(config.config_location) as config_file:
            self.assertEqual(['agrc/forklift'], loads(config_file.read())['repositories'])

    def test_add_repo_invalid(self):
        result = engine.add_repo('bad/repo')

        self.assertIn('[Invalid repo name or owner]', str(result))

    @patch('forklift.engine._validate_repo')
    def test_add_repo_checks_for_duplicates(self, _validate_repo_mock):
        _validate_repo_mock.return_value = ''
        engine.add_repo('tests/data')
        engine.add_repo('tests/data')

        with open(config.config_location) as config_file:
            self.assertEqual(loads(config_file.read())['repositories'], ['tests/data'])

    @patch('forklift.engine.lift._remove_if_exists')
    def test_remove_repo(self, lift):
        test_config_path = join(test_data_folder, 'remove_test_config.json')

        with open(config.config_location, 'w') as json_data_file, open(test_config_path) as test_config_file:
            json_data_file.write(test_config_file.read())

        engine.remove_repo('path/one')

        with open(config.config_location) as test_config_file:
            self.assertEqual(['path/two'], loads(test_config_file.read())['repositories'])

    @patch('forklift.config.get_config_prop', return_value='test')
    @patch('forklift.engine._get_repos', return_value=['path/one'])
    @patch('forklift.engine.lift._remove_if_exists')
    def test_deletes_repository_folder(self, lift, remove, config):
        engine.remove_repo('path/one')

        lift.assert_called_once()
        lift.assert_called_with(join('test', 'one'))

    def test_remove_repo_checks_for_existing(self):
        self.assertEqual('{} is not in the repositories list!'.format('blah'), engine.remove_repo('blah'))

    def test_list_repos(self):
        config.set_config_prop('repositories', ['blah', 'blah2'], override=True)

        result = engine.list_repos()

        self.assertEqual(result, ['blah: [Invalid repo name or owner]', 'blah2: [Invalid repo name or owner]'])


class TestListPallets(CleanUpAlternativeConfig):

    def setUp(self):
        engine.init()

    def test_list_pallets(self):
        test_pallets_folder = join(test_data_folder, 'list_pallets')
        pallets, _ = engine._get_pallets_in_folder(test_pallets_folder)

        self.assertEqual(len(pallets), 4)
        self.assertEqual(pallets[0][0], join(test_pallets_folder, 'multiple_pallets.py'))
        self.assertEqual(pallets[0][1].__name__, 'PalletOne')
        self.assertEqual(pallets[3][1].__name__, 'NestedPallet')

    def test_list_pallets_from_config(self):
        config.set_config_prop('warehouse', test_pallets_folder, override=True)
        pallets, _ = engine.list_pallets()

        self.assertEqual(len(pallets), 4)
        self.assertEqual(pallets[0][0], join(test_pallets_folder, 'multiple_pallets.py'))
        self.assertEqual(pallets[0][1].__name__, 'PalletOne')

    def test_list_pallets_order(self):
        pallets, _ = engine._get_pallets_in_file(join(test_data_folder, 'pallet_order.py'))

        self.assertEqual(pallets[0][1].__name__, 'PalletA')
        self.assertEqual(pallets[1][1].__name__, 'PalletB')
        self.assertEqual(pallets[2][1].__name__, 'PalletC')

    def test_get_specific_pallet_in_file(self):
        pallets, _ = engine._get_pallets_in_file(join(test_data_folder, 'pallet_order.py:PalletB'))
        self.assertEqual(len(pallets), 1)
        self.assertEqual(pallets[0][1].__name__, 'PalletB')

    def test_get_pallets_in_file_same_pallet_twice(self):
        #: we should be able to import a pallet more than once from the same file
        #: use case is when you run a specific pallet that is located in the warehouse
        pallets, _ = engine._get_pallets_in_file(join(test_data_folder, 'duplicate_import.py'))
        pallets2, _ = engine._get_pallets_in_file(join(test_data_folder, 'duplicate_import.py'))

        try:
            #: does not raise
            for info in pallets:
                info[1]()
            for info in pallets2:
                info[1]()
        except Exception as e:
            self.fail(e)

    def test_handles_build_errors(self):
        pallets, _ = engine._build_pallets(join(test_data_folder, 'BuildErrorPallet.py'), None)

        self.assertEqual(len([p for p in pallets if p.success[0]]), 1)
        self.assertEqual(len([p for p in pallets if not p.success[0]]), 2)

    def test_pallet_with_import_error(self):
        _, import_error = engine._get_pallets_in_file(join(test_folder, 'PalletWithSyntaxErrors.py'))

        self.assertRegexpMatches(import_error, 'expected an indented block')


@patch('forklift.engine.git_update')
@patch('forklift.lift.process_crates_for')
@patch('forklift.lift.process_pallets')
class TestLiftPallets(CleanUpAlternativeConfig):

    def setUp(self):
        engine.init()

    def test_lift_pallets_with_path(self, process_pallets, process_crates_for, git_update):
        engine.lift_pallets(join(test_pallets_folder, 'multiple_pallets.py'))

        self.assertEqual(len(process_crates_for.call_args[0][0]), 2)
        self.assertEqual(len(process_pallets.call_args[0][0]), 2)

    def test_lift_pallets_with_out_path(self, process_pallets, process_crates_for, git_update):
        config.set_config_prop('warehouse', test_pallets_folder, override=True)
        engine.lift_pallets()

        self.assertEqual(len(process_crates_for.call_args[0][0]), 4)
        self.assertEqual(len(process_pallets.call_args[0][0]), 4)

    def test_lift_pallets_pallet_arg(self, process_pallets, process_crates_for, git_update):
        engine.lift_pallets(join(test_data_folder, 'pallet_argument.py'), 'test')

        pallet = process_crates_for.call_args[0][0][0]
        self.assertEqual(pallet.arg, 'test')

        engine.lift_pallets(join(test_data_folder, 'pallet_argument.py'))

        pallet = process_crates_for.call_args[0][0][0]
        self.assertEqual(pallet.arg, None)

    def test_lift_pallets_alphebetical_order(self, process_pallets, process_crates_for, git_update):
        engine.lift_pallets(join(test_data_folder, 'alphabetize', 'pallet.py'))

        order = [p.__class__.__name__ for p in process_crates_for.call_args[0][0]]

        self.assertEqual(order, ['Pallet1', 'Pallet2', 'Pallet3'])

    @patch('forklift.lift.prepare_packaging_for_pallets')
    def test_lift_pallets_prepare_packaging(self, prepare_mock, process_pallets, process_crates_for, git_update):
        engine.lift_pallets(join(test_data_folder, 'pallet_argument.py'))

        prepare_mock.assert_called_once()


class TestEngineGeneral(unittest.TestCase):

    def test_repo_to_url(self):
        self.assertEqual(engine._repo_to_url('repo'), 'https://github.com/repo.git')

    def test_send_report_email(self):
        pytest.skip()

        template_dir = join(dirname(abspath(__file__)), '..', 'src', 'forklift', 'templates')

        # yapf: disable
        pallet_reports = [{
            'name': 'c:\\TypicalPallet.py:TypicalPallet',
            'success': True,
            'requires_processing': True,
            'post_copy_processed': True,
            'shipped': True,
            'message': '',
            'crates': [{
                'name': 'Counties',
                'result': 'Created table successfully.',
                'crate_message': '',
                'message_level': ''
            }],
            'total_processing_time': '4780 ms'
        }, {
            'name': 'c:\\TypicalPallet.py:FailPallet',
            'success': False,
            'requires_processing': True,
            'post_copy_processed': False,
            'shipped': False,
            'message': 'This pallet had all sorts of problems',
            'crates': [{
                'name': 'Counties',
                'result': 'Created table unsuccessfully.',
                'crate_message': '',
                'message_level': ''
            }],
            'total_processing_time': '4780 ms'
        }]
        # yapf: enable

        problems = ['service1', 'service2']
        data = ['boundaries.gdb', 'otherthing.gdb']
        # problems = []
        # data = []
        ship_status = {
            'hostname': 'testing.host',
            'total_pallets': len(pallet_reports),
            'pallets': pallet_reports,
            'num_success_pallets': len([p for p in pallet_reports if p['success']]),
            'data_moved': data,
            'problem_services': problems,
            'total_time': '5000 ms'
        }

        ship_template = join(template_dir, 'ship.html')

        output = engine._send_report_email(ship_template, ship_status, 'Shipping')
        with open(join(test_data_folder, 'successful_ship.html'), 'w') as report:
            report.write(output)


class TestGitUpdate(CleanUpAlternativeConfig):

    @patch('git.Repo.clone_from')
    @patch('forklift.engine._get_repo')
    @patch('forklift.engine._validate_repo')
    def test_git_update(self, _validate_repo_mock, _get_repo_mock, clone_from_mock):
        remote_mock = Mock()
        remote_mock.pull = Mock()
        remote_mock.pull.return_value = []
        repo_mock = Mock()
        repo_mock.remotes = [remote_mock]
        _get_repo_mock.return_value = repo_mock
        _validate_repo_mock.return_value = ''
        engine.init()
        config.set_config_prop('warehouse', test_pallets_folder, override=True)
        config.set_config_prop('repositories', ['agrc/nested', 'agrc/forklift'])

        results = engine.git_update()

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
            'import_errors': ['an import error']
        }

        print(engine._generate_console_report(report))

    @patch('forklift.engine.dump')
    @patch('builtins.open', mock_open(read_data='1'))
    def test_generate_packing_slip_file(self, dump):
        good_crate = {'name': 'Good-Crate', 'result': Crate.CREATED, 'crate_message': None}
        bad_crate = {'name': 'Bad-Crate', 'result': Crate.UNHANDLED_EXCEPTION, 'crate_message': 'This thing blew up.', 'message_level': 'error'}
        warn_crate = {'name': 'Warn-Crate', 'result': Crate.WARNING, 'crate_message': 'This thing almost blew up.', 'message_level': 'warning'}

        success = {
            'name': 'Successful Pallet',
            'success': True,
            'message': None,
            'ship_on_fail': False,
            'crates': [good_crate, good_crate, warn_crate],
            'total_processing_time': '1 hr',
            'is_ready_to_ship': True
        }
        fail = {
            'name': 'Fail Pallet',
            'success': False,
            'ship_on_fail': False,
            'message': 'What Happened?!',
            'crates': [bad_crate, good_crate],
            'total_processing_time': '2 hrs',
            'is_ready_to_ship': True
        }
        not_ready_to_ship = {
            'name': 'Successful Pallet',
            'success': True,
            'ship_on_fail': False,
            'message': None,
            'crates': [good_crate, good_crate, warn_crate],
            'total_processing_time': '1 hr',
            'is_ready_to_ship': False
        }

        report = {
            'total_pallets': 3,
            'num_success_pallets': 1,
            'git_errors': ['a git error'],
            'pallets': [success, fail, not_ready_to_ship],
            'total_time': '5 minutes'
        }

        engine._generate_packing_slip(report, test_data_folder)

        # pylint: disable=no-member
        open.assert_called_with(join(test_data_folder, engine.packing_slip_file), 'w', encoding='utf-8')
        dump.assert_called_once()
        self.assertEqual(len(dump.call_args[0][0]), 2)

    @patch('forklift.engine._build_pallets', return_data=1)
    def test_process_packing_slip(self, mock):
        with open(join(test_data_folder, 'test_engine', 'packing-slip.json')) as slip_file:
            packing_slip = loads(slip_file.read())

            pallets = engine._process_packing_slip(packing_slip)

            self.assertEqual(len(pallets), 2)


class TestScorchedEarth(CleanUpAlternativeConfig):
    scratch_patch = join(test_data_folder, 'scratch.gdb')

    @patch('forklift.core.scratch_gdb_path', scratch_patch)
    def test_deletes_folders(self):
        test_hash_location = join(test_data_folder, 'hashLocation')
        test_folder = join(test_hash_location, 'test')

        if exists(test_folder):
            rmdir(test_folder)
        makedirs(test_folder)
        config.set_config_prop('hashLocation', test_hash_location)

        engine.scorched_earth()

        self.assertFalse(exists(core.scratch_gdb_path))
        self.assertFalse(exists(test_folder))


class TestShipData(CleanUpAlternativeConfig):
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

    @patch('forklift.engine.listdir', return_value=[])
    def test_ship_exits_if_no_files_or_slip(self, listdir):
        shipped = engine.ship_data()

        self.assertFalse(shipped)

    @patch('forklift.engine._generate_ship_console_report')
    @patch('forklift.engine.socket.gethostname', return_value="test.host")
    @patch('forklift.engine.exists', return_value=True)
    @patch('forklift.engine._process_packing_slip')
    @patch('forklift.config.get_config_prop')
    @patch('forklift.lift.copy_data')
    @patch('forklift.engine.listdir', return_value=[engine.packing_slip_file])
    def test_ship_only_ships_if_only_slip_found(self, listdir, copy_data, config_prop, packing_slip, exists, socket, generate_mock):

        def mock_props(value):
            if value == 'servers':
                return [{'machineName': '0-host', 'username': 'username', 'password': 'password', 'port': 0}]

            return 'whatever'

        config_prop.side_effect = mock_props

        engine.ship_data()

        expected_report = {'hostname': 'test.host', 'total_pallets': 0, 'pallets': [], 'num_success_pallets': 0, 'server_reports': []}

        #: we don't care about total_time since it can vary between test runs
        assert expected_report.items() <= generate_mock.call_args[0][0].items()
        copy_data.assert_not_called()
        packing_slip.assert_called_once()

    @patch('forklift.engine._generate_ship_console_report', return_value='')
    @patch('forklift.engine.exists', return_value=True)
    @patch('forklift.engine._process_packing_slip')
    @patch('forklift.lift.copy_data')
    @patch('forklift.engine.listdir', return_value=[engine.packing_slip_file])
    def test_post_process_if_success(self, listdir, copy_data, packing_slip, exists, generate_mock):
        slip = {'success': True, 'requires_processing': True}
        pallet = Mock(slip=slip, total_processing_time=3)
        pallet.ship.return_value = None
        pallet.post_copy_process.return_value = None
        pallet.copy_data = []
        packing_slip.return_value = [pallet]

        engine.ship_data()

        pallet.ship.assert_called_once()
        pallet.post_copy_process.assert_called_once()

    @patch('forklift.engine._generate_ship_console_report', return_value='')
    @patch('forklift.engine.exists', return_value=True)
    @patch('forklift.engine._process_packing_slip')
    @patch('forklift.lift.copy_data')
    @patch('forklift.engine.listdir', return_value=[engine.packing_slip_file])
    def test_post_process_if_not_success(self, listdir, copy_data, packing_slip, exists, generate_mock):
        slip = {'success': False, 'requires_processing': True}
        pallet = Mock(slip=slip, total_processing_time=3)
        pallet.ship.return_value = None
        pallet.post_copy_process.return_value = None
        pallet.copy_data = []
        packing_slip.return_value = [pallet]

        engine.ship_data()

        pallet.ship.assert_not_called()
        pallet.post_copy_process.assert_not_called()


class TestGetAffectedServices(unittest.TestCase):
    def test_gets_list_of_services(self):
        service1 = ('a', 'b')
        service2 = ('c', 'd')
        service3 = ('e', 'f')
        pallet1 = Mock(copy_data=['path/to/gdb1', 'path/to/gdb2'], arcgis_services=[service1])
        pallet2 = Mock(copy_data=['path/to/gdb1'], arcgis_services=[service2])
        pallet3 = Mock(copy_data=['path/to/gdb3'], arcgis_services=[service3])

        services_affected = engine._get_affected_services(['gdb1'], [pallet1, pallet2, pallet3])

        assert len(services_affected) == 2
        assert service1 in services_affected
        assert service2 in services_affected
        assert service3 not in services_affected
