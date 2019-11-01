#!/usr/bin/python3

# check_etherpad.py - Nagios/Icinga check script for Etherpad instances
#
# Licensed under the GNU GPLv3
# (c) 2018 doobry@systemli.org

import argparse
from datetime import datetime, timedelta
import nagiosplugin
import requests
import time

class EtherPad(nagiosplugin.Resource):
    """Domain model: Count of Etherpad pads.

    Determines the count of pads on an Etherpad instance.
    """

    def __init__(self, protocol='http', host='localhost', port=9001,
                       apiversion='1.2.13', apikey='abc', suffix=None,
                       ignoresuffix=[]):
        self.protocol     = protocol
        self.host         = host
        self.port         = port
        self.apiversion   = apiversion
        self.apikey       = apikey
        self.suffix       = suffix
        self.ignoresuffix = ignoresuffix
        self.padids       = self.getPadIDs()

    def fetchApi(self, apicmd, apiargs):
        payload = {'apikey': self.apikey}
        if apiargs:
            payload = {**payload, **apiargs}
        req = requests.get('{}://{}:{}/api/{}/{}'.format(self.protocol,
                self.host, self.port, self.apiversion, apicmd),
                 params=payload, timeout=60)
        return req.json()

    def getPadIDs(self):
        apires = self.fetchApi(apicmd='listAllPads', apiargs='')
        allpadids = apires['data']['padIDs']
        padids = []
        for id in allpadids:
            if self.suffix and not id.endswith(self.suffix):
                continue
            if self.ignoresuffix and id.endswith(tuple(self.ignoresuffix)):
                    continue
            padids.append(id)
        return padids

    def getOldestEditedPad(self):
        oldestedited = 0
        for id in self.padids:
            apiargs = {'padID': id}
            apires  = self.fetchApi(apicmd='getLastEdited',
                      apiargs=apiargs)
            lastedited = apires['data']['lastEdited']
            if oldestedited > lastedited:
                oldestedited = lastedited
            elif oldestedited == 0:
                oldestedited = lastedited
        return int(oldestedited / 1000)

    def probe(self):
        padcount = len(self.padids)
        if padcount == 0:
            padage = int(time.mktime(datetime.utcnow().timetuple()))
        else:
            padage = self.getOldestEditedPad()
        return [nagiosplugin.Metric('padcount', padcount, min=0,
                                    context='padcount'),
                nagiosplugin.Metric('padage', padage, min=0,
                                    context='padage')]

class LoadSummary(nagiosplugin.Summary):
    def ok(self, results):
        if results['padage'].metric.value == 0:
            paddays = 0
        else:
            paddays = (datetime.utcnow() -
                    datetime.fromtimestamp(results['padage'].metric.value)).days
        return '{} active pads, oldest pad {} days'.format(
                results['padcount'].metric,
                paddays)
    problem = ok

def main():
    argp = argparse.ArgumentParser(description=__doc__)
    argp.add_argument('-H', '--hostname', metavar='HOST', default='localhost',
                help='hostname of the Etherpad instance (default: localhost)')
    argp.add_argument('-p', '--port', metavar='PORT', default='9001',
                help='port of the Etherpad instance (default: 9001)')
    argp.add_argument('-a', '--apikey', metavar='APIKEY',
                help='apikey for the Etherpad instance')
    argp.add_argument('-s', '--suffix', metavar='SUFFIX',
                help='limit considered pads to this suffix')
    argp.add_argument('-i', '--ignore-suffix', metavar='IGNORE-SUFFIX',
                action='append',
                help='limit considered pads by ignoring this suffix')
    argp.add_argument('-w', '--warning', metavar='RANGE', default='',
                help='return warning if pad count is outside RANGE')
    argp.add_argument('-c', '--critical', metavar='RANGE', default='',
                help='return critical if pad count is outside RANGE')
    argp.add_argument('-W', '--warning-days', metavar='DAYS', type=int,
                default=0,
                help='return warning if oldest edited pad is older than DAYS')
    argp.add_argument('-C', '--critical-days', metavar='DAYS', type=int,
                default=0,
                help='return critical if oldest edited pad is older than DAYS')
    args = argp.parse_args()

    if args.warning_days:
        args.warning_days = int(time.mktime((datetime.utcnow() -
                timedelta(days=args.warning_days)).timetuple()))
    if args.critical_days:
        args.critical_days = int(time.mktime((datetime.utcnow() -
                timedelta(days=args.critical_days)).timetuple()))

    check = nagiosplugin.Check(
                EtherPad(host=args.hostname, apikey=args.apikey,
                    suffix=args.suffix, ignoresuffix=args.ignore_suffix),
                nagiosplugin.ScalarContext('padcount', args.warning,
                    args.critical),
                nagiosplugin.ScalarContext('padage',
                    "{}:".format(args.warning_days),
                    "{}:".format(args.critical_days), fmt_metric='{value}'),
                LoadSummary())
    check.main(timeout=60)

if __name__ == '__main__':
    main()
