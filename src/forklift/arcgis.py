#!/usr/bin/env python
# * coding: utf8 *
'''
arcgis.py

A module that contains a class to control arcgis services.
'''

import requests
import secrets
from time import sleep
from time import time


base_url = r'http://{}:6080/arcgis/admin/'
token_url = r'{}generateToken'.format(base_url)
services_url = r'{}services'.format(base_url)
username = secrets.ags_username
password = secrets.ags_password
server = secrets.ags_server_host


class LightSwitch(object):
    def __init__(self):
        self.token = None
        self.token_expire_milliseconds = 0
        self.payload = None

    def turn_off(self, service, type):
        return self._flip_switch(service, type, 'stop')

    def turn_on(self, service, type):
        return self._flip_switch(service, type, 'start')

    def _flip_switch(self, service, type, what):
        url = '{}/{}.{}/{}'.format(services_url.format(server),
                                   service,
                                   type,
                                   what)
        return self._fetch(url)

    def _fetch(self, url):
        # check to make sure that token isn't expired
        if self.token_expire_milliseconds <= time() * 1000:
            self._request_token()

        data = {'f': 'json', 'token': self.token}

        r = requests.post(url, data=data)
        r.raise_for_status()

        ok = self._return_false_for_status(r.json())

        sleep(3.0)

        return ok

    def _return_false_for_status(self, json_response):
        if 'status' in json_response.keys() and json_response['status'] == 'error':
            return (False, '; '.join(json_response['messages']))

        return (True, None)

    def _request_token(self):
        data = {'username': username,
                'password': password,
                'client': 'requestip',
                'expiration': 60,
                'f': 'json'}

        response = requests.post(token_url.format(server), data=data)
        response.raise_for_status()

        response_data = response.json()
        self._return_false_for_status(response_data)

        self.token = response_data['token']
        self.token_expire_milliseconds = int(response_data['expires'])
