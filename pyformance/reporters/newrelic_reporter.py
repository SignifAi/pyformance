# -*- coding: utf-8 -*-
from __future__ import print_function
import json
import os
import socket
import sys
from itertools import chain

from pyformance.__version__ import __version__
from .reporter import Reporter

if sys.version_info[0] > 2:
    import urllib.request as urllib
    import urllib.error as urlerror
else:
    import urllib2 as urllib
    import urllib2 as urlerror


class NewRelicSink(object):
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

    @property
    def min(self):
        return self._min if self._min != float('inf') else 0

    @property
    def max(self):
        return self._max if self._max != -float('inf') else 0


class NewRelicReporter(Reporter):
    """
    Reporter for new relic
    """

    MAX_METRICS_PER_REQUEST = 10000
    PLATFORM_URL = 'https://platform-api.newrelic.com/platform/v1/metrics'

    def __init__(self, license_key, registry=None, name=socket.gethostname(), reporting_interval=5, prefix="",
                 clock=None):
        super(NewRelicReporter, self).__init__(
            registry, reporting_interval, clock)
        self.name = name
        self.prefix = prefix

        self.http_headers = {'Accept': 'application/json',
                             'Content-Type': 'application/json',
                             'X-License-Key': license_key}

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

    def create_metrics(self, registry):
        results = {}
        # noinspection PyProtectedMember
        meters = chain(registry._timers.items(), registry._counters.items())
        for key, value in meters:
            sink = value.sink

            if not sink.count:
                continue

            full_key = 'Component/{}{}'.format(self.prefix, key)
            results[full_key.replace('.', '/')] = {
                "total": sink.total,
                "count": sink.count,
                "min": sink.min,
                "max": sink.max,
                "sum_of_squares": sink.sum_of_squares
            }
            sink.__init__()

        return results

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
