# -*- coding: utf-8 -*-
from __future__ import print_function
import json
import os
import socket
import sys
from itertools import chain
import six

from pyformance.__version__ import __version__
from .reporter import Reporter

if sys.version_info[0] > 2:
    import urllib.request as urllib
    import urllib.error as urlerror
else:
    import urllib2 as urllib
    import urllib2 as urlerror

try:
    import newrelic.agent
    NEWRELIC_AGENT = True
except:
    NEWRELIC_AGENT = False


class NewRelicSink(object):
    def __init__(self):
        if NEWRELIC_AGENT:
            self.new_relic_agent_sink = _NewRelicSink()
        else:
            self.new_relic_agent_sink = None

        self.regular_sink = _NewRelicSink()

    def add(self, value):
        if self.new_relic_agent_sink:
            self.new_relic_agent_sink.add(value)
        self.regular_sink.add(value)

    def clear(self):
        if self.new_relic_agent_sink:
            self.new_relic_agent_sink.clear()
        self.regular_sink.clear()


class _NewRelicSink(object):
    def __init__(self):
        self.total = 0
        self.count = 0
        self._min = float('inf')
        self._max = -float('inf')
        self.sum_of_squares = 0

    def add(self, value):
        self.total += value
        self.count += 1
        self.sum_of_squares += value * value
        self._min = min(self._min, value)
        self._max = max(self._max, value)

    def clear(self):
        self.total = 0
        self.count = 0
        self._min = float('inf')
        self._max = -float('inf')
        self.sum_of_squares = 0

    @property
    def min(self):
        return self._min if self._min != float('inf') else 0

    @property
    def max(self):
        return self._max if self._max != -float('inf') else 0


def format_unit(metric):
    if metric.unit is None:
        return ''
    else:
        return '[{}]'.format(metric.unit)


class NewRelicReporter(Reporter):
    """
    Reporter for new relic
    """

    MAX_METRICS_PER_REQUEST = 10000
    PLATFORM_URL = 'https://platform-api.newrelic.com/platform/v1/metrics'

    def __init__(self, license_key, registry=None, name=socket.gethostname(), reporting_interval=60, prefix=None,
                 clock=None, plugin_collection=True):
        super(NewRelicReporter, self).__init__(
            registry, reporting_interval, clock)
        self.name = name
        self.prefix = prefix + "/" if prefix is not None else ""
        self.plugin_collection = plugin_collection

        self.http_headers = {'Accept': 'application/json',
                             'Content-Type': 'application/json',
                             'X-License-Key': license_key}

        if NEWRELIC_AGENT:
            @newrelic.agent.data_source_generator(name='Pyformance')
            def metrics_generator():
                metrics = self.create_metrics(self.registry, 'new_relic_agent_sink', 'Custom')
                return six.iteritems(metrics)

            newrelic.agent.register_data_source(metrics_generator)

    def start(self):
        if self.plugin_collection:
            super(NewRelicReporter, self).start()

    def report_now(self, registry=None, timestamp=None):
        metrics = self.collect_metrics(registry or self.registry)
        if metrics:
            try:
                # XXX: better use http-keepalive/pipelining somehow?
                request = urllib.Request(self.PLATFORM_URL, metrics.encode() if sys.version_info[0] > 2 else metrics)
                for k, v in self.http_headers.items():
                    request.add_header(k, v)
                result = urllib.urlopen(request)
                if isinstance(result, urlerror.HTTPError):
                    raise result
            except Exception as e:
                print(e, file=sys.stderr)

    @property
    def agent_data(self):
        """Return the agent data section of the NewRelic Platform data payload

        :rtype: dict

        """
        return {'host': socket.gethostname(),
                'pid': os.getpid(),
                'version': __version__}

    def create_metrics(self, registry, sink_type='regular_sink', key_name_prefix='Component'):
        results = {}
        # noinspection PyProtectedMember
        gauges = registry._gauges.items()
        for key, gauge in gauges:
            key = '{}/gauge{}'.format(self._get_key_name(key, key_name_prefix), format_unit(gauge))
            results[key] = gauge.get_value()

        # noinspection PyProtectedMember
        for key, histogram in registry._histograms.items():
            key = self._get_key_name(key, key_name_prefix)
            snapshot = histogram.get_snapshot()
            key = '{}/{{}}{}'.format(key, format_unit(histogram))

            results[key.format('avg')] = histogram.get_mean()
            results[key.format('std_dev')] = histogram.get_stddev()
            snapshot = histogram.get_snapshot()
            results[key.format('75_percentile')] = snapshot.get_75th_percentile()
            results[key.format('95_percentile')] = snapshot.get_95th_percentile()
            results[key.format('99_percentile')] = snapshot.get_99th_percentile()
            results[key.format('999_percentile')] = snapshot.get_999th_percentile()

        # noinspection PyProtectedMember
        for key, meter in registry._meters.items():
            key = '{}/{{}}[{}/minute]'.format(self._get_key_name(key, key_name_prefix), meter.unit if meter.unit else 'event')

            results[key.format('15m_rate')] = meter.get_fifteen_minute_rate()
            results[key.format('5m_rate')] = meter.get_five_minute_rate()
            results[key.format('1m_rate')] = meter.get_one_minute_rate()
            results[key.format('mean_rate')] = meter.get_mean_rate()

        # noinspection PyProtectedMember
        for key, timer in registry._timers.items():
            key = '{}/{{}}{}'.format(self._get_key_name(key, key_name_prefix), format_unit(timer))
            snapshot = timer.get_snapshot()
            results.update({key.format("avg"): timer.get_mean(),
                            key.format("count"): timer.get_count(),
                            key.format("std_dev"): timer.get_stddev(),
                            key.format("15m_rate"): timer.get_fifteen_minute_rate(),
                            key.format("5m_rate"): timer.get_five_minute_rate(),
                            key.format("1m_rate"): timer.get_one_minute_rate(),
                            key.format("mean_rate"): timer.get_mean_rate(),
                            key.format("50_percentile"): snapshot.get_median(),
                            key.format("75_percentile"): snapshot.get_75th_percentile(),
                            key.format("95_percentile"): snapshot.get_95th_percentile(),
                            key.format("99_percentile"): snapshot.get_99th_percentile(),
                            key.format("999_percentile"): snapshot.get_999th_percentile()})

        # noinspection PyProtectedMember
        sink_meters = filter(lambda tup: tup[1].sink,
                             chain(registry._timers.items(), registry._counters.items(), registry._histograms.items(),
                                   registry._meters.items()))
        for key, value in sink_meters:
            sink = getattr(value.sink, sink_type)

            if not sink.count:
                continue
            key = "{}/{}{}".format(self._get_key_name(key, key_name_prefix), "raw", format_unit(value))
            results[key] = {
                "total": sink.total,
                "count": sink.count,
                "min": sink.min,
                "max": sink.max,
                "sum_of_squares": sink.sum_of_squares
            }
            sink.clear()

        return results

    def _get_key_name(self, key, prefix="Component"):
        return '{}/{}{}'.format(prefix, self.prefix, key).replace('.', '/')

    def collect_metrics(self, registry):
        body = {
            'agent': self.agent_data,
            'components': [{
                'guid': 'com.github.pyformance',
                'name': self.name,
                'duration': self.reporting_interval,
                'metrics': self.create_metrics(registry)
            }]
        }

        return json.dumps(body, ensure_ascii=False, sort_keys=True)
