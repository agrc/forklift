#!/usr/bin/env python
# * coding: utf8 *
'''
test_arcgis.py

A module that tests arcgis.py
'''

import unittest
from time import time

import pytest
import requests
from forklift.arcgis import LightSwitch
from mock import Mock, call, patch


class TestLightSwitch(unittest.TestCase):

    def setUp(self):
        self.patient = LightSwitch(
            ('primary', {
                'machineName': 'machine.name',
                'username': 'username',
                'password': 'password',
                'protocol': 'protocol',
                'port': 6080
            })
        )

    def test_ensure_stop(self):
        _execute_mock = Mock()
        _execute_mock.side_effect = [(True, None)]

        self.patient._execute = _execute_mock

        self.patient.ensure('stop')

        _execute_mock.assert_called_once()
        _execute_mock.assert_called_with(self.patient.switch_url + 'stop')

    def test_ensure_start(self):
        _execute_mock = Mock()
        _execute_mock.side_effect = [(True, None)]

        self.patient._execute = _execute_mock

        self.patient.ensure('start')

        _execute_mock.assert_called_once()
        _execute_mock.assert_called_with(self.patient.switch_url + 'start')

    def test_validate_service_state(self):

        def fake_server(value):
            print(value)
            if value.endswith('arcgis/admin/services'):
                return {
                    'folderName': '/',
                    'description': 'Root folder',
                    'folders': ['App1'],
                    'services': [{
                        'folderName': '/',
                        'serviceName': 'Service1',
                        'type': 'MapServer',
                        'description': ''
                    }, {
                        'folderName': '/',
                        'serviceName': 'Service2',
                        'type': 'GPServer',
                        'description': ''
                    }]
                }
            elif value.endswith('arcgis/admin/services/App1'):
                return {
                    'folderName': '/App1',
                    'description': 'App folder',
                    'services': [{
                        'folderName': 'App1',
                        'serviceName': 'Service3',
                        'type': 'MapServer',
                        'description': ''
                    }, {
                        'folderName': 'App1',
                        'serviceName': 'Service4',
                        'type': 'GPServer',
                        'description': ''
                    }]
                }
            elif value.endswith('arcgis/admin/services/Service1.MapServer/status'):
                return {'configuredState': 'STARTED', 'realTimeState': 'STOPPED'}
            elif value.endswith('arcgis/admin/services/Service2.GPServer/status'):
                return {'configuredState': 'STARTED', 'realTimeState': 'STARTED'}
            elif value.endswith('arcgis/admin/services/App1/Service3.MapServer/status'):
                return {'configuredState': 'STARTED', 'realTimeState': 'STOPPED'}
            elif value.endswith('arcgis/admin/services/App1/Service4.GPServer/status'):
                return {'configuredState': 'STARTED', 'realTimeState': 'STARTED'}

        mock = Mock(side_effect=fake_server)
        self.patient._fetch = mock
        self.patient._started = True
        self.server_qualified_name = 'machine.name'

        services = self.patient.validate_service_state()
        self.assertEqual(services, ['Service1.MapServer', 'App1/Service3.MapServer'])

    def test_vaidate_service_state_returns_empty_when_server_is_stopped(self):
        self.patient._started = False
        services = self.patient.validate_service_state()
        self.assertEqual(len(services), 0)

    @patch('forklift.arcgis.sleep')
    @patch('forklift.arcgis.requests')
    def test_fetch_requests_token_when_expired(self, request, sleep):
        post_response_mock = Mock()
        post_response_mock.raise_for_status = Mock(return_value=False)
        post_response_mock.json = Mock(return_value={'token': 'token1', 'expires': '123'})
        request.post = Mock(return_value=post_response_mock)

        request_token_mock = Mock()
        return_false_for_status_mock = Mock(return_value=(True, None))

        self.patient._request_token = request_token_mock
        self.patient._return_false_for_status = return_false_for_status_mock

        self.patient._fetch('url')

        request_token_mock.assert_called_once()

    @patch('forklift.arcgis.sleep')
    @patch('forklift.arcgis.requests')
    def test_fetch_requests_uses_exiting_token(self, request, sleep):
        post_response_mock = Mock()
        post_response_mock.raise_for_status = Mock(return_value=False)
        post_response_mock.json = Mock(return_value={'token': 'token1', 'expires': '123'})
        request.post = Mock(return_value=post_response_mock)

        request_token_mock = Mock()
        request.post = post_response_mock

        return_false_for_status_mock = Mock(return_value=(True, None))
        self.patient._request_token = request_token_mock
        self.patient.token_expire_milliseconds = (time() * 1000) + 10000
        self.patient._return_false_for_status = return_false_for_status_mock

        self.patient._fetch('url')

        request_token_mock.assert_not_called()

    def test_return_false_for_status_returns_false_if_error_in_status(self):
        bad_status = {'status': 'error', 'messages': ['join', 'me']}

        actual = self.patient._return_false_for_status(bad_status)

        self.assertEqual(actual, (False, 'join; me'))

    def test_return_false_for_status_with_success_returns_true(self):
        bad_status = {'status': '', 'messages': ['yay', 'me']}

        actual = self.patient._return_false_for_status(bad_status)

        self.assertEqual(actual, (True, None))

    @patch('forklift.arcgis.requests')
    def test_request_token(self, request):
        post_response_mock = Mock()
        post_response_mock.raise_for_status = Mock(return_value=False)
        post_response_mock.json = Mock(return_value={'token': 'token1', 'expires': '123'})
        request.post = Mock(return_value=post_response_mock)

        self.patient._return_false_for_status = Mock(return_value=(True, None))

        self.patient._request_token()

        self.assertEqual(self.patient.token, 'token1')
        self.assertEqual(self.patient.token_expire_milliseconds, 123)

    @patch('forklift.arcgis.sleep')
    def test_ensure_tries_five_times_with_failures(self, sleep):
        self.patient._execute = Mock(return_value=(False, 'failed'))

        status, message = self.patient.ensure('start')

        self.assertFalse(status)
        self.assertEqual(message, 'failed')
        self.assertEqual(self.patient._execute.call_count, 5)
        sleep.assert_has_calls([call(1), call(2), call(4), call(8), call(12)])

    @patch('forklift.arcgis.sleep')
    def test_ensure_returns_formatted_problems(self, sleep):
        self.patient._execute = Mock(return_value=(False, 'failed'))

        _, message = self.patient.ensure('start')

        self.assertEqual('failed', message)

    @patch('forklift.arcgis.sleep')
    def test_ensure_tries_until_success(self, sleep):
        self.patient._execute = Mock(side_effect=[(False, ''), (True, '')])

        status, message = self.patient.ensure('stop')

        self.assertTrue(status)
        self.assertEqual(message, '')
        self.assertEqual(self.patient._execute.call_count, 2)
        sleep.assert_has_calls([call(1)])

    @patch('forklift.arcgis.requests.post')
    def test_handles_timeout_gracefully(self, post):
        post.side_effect = requests.exceptions.Timeout('timed out')

        self.patient.token_expire_milliseconds = 9223372036854775807
        status, message = self.patient._execute('url')

        self.assertEqual(post.call_count, 1)
        self.assertFalse(status)
        self.assertEqual(message, str(post.side_effect))

    @patch('forklift.arcgis.requests.post')
    def test_handles_connection_error_gracefully(self, post):
        post.side_effect = requests.exceptions.ConnectTimeout('timed out')

        self.patient.token_expire_milliseconds = 9223372036854775807
        status, message = self.patient._execute('url')

        self.assertEqual(post.call_count, 1)
        self.assertFalse(status)
        self.assertEqual(message, str(post.side_effect))

    @patch('forklift.arcgis.requests.post')
    def test_handles_httperror_error_gracefully(self, post):
        post.side_effect = requests.exceptions.HTTPError('http error')

        self.patient.token_expire_milliseconds = 9223372036854775807
        status, message = self.patient._execute('url')

        self.assertEqual(post.call_count, 1)
        self.assertFalse(status)
        self.assertEqual(message, str(post.side_effect))

    def test_missing_vars(self):
        with pytest.raises(KeyError):
            self.patient = LightSwitch(('primary', {'a': 1}))

    def test_empty_vars(self):
        with pytest.raises(Exception):
            self.patient = LightSwitch(('primary', {'username': None, 'password': None, 'machineName': 'test'}))
