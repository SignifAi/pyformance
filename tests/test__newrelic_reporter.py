import json
import os
import socket

from pyformance import MetricsRegistry
from pyformance.meters import SimpleGauge
from pyformance.reporters.newrelic_reporter import NewRelicReporter, NewRelicSink
from tests import TimedTestCase


class TestNewRelicReporter(TimedTestCase):
    def setUp(self):
        super(TestNewRelicReporter, self).setUp()
        self.registry = MetricsRegistry(clock=self.clock, sink=NewRelicSink)
        self.maxDiff = None

    def tearDown(self):
        super(TestNewRelicReporter, self).tearDown()

    def test_report_now(self):
        r = NewRelicReporter(
            'license_key',
            registry=self.registry, reporting_interval=1, clock=self.clock, name='foo')
        h1 = self.registry.histogram("hist", 'a/b')
        for i in range(10):
            h1.add(2 ** i)
        t1 = self.registry.timer("t1")
        gauge = self.registry.gauge('g1', SimpleGauge(unit='g'))
        gauge_value = 10
        gauge.set_value(gauge_value)

        m = self.registry.meter('m1', 'u1/u2')
        m.mark()

        with t1.time():
            m.mark()
            c1 = self.registry.counter("counter-1", 'c')
            c2 = self.registry.counter("counter-2", 'c')
            c1.inc()
            c2.dec()
            c2.dec()
            self.clock.add(1)
            m.mark()
        output = json.loads(r.collect_metrics(self.registry))
        expected = {
            "agent": {
                "host": socket.gethostname(),
                "pid": os.getpid(),
                "version": "0.3.2"
            },
            "components": [
                {
                    "duration": 1,
                    "guid": "com.github.pyformance",
                    "metrics": {
                        "Component/counter-1/raw[c]": {"count": 1, "max": 1, "min": 1, "sum_of_squares": 1, "total": 1},
                        "Component/counter-2/raw[c]": {"count": 2, "max": -1, "min": -2, "sum_of_squares": 5, "total": -3},
                        "Component/t1/raw[event/second]": {"count": 1, "max": 1, "min": 1, "sum_of_squares": 1, "total": 1},
                        "Component/g1/gauge[g]": gauge_value,
                        "Component/hist/raw[a/b]": {"count": 10, "max": 512, "sum_of_squares": 349525, "total": 1023, "min": 1},
                        "Component/m1/raw[u1/u2]": {"count": 3, "max": 1, "sum_of_squares": 3, "total": 3, "min": 1}
                    },
                    "name": "foo"}
            ]
        }

        self.assertEqual(expected, output)
