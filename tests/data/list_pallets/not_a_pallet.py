#!/usr/bin/env python
# * coding: utf8 *
'''
not_a_pallet.py

For tests to make sure that they skip non-pallet files
'''


class Hello(object):

    def __init__(self):
        pass

some_property = 1

#: make sure this fails to import
raise Exception('')
