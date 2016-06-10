#!/usr/bin/env python
# * coding: utf8 *
'''
test_config.py

A module that contains tests for config.py
'''

import unittest
from forklift import config
from os.path import exists, join, abspath, dirname
from os import remove
from mock import patch


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
