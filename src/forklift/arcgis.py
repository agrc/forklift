#!/usr/bin/env python
# * coding: utf8 *
'''
arcgis.py

A module that contains a class to control arcgis services.
'''

import logging
import requests
from os import environ
from time import sleep
from time import time


log = logging.getLogger('forklift')

base_url = r'http://{}:6080/arcgis/admin/'
token_url = r'{}generateToken'.format(base_url)
services_url = r'{}services'.format(base_url)


class LightSwitch(object):
    def __init__(self):
        self.username = environ.get('FORKLIFT_AGS_USERNAME')
        self.password = environ.get('FORKLIFT_AGS_PASSWORD')
        self.server = environ.get('FORKLIFT_AGS_SERVER_HOST')
        self.token = None
        self.token_expire_milliseconds = 0
        self.payload = None

    def ensure(self, what, affected_services):
        '''
        ensures that affected_services are started or stopped with 5 attempts. 
        what: string 'off' or 'on' 
        affected_services: list { service_name, service_type }
        
        returns the services that still did not do what was requested'''
        tries = 4
        wait = [8, 5, 3, 2, 1]

        if None in [self.username, self.password, self.server]:
            log.warn('Required environmental variables for connecting to ArcGIS Server do not exist. ' +
                     'No services will be stopped or started. See README.md for more details.')
            return (True, None)

        while len(affected_services) > 0 and tries >= 0:
            problem_child = []
            sleep(wait[tries])

            for service_name, service_type in affected_services:
                if what == 'off':
                    log.debug('stopping %s.%s', service_name, service_type)
                    status, message = self.turn_off(service_name, service_type)
                else:
                    log.debug('starting %s.%s', service_name, service_type)
                    status, message = self.turn_on(service_name, service_type)

                if not status:
                    problem_child.append((service_name, service_type))

            tries -= 1
            affected_services = problem_child

            if len(affected_services) > 0:
                log.debug('retrying %s',  ', '.join([name + '.' + service for name, service in affected_services]))

        return (len(affected_services) == 0, ', '.join([name + '.' + service for name, service in affected_services]))

    def turn_off(self, service, type):
        return self._flip_switch(service, type, 'stop')

    def turn_on(self, service, type):
        return self._flip_switch(service, type, 'start')

    def _flip_switch(self, service, type, what):
        url = '{}/{}.{}/{}'.format(services_url.format(self.server),
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
        if 'status' in list(json_response.keys()) and json_response['status'] == 'error':
            if 'Token Expired.' in json_response['messages']:
                self._request_token()

                return (True, 'Requested new token')
            else:
                return (False, '; '.join(json_response['messages']))

        return (True, None)

    def _request_token(self):
        data = {'username': self.username,
                'password': self.password,
                'client': 'requestip',
                'expiration': 60,
                'f': 'json'}

        response = requests.post(token_url.format(self.server), data=data)
        response.raise_for_status()

        response_data = response.json()
        self._return_false_for_status(response_data)

        self.token = response_data['token']
        self.token_expire_milliseconds = int(response_data['expires'])
