from forklift.models import Pallet


class ArgumentExamplePallet(Pallet):
    def __init__(self, arg=None):
        super(ArgumentExamplePallet, self).__init__()

        print("arg: {}".format(arg))

        self.arg = arg
