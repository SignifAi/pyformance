import os
import socket

from pyformance import MetricsRegistry
from pyformance.reporters.newrelic_reporter import NewRelicReporter, NewRelicSink
from tests import TimedTestCase


class TestNewRelicReporter(TimedTestCase):
    def setUp(self):
        super(TestNewRelicReporter, self).setUp()
        self.registry = MetricsRegistry(clock=self.clock, sink=NewRelicSink())
        self.maxDiff = None

    def tearDown(self):
        super(TestNewRelicReporter, self).tearDown()

    def test_report_now(self):
        r = NewRelicReporter(
            'license_key',
            registry=self.registry, reporting_interval=1, clock=self.clock, name='foo')
        h1 = self.registry.histogram("hist")
        for i in range(10):
            h1.add(2 ** i)
        t1 = self.registry.timer("t1")
        m1 = self.registry.meter("m1")
        m1.mark()
        with t1.time():
            c1 = self.registry.counter("c1")
            c2 = self.registry.counter("counter-2")
            c1.inc()
            c2.dec()
            c2.dec()
            self.clock.add(1)
        output = r.collect_metrics(self.registry)
        expected = '{"agent": {"host": "%s", "pid": %s, "version": "0.3.2"}, "components": [{"duration": 1, "guid": "com.github.pyformance", "metrics": {"Component/t1": {' \
                   '"count": 1, "max": 1, "min": 1, "sum_of_squares": 1, "total": 1}}, "name": "foo"}]}' % (socket.gethostname(), os.getpid())

        self.assertEqual(expected.replace(".0", ""), output.replace(".0", ""))
