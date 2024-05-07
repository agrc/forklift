from forklift.models import Pallet


class BuildSignaturePallet(Pallet):
    def build(self):
        pass


class ExceptionPallet(Pallet):
    def build(self, config):
        raise Exception("This is a test")


class SuccessPallet(Pallet):
    def build(self, config):
        print("hello")
