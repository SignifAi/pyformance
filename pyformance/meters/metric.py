import abc
import six


@six.add_metaclass(abc.ABCMeta)
class Metric(object):
    def __init__(self, sink=None, unit=None):
        self.sink = sink
        self.unit = unit

    def clear(self):
        if self.sink is not None:
            self.sink.clear()

    def add_to_sink(self, value):
        if self.sink is not None:
            self.sink.add(value)
