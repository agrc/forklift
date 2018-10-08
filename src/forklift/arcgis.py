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
        required_fields = 'Required information for connecting to ArcGIS Server do not exist. '
        'Server will not be stopped or started. See README.md for more details.'

        if len(server) != 2:
            log.warning(required_fields)

            raise Exception(required_fields)

        self.server_label = server[0]
        server = server[1]
        self.server_qualified_name = server['machineName']

        if None in [server['username'], server['password'], server['machineName']]:
            log.warning(required_fields)

            raise Exception(required_fields)

        self.username = server['username']
        self.password = server['password']

        self.token_expire_milliseconds = 0
        self.token = None
        self.timeout = 120

        base_url = '{}://{}:{}/arcgis/admin'.format(server['protocol'], server['machineName'], server['port'])
        self.token_url = '{}/generateToken'.format(base_url)
        self.switch_url = '{}/machines/{}/'.format(base_url, server['machineName'])
        self.services_url = '{}/services'.format(base_url)

    def ensure(self, what):
        '''
        what: string 'stop' or 'start'
        server: dictionary of server to stop

        ensures that affected_services are started or stopped with 5 attempts

        returns the services that still did not do what was requested
        '''
        tries = 4
        wait = [12, 8, 4, 2, 0]
        status = False

        while not status and tries >= 0:
            sleep(wait[tries])
            tries -= 1

            status, message = self._execute(self.switch_url + what)

            self._started = what == 'start'

        return status, message

    def validate_service_state(self):
        '''Validates that services that are configured to be started are actually started

        Returns a list of services that did not start properly
        '''
        if not self._started:
            return []

        #: get service paths
        root = self._fetch(self.services_url)
        serviceInfos = root['services']
        for folder in root['folders']:
            folderJson = self._fetch('{}/{}'.format(self.services_url, folder))
            serviceInfos += folderJson['services']

        #: check status of each service
        services = {}
        for info in serviceInfos:
            if info['folderName'] == '/':
                service_path = '{}.{}'.format(info['serviceName'], info['type'])
            else:
                service_path = '{}/{}.{}'.format(info['folderName'], info['serviceName'], info['type'])

            service_status = self._fetch('{}/{}/status'.format(self.services_url, service_path))

            try:
                if service_status['realTimeState'] != service_status['configuredState']:
                    services.setdefault(self.server_qualified_name, []).append(service_path)
            except KeyError:
                services.setdefault(self.server_qualified_name, []).append(service_path)

        return services

    def _execute(self, url):
        '''url: string

        Posts to `url` ensuring a succussful status after getting a token from server.
        Does not return any response data from the server.

        Retuns a tuple with a boolean status and a message
        '''
        self._check_token_freshness()

        ok = (False, None)
        data = {'f': 'json', 'token': self.token}

        try:
            r = requests.post(url, data=data, timeout=self.timeout)
            r.raise_for_status()

            ok = self._return_false_for_status(r.json())
        except requests.exceptions.ConnectTimeout as t:
            return (False, t)
        except requests.exceptions.Timeout as t:
            return (False, t)
        except requests.exceptions.HTTPError as t:
            return (False, t)

        return ok

    def _fetch(self, url):
        '''url: string

        Posts to `url` ensuring a succussful status after getting a token from server.
        Returns the response data from the server.

        Retuns the json response from the server
        '''
        self._check_token_freshness()

        data = {'f': 'json', 'token': self.token}

        r = requests.post(url, data=data, timeout=self.timeout)
        r.raise_for_status()

        return r.json()

    def _check_token_freshness(self):
        '''checks the token expiration and requests a new one if it has expired
        '''
        if self.token_expire_milliseconds <= time() * 1000:
            self._request_token()

    def _return_false_for_status(self, json_response):
        '''json_reponse: string - a json payload from a server

        looks for a status in the json reponse and makes sure it does not contain an error

        Returns a tuple with a boolean status and a message
        '''
        if 'status' in list(json_response.keys()) and json_response['status'] == 'error':
            if 'Token Expired.' in json_response['messages']:
                self._request_token()

                return (True, 'Requested new token')
            else:
                return (False, '; '.join(json_response['messages']))

        return (True, None)

    def _request_token(self):
        '''Makes a request to the token service and stores the token information
        '''
        data = {'username': self.username, 'password': self.password, 'client': 'requestip', 'expiration': 60, 'f': 'json'}

        response = requests.post(self.token_url, data=data)
        response.raise_for_status()

        response_data = response.json()
        self._return_false_for_status(response_data)

        self.token = response_data['token']
        self.token_expire_milliseconds = int(response_data['expires'])
