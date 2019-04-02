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

        self.tries = 4
        self.wait = [12, 8, 4, 2, 1]

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
        status = False

        while not status and self.tries >= 0:
            sleep(self.wait[self.tries])
            self.tries -= 1

            status, message = self._execute(self.switch_url + what)

            self._started = what == 'start'

        return status, message

    def ensure_services(self, what, affected_services):
        '''ensures that affected_services are started or stopped with 5 attempts.
        what: string 'off' or 'on'
        affected_services: list { service_name, service_type }
        returns the services that still did not do what was requested'''

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

        while len(affected_services) > 0 and self.tries >= 0:
            sleep(self.wait[self.tries])
            self.tries -= 1

            affected_services = [act_on_service(service) for service in affected_services]
            affected_services = [service for service in affected_services if service is not None]

            if len(affected_services) > 0:
                log.debug('retrying %s', get_service_names(affected_services))

        self._started = what == 'on'

        return (len(affected_services) == 0, get_service_names(affected_services))

    def validate_service_state(self):
        '''Validates that services that are configured to be started are actually started

        Returns a list of services that did not start properly
        '''
        if not self._started:
            return []

        #: get service paths
        root = self._fetch(self.services_url)
        service_infos = root['services']
        for folder in root['folders']:
            folder_json = self._fetch('{}/{}'.format(self.services_url, folder))
            service_infos += folder_json['services']

        #: check status of each service
        services = []
        for info in service_infos:
            if info['folderName'] == '/':
                service_path = '{}.{}'.format(info['serviceName'], info['type'])
            else:
                service_path = '{}/{}.{}'.format(info['folderName'], info['serviceName'], info['type'])

            service_status = self._fetch('{}/{}/status'.format(self.services_url, service_path))

            try:
                if service_status['realTimeState'] != service_status['configuredState']:
                    services.append(service_path)
            except KeyError:
                services.append(service_path)

        return services

    def turn_off(self, service, type):
        return self._flip_switch(service, type, 'stop')

    def turn_on(self, service, type):
        return self._flip_switch(service, type, 'start')

    def _execute(self, url):
        '''url: string

        Posts to `url` ensuring a successful status after getting a token from server.
        Does not return any response data from the server.

        Returns a tuple with a boolean status and a message
        '''
        ok = (True, None)

        try:
            self._fetch(url)
        except Exception as t:
            return (False, str(t))

        return ok

    def _fetch(self, url):
        '''url: string
        '''
        self._check_token_freshness()

        data = {'f': 'json', 'token': self.token}

        r = requests.post(url, data=data, timeout=self.timeout, verify=False)
        r.raise_for_status()

        data = r.json()
        ok, message = self._return_false_for_status(data)

        if ok:
            return data

        raise Exception(message)

    def _check_token_freshness(self):
        '''checks the token expiration and requests a new one if it has expired
        '''
        if self.token_expire_milliseconds <= time() * 1000:
            self._request_token()

    def _return_false_for_status(self, json_response):
        '''json_response: string - a json payload from a server

        looks for a status in the json response and makes sure it does not contain an error

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

        response = requests.post(self.token_url, data=data, verify=False)
        response.raise_for_status()

        response_data = response.json()
        self._return_false_for_status(response_data)

        self.token = response_data['token']
        self.token_expire_milliseconds = int(response_data['expires'])

    def _flip_switch(self, service, service_type, what):
        log.debug('flipping switch for %s/%s (%s)', service, service_type, what)
        url = '{}/{}.{}/{}'.format(self.services_url, service, service_type, what)

        return self._execute(url)
