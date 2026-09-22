"""
single_pallet.py

A module that contains pallets to be used in test_lift.py tests
"""

from forklift.models import Pallet


class SinglePallet(Pallet):
    def __init__(self):
        super().__init__()
