from forklift.models import Pallet


class ArgumentExamplePallet(Pallet):
    def __init__(self, arg=None):
        super().__init__()

        print(f"arg: {arg}")

        self.arg = arg
