#!/usr/bin/env python
# * coding: utf8 *
'''
test_lift.py

A module that contains tests for the lift.py module
'''

import unittest
from forklift import lift
from json import loads
from os import remove
from os.path import abspath, dirname, join, exists


class TestLift(unittest.TestCase):

    test_data_folder = join(dirname(abspath(__file__)), 'data', 'list_plugins')

    def setUp(self):
        if exists('config.json'):
            remove('config.json')

    def tearDown(self):
        if exists('config.json'):
            remove('config.json')

    def test_init_creates_config_file(self):
        path = lift.init()

        self.assertTrue(exists(path))

        with open(path) as config:
            self.assertEquals(['c:\\scheduled'], loads(config.read()))

    def test_list_plugins(self):
        plugins = lift.list_plugins(paths=[self.test_data_folder])

        self.assertEquals(len(plugins), 3)
        self.assertEquals(plugins[0][0], join(self.test_data_folder, 'multiple_plugins.py'))
        self.assertEquals(plugins[0][1], 'PluginOne')

    def test_set_config_paths_requires_list(self):
        self.assertRaises(Exception, lift._set_config_paths, 'hello')

    def test_add_plugin_folder(self):
        path = lift.init()

        lift.add_plugin_folder('another/folder')

        with open(path) as config:
            self.assertEquals(['c:\\scheduled', 'another/folder'], loads(config.read()))
