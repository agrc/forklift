#!/usr/bin/env python
# * coding: utf8 *
"""
nested.py

A module that contains pallets to be used in test_lift.py tests
"""

from forklift.models import Pallet


class NestedPallet(Pallet):
    def __init__(self):
        super(NestedPallet, self).__init__()
