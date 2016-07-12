from forklift.models import Pallet
from os.path import join


class PalletOne(Pallet):
    def __init__(self):
        super(PalletOne, self).__init__()
        print('pallet one init')
        print('join: {}'.format(join('a', 'b')))

    def build(self, config):
        print('pallet one build')
        print('join: {}'.format(join('a', 'b')))
