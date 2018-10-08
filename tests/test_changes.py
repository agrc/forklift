#!/usr/bin/env python
# * coding: utf8 *
'''
test_changes.py

A module that contains the tests for the changes model
'''

import unittest

from forklift.models import Changes


class TestChanges(unittest.TestCase):

    def setUp(self):
        self.patient = Changes([])

    def test_has_adds_is_false_when_emtpy(self):
        self.assertFalse(self.patient.has_adds())

    def test_has_adds_is_true_with_values(self):
        self.patient.adds = {1: 'a', 2: 'b'}

        self.assertTrue(self.patient.has_adds())

    def test_has_deletes_is_false_when_emtpy(self):
        self.assertFalse(self.patient.has_deletes())

    def test_has_deletes_is_false_when_hashes_are_emtpy(self):
        attribute_hashes = {}

        self.patient.determine_deletes(attribute_hashes)

        self.assertFalse(self.patient.has_deletes())

    def test_has_deletes_is_true_with_values(self):
        attribute_hashes = {'key': 1}

        self.patient.determine_deletes(attribute_hashes)

        self.assertTrue(self.patient.has_deletes())

    def test_has_changes(self):
        self.assertFalse(self.patient.has_changes())

        self.patient.adds = {1: 'a', 2: 'b'}

        self.assertTrue(self.patient.has_changes())

        self.patient.adds = {}

        attribute_hashes = {
            'key1': 1,
            'key2': 2,
            'key3': 3,
        }

        self.patient.determine_deletes(attribute_hashes)

        self.assertTrue(self.patient.has_changes())

        self.patient.adds = {1: 'a', 2: 'b'}

        self.assertTrue(self.patient.has_changes())
