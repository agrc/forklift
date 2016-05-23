#!/usr/bin/env python
# * coding: utf8 *
'''
pallet.py

A module that contains the base class that should be inherited from when building new pallet classes.

Pallets are plugins for the forklift main process. They define a list of crates and
any post processing that needs to happen.
'''

import logging
import settings
from crate import Crate


class Pallet(object):

    def __init__(self):
        #: the table names for all dependent data for an application
        self.crates = []
        #: the logging module to keep track of the pallet
        self.log = logging.getLogger(settings.LOGGER)

    def process(self):
        '''This method will be called by forklift if any of the crates data is modified
        '''
        pass

    def get_crates(self):
        '''returns an array of crates affected by the pallet. This is a self documenting way to know what layers an
        application is using.

        set `self.crates` in your child pallet.
        '''

        return self.crates

    def add_crates(self, crate_infos, defaults={}):
        crate_param_names = ['source_name', 'source', 'destination', 'destination_name']

        for info in crate_infos:
            params = defaults.copy()

            #: info can be a table name here instead of a tuple
            if isinstance(info, basestring):
                params['source_name'] = info
            else:
                for i, val in enumerate(info):
                    params[crate_param_names[i]] = val

            self.crates.append(Crate(**params))

    def add_crate(self, crate_info):
        self.add_crates([crate_info])
