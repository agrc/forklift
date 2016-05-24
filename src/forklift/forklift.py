#!/usr/bin/env python
# * coding: utf8 *
'''
forklift.py

A module that contains methods to handle pallets
'''

import core


def process(pallets):
    processed_crates = {}

    def dirty(crates):
        for crate in crates:
            if crate['dirty']:
                return True

        return False

    for pallet in pallets:
        for crate in pallet.crates:
            if crate.name in processed_crates:
                pass
            else:
                #: possibly rename to has_changes and accept a crate?
                if not core.check_for_changes(crate):
                    processed_crates.setdefault(pallet.name, []).append({'crate': crate.name, 'dirty': False})
                else:
                    core.update_dataset(crate)
                    processed_crates.setdefault(pallet.name, []).append({'crate': crate.name, 'dirty': True})

        if dirty(processed_crates[pallet.name]):
            pallet.process()
