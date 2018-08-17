#!/usr/bin/python3

# check_ethercalc.py - Nagios/Icinga check script for Ethercalc instances
#
# Licensed under the GNU GPLv3
# (c) 2018 doobry@systemli.org

import argparse
from datetime import datetime, timedelta
import nagiosplugin
import requests
import time

class EtherCalc(nagiosplugin.Resource):
    """Domain model: Count of Ethercalc rooms.

    Determines the count of rooms on an Ethercalc instance.
    """

    def __init__(self, protocol='http', host='localhost', port=8000):
        self.protocol   = protocol
        self.host       = host
        self.port       = port
        self.roomids    = self.getCalcIDs()

    def getCalcIDs(self):
        req = requests.get('{}://{}:{}/_rooms/'.format(self.protocol,
                self.host, self.port))
        roomids = req.json()
        return roomids

    def probe(self):
        roomcount = len(self.roomids)
        return [nagiosplugin.Metric('roomcount', roomcount, min=0,
                                    context='roomcount')]

class LoadSummary(nagiosplugin.Summary):
    def ok(self, results):
        return '{} active rooms'.format(results['roomcount'].metric)

    problem = ok

def main():
    argp = argparse.ArgumentParser(description=__doc__)
    argp.add_argument('-H', '--hostname', metavar='HOST', default='localhost',
                help='hostname of the Ethercalc instance (default: localhost)')
    argp.add_argument('-p', '--port', metavar='PORT', default='8000',
                help='port of the Ethercalc instance (default: 8000)')
    argp.add_argument('-w', '--warning', metavar='RANGE', default='',
                help='return warning if room count is outside RANGE')
    argp.add_argument('-c', '--critical', metavar='RANGE', default='',
                help='return critical if room count is outside RANGE')
    args = argp.parse_args()

    check = nagiosplugin.Check(
                EtherCalc(host=args.hostname, port=args.port),
                nagiosplugin.ScalarContext('roomcount', args.warning,
                    args.critical),
                LoadSummary())
    check.main()

if __name__ == '__main__':
    main()
