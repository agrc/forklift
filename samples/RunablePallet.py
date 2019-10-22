'''
RunablePallet.py

A module that contains a pallet that demonstrates how to make it runnable as a script
outside of the forklift process.

For example:

python samples\RunablePallet.py ->

INFO 12:46:44 6 building pallet
INFO 12:46:44 9 lifting pallet
INFO 12:46:44 12 shipping pallet
'''
from forklift.models import Pallet


class RunablePallet(Pallet):
    def build(self, configuration):
        self.log.info('building pallet')

    def lift(self):
        self.log.info('lifting pallet')

    def ship(self):
        self.log.info('shipping pallet')


if __name__ == '__main__':
    pallet = RunablePallet()
    pallet.configure_standalone_logging()
    pallet.build('Dev')
    pallet.lift()
    pallet.ship()
