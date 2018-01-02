#!/usr/bin/env python
# * coding: utf8 *
'''
arcgis.py

A module that contains a class to control arcgis services.
'''

import logging
from os import environ
from time import sleep, time

from multiprocess import Pool

import requests

from . import config

log = logging.getLogger('forklift')

base_url = r'http://{}:6080/arcgis/admin/'
token_url = r'{}generateToken'.format(base_url)
services_url = r'{}services'.format(base_url)


class LightSwitch(object):
    def __init__(self):
        self.reset_credentials()
        self._reset_token()

    def set_credentials(self, username, password, host):
        '''updates the credentials that LightSwitch will use to stop and start services
        '''
        if username:
            self.username = username
        if password:
            self.password = password
        if host:
            self.server = host

        if not username and not password and not host:
            raise Exception('Setting all credentials to empty values will use the default env values.')

        self._reset_token()

    def reset_credentials(self):
        '''reset the credentials to the environmental settings
        '''
        self.username = environ.get('FORKLIFT_AGS_USERNAME')
        self.password = environ.get('FORKLIFT_AGS_PASSWORD')
        self.server = environ.get('FORKLIFT_AGS_SERVER_HOST')

    def ensure(self, what, affected_services):
        '''ensures that affected_services are started or stopped with 5 attempts.
        what: string 'off' or 'on'
        affected_services: list { service_name, service_type }

        returns the services that still did not do what was requested'''
        tries = 4
        wait = [8, 5, 3, 2, 1]

        if None in [self.username, self.password, self.server]:
            log.warn('Required environmental variables for connecting to ArcGIS Server do not exist. ' +
                     'No services will be stopped or started. See README.md for more details.')
            return (True, None)

        def act_on_service(service_info):
            #: logs within this context do not show up in the console or log file
            service_name, service_type = service_info
            if what == 'off':
                status, message = self.turn_off(service_name, service_type)
            else:
                status, message = self.turn_on(service_name, service_type)

            if not status:
                return (service_name, service_type)
            return None

        def get_service_names(services):
            return ', '.join([name + '.' + service for name, service in affected_services])

        while len(affected_services) > 0 and tries >= 0:
            sleep(wait[tries])
            tries -= 1

            num_processes = environ.get('FORKLIFT_POOL_PROCESSES')
            swimmers = num_processes or config.default_num_processes
            if swimmers > len(affected_services):
                swimmers = len(affected_services)
            with Pool(swimmers) as pool:
                log.debug('affected services: %s', get_service_names(affected_services))
                affected_services = [service for service in pool.map(act_on_service, affected_services) if service is not None]

            if len(affected_services) > 0:
                log.debug('retrying %s', get_service_names(affected_services))

        return (len(affected_services) == 0, get_service_names(affected_services))

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

        ok = False
        data = {'f': 'json', 'token': self.token}

        try:
            r = requests.post(url, data=data, timeout=30)
            r.raise_for_status()

            ok = self._return_false_for_status(r.json())
        except requests.exceptions.Timeout:
            return False
        except requests.exceptions.ConnectTimeout:
            return False

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

    def _reset_token(self):
        self.token = None
        self.token_expire_milliseconds = 0
        self.payload = None
