from time import clock
from contextlib import contextmanager


def get_milliseconds():
    return round(clock() * 1000, 5)


@contextmanager
def measure_time(title):
    start = get_milliseconds()
    yield
    print('{}:{}{} ms'.format(title,
                              ''.join([' ' for x in range(1, 35 - len(title))]),
                              round(get_milliseconds() - start, 5)))
