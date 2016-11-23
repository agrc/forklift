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

    def test_determine_deletes_unions_hash_values(self):
        attribute_hashes = {
            'key1': 1,
            'key2': 2,
            'key3': 3,
        }

        geometry_hashes = {
            'key1': 3,
            'key2': 4,
            'key3': 5,
        }

        deletes = self.patient.determine_deletes(attribute_hashes, geometry_hashes)

        self.assertEqual(deletes, set([1, 2, 3, 4, 5]))

    def test_get_delete_where_caluse_is_formatted_correctly(self):
        attribute_hashes = {
            'key1': 1,
            'key2': 2,
            'key3': 3,
        }

        geometry_hashes = {
            'key1': 3,
            'key2': 4,
            'key3': 5,
        }

        self.patient.determine_deletes(attribute_hashes, geometry_hashes)

        self.assertEqual(self.patient.get_delete_where_clause(), 'OBJECTID in (1,2,3,4,5)')

    def test_get_delete_where_caluse_is_empty_when_no_changes(self):
        self.assertEqual(self.patient.get_delete_where_clause(), '')

    def test_has_adds_is_false_when_emtpy(self):
        self.assertFalse(self.patient.has_adds())

    def test_has_adds_is_true_with_values(self):
        self.patient.adds.append((1, 2, 3))

        self.assertTrue(self.patient.has_adds())

    def test_has_deletes_is_false_when_emtpy(self):
        self.assertFalse(self.patient.has_deletes())

    def test_has_deletes_is_false_when_hashes_are_emtpy(self):
        attribute_hashes = {}
        geometry_hashes = {}

        self.patient.determine_deletes(attribute_hashes, geometry_hashes)

        self.assertFalse(self.patient.has_deletes())

    def test_has_deletes_is_true_with_values(self):
        attribute_hashes = {}
        geometry_hashes = {
            'key': 1
        }

        self.patient.determine_deletes(attribute_hashes, geometry_hashes)

        self.assertTrue(self.patient.has_deletes())
