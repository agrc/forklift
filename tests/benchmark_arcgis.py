#!/usr/bin/env python
'''
benchmark_arcgis.py

A module that benchmarks the arcgis module

Make sure that the services in `SERVICES` are published to your server. Or
change them to match services that are already published to your server.
'''
import sys
from os import path
from time import clock  # NOQA

from forklift.arcgis import LightSwitch  # NOQA

forklift_path = path.join(path.dirname(path.abspath(__file__)), r'..\src')
sys.path.insert(0, forklift_path)


SERVICES = [
    ('Broadband/ExportWebMap', 'GPServer'),
    ('Broadband/FixedCached', 'MapServer'),
    ('Broadband/MobileCached', 'MapServer'),
    ('Broadband/ProviderCoverage', 'MapServer'),
    ('Broadband/WirelineCached', 'MapServer'),
    ('PLPCO/BackgroundLayers', 'MapServer'),
    ('PLPCO/RoadsGeneral', 'MapServer'),
    ('PLPCO/SherlockData', 'MapServer'),
    ('Geolocators/Roads_AddressSystem_ACSALIAS', 'GeocodeServer'),
    ('Geolocators/Roads_AddressSystem_ALIAS1', 'GeocodeServer'),
    ('Geolocators/Roads_AddressSystem_ALIAS2', 'GeocodeServer'),
    ('Geolocators/Roads_AddressSystem_STREET', 'GeocodeServer')
]
NUM_REPEATS = 3


def main():
    light_switch = LightSwitch()

    print('ensuring that services are on to begin with...')
    light_switch.ensure('on', SERVICES)

    def benchmark():
        start = clock()

        print('stopping services...')
        light_switch.ensure('off', SERVICES)

        print('restarting services...')
        light_switch.ensure('on', SERVICES)

        return clock() - start

    sum_times = 0
    for i in range(1, NUM_REPEATS + 1):
        print('repetition #:{}'.format(i))
        sum_times = sum_times + benchmark()

    print('average time: {} seconds'.format(sum_times / NUM_REPEATS))
    print('total time: {} seconds'.format(sum_times))


if __name__ == '__main__':
    main()
