from threading import Lock

from pyformance.meters.metric import Metric


class Counter(Metric):

    """
    An incrementing and decrementing metric
    """

    def __init__(self, sink=None, unit=None):
        super(Counter, self).__init__(sink, unit)
        self.lock = Lock()
        self.counter = 0

    def inc(self, val=1):
        "increment counter by val (default is 1)"
        with self.lock:
            self.counter += val
            self.add_to_sink(self.counter)

    def dec(self, val=1):
        "decrement counter by val (default is 1)"
        self.inc(-val)

    def get_count(self):
        "return current value of counter"
        return self.counter

    def clear(self):
        "reset counter to 0"
        with self.lock:
            super(Counter, self).clear()
            self.counter = 0
