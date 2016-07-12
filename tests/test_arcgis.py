#!/usr/bin/env python
# * coding: utf8 *
'''
test_arcgis.py

A module that tests arcgis.py
'''

import unittest
from forklift import arcgis
from forklift.arcgis import LightSwitch
from mock import Mock
from mock import patch
from time import time


class TestLightSwitch(unittest.TestCase):

    def setUp(self):
        arcgis.username = 'name'
        arcgis.password = 'password'
        arcgis.server = 'host'

        self.patient = LightSwitch()

    def test_turn_on(self):
        flip_switch_mock = Mock()

        self.patient._flip_switch = flip_switch_mock

        self.patient.turn_on('MyService', 'ServiceType')

        flip_switch_mock.assert_called_once()
        flip_switch_mock.assert_called_with('MyService', 'ServiceType', 'start')

    def test_turn_off(self):
        flip_switch_mock = Mock()

        self.patient._flip_switch = flip_switch_mock

        self.patient.turn_off('MyService', 'ServiceType')

        flip_switch_mock.assert_called_once()
        flip_switch_mock.assert_called_with('MyService', 'ServiceType', 'stop')

    def test_flip_switch(self):
        fetch_mock = Mock()

        self.patient._fetch = fetch_mock

        self.patient._flip_switch('MyService', 'ServiceType', 'action')

        fetch_mock.assert_called_once()
        fetch_mock.assert_called_with('http://host:6080/arcgis/admin/services/MyService.ServiceType/action')

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
        affected_services = [('1', 'MapServer')]

        self.patient.turn_on = Mock(return_value=(False, ''))
        self.patient.turn_off = Mock()

        status, affected_services = self.patient.ensure('on', affected_services)

        self.assertFalse(status)
        self.assertEqual('1.MapServer', affected_services)
        self.assertEqual(self.patient.turn_on.call_count, 5)
        self.patient.turn_off.assert_not_called()
        sleep.assert_has_calls([call(1), call(2), call(3), call(5), call(8)])

    @patch('forklift.arcgis.sleep')
    def test_ensure_returns_formatted_problems(self, sleep):
        affected_services = [('1', 'MapServer'), ('2', 'GPServer'), ('3', 'GeocodeServer')]

        self.patient.turn_on = Mock(return_value=(False, ''))
        self.patient.turn_off = Mock()

        status, affected_services = self.patient.ensure('on', affected_services)

        self.assertEqual('1.MapServer, 2.GPServer, 3.GeocodeServer', affected_services)

    @patch('forklift.arcgis.sleep')
    def test_ensure_tries_until_success(self, sleep):
        affected_services = [('1', 'MapServer')]

        self.patient.turn_on = Mock(side_effect=[(False, ''), (True, '')])
        self.patient.turn_off = Mock()

        status, affected_services = self.patient.ensure('on', affected_services)

        self.assertTrue(status)
        self.assertEqual(affected_services, '')
        self.patient.turn_off.assert_not_called()
        self.assertEqual(self.patient.turn_on.call_count, 2)
        sleep.assert_has_calls([call(1)])
