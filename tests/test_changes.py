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

        self.assertEqual(deletes, [1, 2, 3, 4, 5])

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

        self.assertEqual(self.patient.get_deletes_where_clause('OBJECTID', int), 'OBJECTID IN (1,2,3,4,5)')

    def test_get_delete_where_caluse_is_empty_when_no_changes(self):
        self.assertIsNone(self.patient.get_deletes_where_clause('OBJECTID', int))

    def test_has_adds_is_false_when_emtpy(self):
        self.assertFalse(self.patient.has_adds())

    def test_has_adds_is_true_with_values(self):
        self.patient.adds = {'1': 'a', '2': 'b'}

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

    def test_adds_where_clause_is_empty_when_table_ends_with_prefix(self):
        self.patient.table = 'table_suffix'
        self.patient.adds = {'1': 'a', '2': 'b'}
        clause = self.patient.get_adds_where_clause('primary', str, '_suffix')

        self.assertIsNone(clause)

    def test_adds_where_clause_is_in_clause_when_table_is_source(self):
        self.patient.table = 'table_nosuffixmatch'
        self.patient.adds = {'1': 'a', '2': 'b'}
        clause = self.patient.get_adds_where_clause('primary', int, '_suffix')

        #: use a regex since order of adds dictionary isn't guaranteed
        self.assertRegexpMatches(clause, r'primary IN \(\d,\d\)')

    def test_has_changes(self):
        self.assertFalse(self.patient.has_changes())

        self.patient.adds = {'1': 'a', '2': 'b'}

        self.assertTrue(self.patient.has_changes())

        self.patient.adds = {}

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

        self.assertTrue(self.patient.has_changes())

        self.patient.adds = {'1': 'a', '2': 'b'}

        self.assertTrue(self.patient.has_changes())

    def test_get_where_clause_handles_single_in_statement(self):
        where = self.patient._get_where_clause([1, 2], 'NAME', int)
        self.assertEqual(where, 'NAME IN (1,2)')

        where = self.patient._get_where_clause(['1'], 'NAME', str)
        self.assertEqual(where, 'NAME IN (\'1\')')

    def test_get_where_clause_splits_in_statements(self):
        where = self.patient._get_where_clause(range(1, 1100), 'NAME', int)
        self.assertRegexpMatches(where, r'IN \([\d,]*\d\) OR NAME IN \([\d,]*\d\)')

    def test_get_where_clause_is_empty_when_changes_equals_total_rows(self):
        self.patient.adds = {'1': 'a', '2': 'b'}
        self.patient.total_rows = 2
        clause = self.patient.get_adds_where_clause('primary', int, '_suffix')

        self.assertIsNone(clause)

        self.patient._deletes = ['1', '2', '3']
        self.patient.total_rows = 3
        clause = self.patient.get_deletes_where_clause('primary', int)

        self.assertIsNone(clause)
