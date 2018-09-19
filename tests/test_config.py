#!/usr/bin/env python
# * coding: utf8 *
'''
test_config.py

A module that contains tests for config.py
'''

import unittest
from os import remove
from os.path import abspath, dirname, exists, join

from mock import patch

from forklift import config

config.config_location = join(abspath(dirname(__file__)), 'config.json')


class ConfigTest(unittest.TestCase):
    def setUp(self):
        if exists(config.config_location):
            remove(config.config_location)

    def tearDown(self):
        if exists(config.config_location):
            remove(config.config_location)

    def test_set_config_prop_overrides_all_values(self):
        folder = 'blah'
        config.set_config_prop('warehouse', folder, override=True)

        self.assertEqual(config.get_config_prop('warehouse'), folder)

    @patch('forklift.config.create_default_config', wraps=config.create_default_config)
    def test_get_config_creates_default_config(self, mock_obj):
        config._get_config()

        mock_obj.assert_called_once()

    @patch('forklift.config._get_config')
    def test_set_config_prop_returns_message_if_not_found(self, mock_obj):
        mock_obj.return_value = {}

        message = config.set_config_prop('this was', 'not found')

        self.assertEqual(message, 'this was not found in config.')

    @patch('forklift.config._get_config')
    def test_set_config_prop_appends_items_from_list_if_not_overriding(self, mock_obj):
        mock_obj.return_value = {'test': []}

        message = config.set_config_prop('test', [1, 2, 3])

        self.assertEqual(message, 'Added [1, 2, 3] to test')

    @patch('forklift.config._get_config')
    def test_set_config_prop_sets_value(self, mock_obj):
        mock_obj.return_value = {'test': ''}

        message = config.set_config_prop('test', 'value')

        self.assertEqual(message, 'Added value to test')

    @patch('forklift.config._get_config')
    def test_config_values_merge_from_parent_options(self, mock_obj):
        mock_obj.return_value = {
            'servers': {
                'options': {
                    'username': 'username',
                    'password': 'password',
                    'port': 0
                },
                '0': {
                    'machineName': '0-host',
                },
                '1': {
                    'machineName': '1-host'
                },
                '2': {
                    'machineName': '2-host',
                    'username': 'other-username',
                    'password': 'other-password',
                    'port': 1
                }
            }
        }

        servers = config.get_config_prop('servers')
        self.assertEqual(servers['0'], {
            'machineName': '0-host',
            'username': 'username',
            'password': 'password',
            'port': 0
        })

        self.assertEqual(servers['1'], {
            'machineName': '1-host',
            'username': 'username',
            'password': 'password',
            'port': 0
        })

        self.assertEqual(servers['2'], {
            'machineName': '2-host',
            'username': 'other-username',
            'password': 'other-password',
            'port': 1
        })
