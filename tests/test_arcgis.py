#!/usr/bin/env python
# * coding: utf8 *
'''
test_arcgis.py

A module that tests arcgis.py
'''

import unittest
from time import time

import requests
from mock import Mock, call, patch
from nose.tools import raises

from forklift.arcgis import LightSwitch


class TestLightSwitch(unittest.TestCase):

    def setUp(self):
        self.patient = LightSwitch(('primary', {
            'machineName': 'machine.name',
            'username': 'username',
            'password': 'password',
            'protocol': 'protocol',
            'port': 6080
        }))

    def test_ensure_stop(self):
        _fetch_mock = Mock()
        _fetch_mock.side_effect = [(True, None)]

        self.patient._fetch = _fetch_mock

        self.patient.ensure('stop')

        _fetch_mock.assert_called_once()
        _fetch_mock.assert_called_with(self.patient.switch_url + 'stop')

    def test_ensure_start(self):
        _fetch_mock = Mock()
        _fetch_mock.side_effect = [(True, None)]

        self.patient._fetch = _fetch_mock

        self.patient.ensure('start')

        _fetch_mock.assert_called_once()
        _fetch_mock.assert_called_with(self.patient.switch_url + 'start')

    @patch('forklift.arcgis._fetch')
    def test_vaidate_service_state(self, fetch):
        def fake_server(value):
            if value.endswith('arcgis/admin/services?f=json'):
                return '{"folderName":"/","description":"Root folder","folders":["App1"],"services":[{folderName: "/",serviceName: "Service1",type: "MapServer",description: ""}, {folderName: "/",serviceName: "Service2",type: "GPServer",description: ""}]}'
            elif value.endswith('arcgis/admin/services/App1?f=json'):
                return '{"folderName":"/App1","description":"App folder","services":[{folderName: "/App1",serviceName: "Service3",type: "MapServer",description: ""}, {folderName: "/App1",serviceName: "Service4",type: "GPServer",description: ""}]}'
            elif value.endswith('arcgis/admin/services/App1/Service1.MapServer/status?f=json'):
                return '{ configuredState: "STARTED", realTimeState: "STOPPED" }'
            elif value.endswith('arcgis/admin/services/App1/Service2.GPServer/status?f=json'):
                return '{ configuredState: "STARTED", realTimeState: "STARTED" }'
            elif value.endswith('arcgis/admin/services/Service3.MapServer/status?f=json'):
                return '{ configuredState: "STARTED", realTimeState: "STOPPED" }'
            elif value.endswith('arcgis/admin/services/Service4.GPServer/status?f=json'):
                return '{ configuredState: "STARTED", realTimeState: "STARTED" }'

        fetch.side_effect = fake_server

        services = self.patient.validate_service_state()
        self.assertEqual(services, ['App1/Service1.MapServer', 'Service3.Mapserver'])

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
        self.patient._fetch = Mock(return_value=(False, 'failed'))

        status, message, services = self.patient.ensure('start')

        self.assertFalse(status)
        self.assertEqual(message, 'failed')
        self.assertEqual(self.patient._fetch.call_count, 5)
        sleep.assert_has_calls([call(0), call(2), call(4), call(8), call(12)])

    @patch('forklift.arcgis.sleep')
    def test_ensure_returns_formatted_problems(self, sleep):
        self.patient._fetch = Mock(return_value=(False, 'failed'))

        status, message, services = self.patient.ensure('start')

        self.assertEqual('failed', message)

    @patch('forklift.arcgis.sleep')
    def test_ensure_tries_until_success(self, sleep):
        self.patient._fetch = Mock(side_effect=[(False, ''), (True, '')])

        status, message, services = self.patient.ensure('stop')

        self.assertTrue(status)
        self.assertEqual(message, '')
        self.assertEqual(self.patient._fetch.call_count, 2)
        sleep.assert_has_calls([call(0)])

    @patch('forklift.arcgis.requests.post')
    def test_handles_timeout_gracefully(self, post):
        post.side_effect = requests.exceptions.Timeout('timed out')

        self.patient.token_expire_milliseconds = 9223372036854775807
        status, message = self.patient._fetch('url')

        self.assertEqual(post.call
        _count, 1)
        self.assertFalse(status)
        self.assertEqual(message, post.side_effect)

    @patch('forklift.arcgis.requests.post')
    def test_handles_connection_error_gracefully(self, post):
        post.side_effect = requests.exceptions.ConnectTimeout('timed out')

        self.patient.token_expire_milliseconds = 9223372036854775807
        status, message = self.patient._fetch('url')

        self.assertEqual(post.call_count, 1)
        self.assertFalse(status)
        self.assertEqual(message, post.side_effect)

    @patch('forklift.arcgis.requests.post')
    def test_handles_httperror_error_gracefully(self, post):
        post.side_effect = requests.exceptions.HTTPError('http error')

        self.patient.token_expire_milliseconds = 9223372036854775807
        status, message = self.patient._fetch('url')

        self.assertEqual(post.call_count, 1)
        self.assertFalse(status)
        self.assertEqual(message, post.side_effect)

    @raises(KeyError)
    def test_missing_vars(self):
        self.patient = LightSwitch(('primary', {'a': 1}))

    @raises(Exception)
    def test_empty_vars(self):
        self.patient = LightSwitch(('primary', {'username': None, 'password': None, 'machineName': 'test'}))
