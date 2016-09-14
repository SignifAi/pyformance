from threading import Lock


class Counter(object):

    """
    An incrementing and decrementing metric
    """

    def __init__(self, sink=None):
        super(Counter, self).__init__()
        self.lock = Lock()
        self.counter = 0
        self.sink = sink

    def inc(self, val=1):
        "increment counter by val (default is 1)"
        with self.lock:
            self.counter += val
        if self.sink is not None:
            self.sink.add(self.counter)

    def dec(self, val=1):
        "decrement counter by val (default is 1)"
        self.inc(-val)

    def get_count(self):
        "return current value of counter"
        return self.counter

    def clear(self):
        "reset counter to 0"
        with self.lock:
            self.counter = 0
