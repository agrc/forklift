from forklift.models import Pallet
import os


class PalletTwo(Pallet):
    def __init__(self):
        super(PalletTwo, self).__init__()
        print('pallet two init')
        print('join: {}'.format(os.path.join('a', 'b')))

    def build(self, config):
        print('pallet two build')
        print('join: {}'.format(os.path.join('a', 'b')))
