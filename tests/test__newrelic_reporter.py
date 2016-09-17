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

        m = self.registry.meter('m1', 'u1')
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
                "version": "0.3.3"
            },
            "components": [
                {
                    "duration": 1,
                    "guid": "com.github.pyformance",
                    "metrics": {
                        "Component/hist/raw[a/b]": {
                            "max": 512,
                            "total": 1023,
                            "min": 1,
                            "count": 10,
                            "sum_of_squares": 349525
                        },
                        "Component/t1/95_percentile[event/minute]": 1.,
                        "Component/hist/999_percentile[a/b]": 512,
                        "Component/counter-2/raw[c]": {
                            "total": -3,
                            "max": -1,
                            "count": 2,
                            "sum_of_squares": 5,
                            "min": -2
                        },
                        "Component/t1/mean_rate[event/minute]": 1.,
                        "Component/t1/999_percentile[event/minute]": 1.,
                        "Component/m1/1m_rate[u1/minute]": 0,
                        "Component/t1/15m_rate[event/minute]": 0,
                        "Component/hist/99_percentile[a/b]": 512,
                        "Component/t1/raw[event/minute]": {
                            "min": 1,
                            "count": 1,
                            "sum_of_squares": 1,
                            "max": 1,
                            "total": 1
                        },
                        "Component/m1/mean_rate[u1/minute]": 3.,
                        "Component/hist/std_dev[a/b]": 164.94851048466947,
                        "Component/counter-1/raw[c]": {
                            "count": 1,
                            "sum_of_squares": 1,
                            "min": 1,
                            "max": 1,
                            "total": 1
                        },
                        "Component/t1/50_percentile[event/minute]": 1.,
                        "Component/t1/99_percentile[event/minute]": 1.,
                        "Component/hist/95_percentile[a/b]": 512,
                        "Component/m1/15m_rate[u1/minute]": 0,
                        "Component/hist/75_percentile[a/b]": 160.,
                        "Component/t1/5m_rate[event/minute]": 0,
                        "Component/hist/avg[a/b]": 102.3,
                        "Component/t1/count[event/minute]": 1.,
                        "Component/g1/gauge[g]": 10,
                        "Component/t1/1m_rate[event/minute]": 0,
                        "Component/t1/75_percentile[event/minute]": 1.,
                        "Component/t1/std_dev[event/minute]": 0,
                        "Component/m1/raw[u1]": {
                            "min": 1,
                            "sum_of_squares": 3,
                            "count": 3,
                            "total": 3,
                            "max": 1
                        },
                        "Component/t1/avg[event/minute]": 1.,
                        "Component/m1/5m_rate[u1/minute]": 0
                    },
                    "name": "foo"}
            ]
        }

        self.assertEqual(expected, output)
