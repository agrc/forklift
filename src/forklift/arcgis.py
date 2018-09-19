#!/usr/bin/env python
# * coding: utf8 *
'''
arcgis.py

A module that contains a class to control arcgis services.
'''

import logging
from time import sleep, time

import requests

log = logging.getLogger('forklift')


class LightSwitch(object):

    def __init__(self, server):
        if None in [server['username'], server['password'], server['machineName']]:
            required_fields = 'Required information for connecting to ArcGIS Server do not exist. '
            'Server will not be stopped or started. See README.md for more details.'
            log.warn(required_fields)

            raise Exception(required_fields)

        self.username = server['username']
        self.password = server['password']

        base_url = '{}://{}:{}/arcgis/admin'.format(server['protocol'], server['machineName'], server['port'])
        self.token_url = '{}/generateToken'.format(base_url)
        self.switch_url = '{}/machines/{}/'.format(base_url, server['machineName'])
        self.token_expire_milliseconds = 0

    def ensure(self, what):
        '''ensures that affected_services are started or stopped with 5 attempts.
        what: string 'stop' or 'start'
        server: dictionary of server to stop

        returns the services that still did not do what was requested'''
        tries = 4
        wait = [8, 5, 3, 2, 1]
        status, message = self._flip_switch(self.switch_url, what)

        while not status and tries >= 0:
            sleep(wait[tries])
            tries -= 1

            status, message = self._flip_switch(self.switch_url, what)

        return status, message

    def _flip_switch(self, url, what):
        return self._fetch(url + what)

    def _fetch(self, url):
        # check to make sure that token isn't expired
        if self.token_expire_milliseconds <= time() * 1000:
            self._request_token()

        ok = (False, None)
        data = {'f': 'json', 'token': self.token}

        try:
            r = requests.post(url, data=data, timeout=120)
            r.raise_for_status()

            ok = self._return_false_for_status(r.json())
        except requests.exceptions.Timeout as t:
            return (False, t)
        except requests.exceptions.ConnectTimeout as t:
            return (False, t)

        return ok

    def _return_false_for_status(self, json_response):
        if 'status' in list(json_response.keys()) and json_response['status'] == 'error':
            if 'Token Expired.' in json_response['messages']:
                self._request_token()

                return (True, 'Requested new token')
            else:
                return (False, '; '.join(json_response['messages']))

        return (True, None)

    def _request_token(self):
        data = {'username': self.username, 'password': self.password, 'client': 'requestip', 'expiration': 60, 'f': 'json'}

        response = requests.post(self.token_url, data=data)
        response.raise_for_status()

        response_data = response.json()
        self._return_false_for_status(response_data)

        self.token = response_data['token']
        self.token_expire_milliseconds = int(response_data['expires'])
