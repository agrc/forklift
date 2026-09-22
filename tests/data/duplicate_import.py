"""
duplicate_import.py

A module that contains tests to make sure that we can import the same pallet twice
"""

from forklift.models import Pallet


class DuplicatePallet(Pallet):
    def __init__(self):
        super().__init__()
