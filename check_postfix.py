#!/usr/bin/python3

# check_postfix.py - Nagios/Icinga check script for Postfix mail server
#
# Licensed under the GNU GPLv3
# (c) 2018 doobry@systemli.org

import argparse
from datetime import datetime, timedelta
from dateutil import parser
import nagiosplugin
import operator
import os
import re
import sys

class Postfix(nagiosplugin.Resource):
    """Domain model: Get mail throughput from Postfix mail server.

    Get mail throughput (by minute, hour, day, week) from Postfix mail logs.
    """

    def __init__(self, logfile, mode):
        self.logfile = logfile
        self.mode    = mode
        self.now     = datetime.now().replace(microsecond=0)

    def timeFromLine(self, line):
        # Return time object from mail log timestamp
        try:
            t_line = parser.parse(line[0:15])
            return t_line
        except:
            print("Error: unable to get time from line: {}".format(line))
            sys.exit(255)

    def g(self, logfile, t_search):
        f = open(logfile)
        # Get size of file in bytes
        f.seek(0, 2)
        f_size = f.tell()

        # Binary search through file
        left, right = 0, f_size - 1
        while (left < right):
            mid = int((left + right) / 2)
            f.seek(mid)
            # no realign to a line
            if mid:
                f.readline()
            t_line = self.timeFromLine(f.readline())
            if t_search == t_line:
                f.close()
                return mid
            elif t_search > t_line:
                left = mid + 1
            else:
                right = mid - 1
        f.close()
        return mid

    def parseLogs(self, logfile, start=0):
        (sent, recv, grey, rjct) = (0, 0, 0, 0)
        f = open(logfile)
        f.seek(start)
        f.readline()
        for line in f:
            if re.search(" postfix/smtp.* to.*, status=sent", line):
                sent += 1
            elif re.search(" postfix/pipe.* to.*, relay=dovecot, .*, status=sent", line):
                recv += 1
            elif re.search(" postfix/smtpd.* NOQUEUE: reject:.* rejected:", line):
                if re.search("Greylisted", line):
                    grey += 1
                else:
                    rjct += 1

        f.close()
        return (sent, recv, grey, rjct)

    def readLogs(self, logfile, t_search, recurse=0):
        f = open(logfile)
        # read first line
        line = f.readline()
        t_first = self.timeFromLine(line)

        if t_search < t_first:
            f.close() 
            # start timestamp is before logfile, parse whole logfile
            stats = self.parseLogs(logfile, 0)
            # if possible, read parent logfile
            l_rotated = "{}.1".format(logfile)
            if recurse == 0 and os.path.isfile(l_rotated):
                print("RECURSE!!")
                stats_rotated = self.readLogs(l_rotated, t_search, 1)
                stats = tuple(map(operator.add, stats, stats_rotated))
            else:
                print("Warning: Couldn't find all logs, stats are incomplete")
            return stats

        # read last line
        last = line
        while (line != ''):
            last = line
            line = f.readline()
        t_last = self.timeFromLine(last)

        f.close()

        if t_search > t_last:
            return (0, 0, 0, 0)
        else:
            # parse logfile from detected startpoint
            start = self.g(logfile, t_search)
            stats = self.parseLogs(logfile, start)
            return stats

    def probe(self):
        if self.mode == 'minute':
            t_start = self.now - timedelta(minutes=1)
        if self.mode == 'hour':
            t_start = self.now - timedelta(hours=1)
        if self.mode == 'day':
            t_start = self.now - timedelta(days=1)
        if self.mode == 'week':
            t_start = self.now - timedelta(days=7)

        (sent, recv, grey, rjct) = self.readLogs(self.logfile, t_start)
        return [nagiosplugin.Metric('sent', sent, min=0,
                                context=self.mode),
                nagiosplugin.Metric('received', recv, min=0,
                                context=self.mode),
                nagiosplugin.Metric('greylisted', grey, min=0,
                                context=self.mode),
                nagiosplugin.Metric('rejected', rjct, min=0,
                                context=self.mode)]

class LoadSummary(nagiosplugin.Summary):
    def __init__(self, mode):
        self.mode = mode

    def ok(self, results):
        return 'messages per {}: {} sent, {} received, {} greylisted, {} rejected'.format(
                    self.mode,
                    results['sent'].metric,
                    results['received'].metric,
                    results['greylisted'].metric,
                    results['rejected'].metric)

    problem = ok

def main():
    argp = argparse.ArgumentParser(description=__doc__)
    argp.add_argument('-l', '--logfile', metavar='FILE', default='/var/log/mail.log',
                help='Postfix logfile (default: /var/log/mail.log)')
    argp.add_argument('-m', '--mode', metavar='MODE', default='minute',
                help='mode to check: minute, hour, day, week \
                      (default: minute)')
    argp.add_argument('-w', '--warning', metavar='RANGE', default='',
                help='return warning if value is outside RANGE')
    argp.add_argument('-c', '--critical', metavar='RANGE', default='',
                help='return critical if value is outside RANGE')
    args = argp.parse_args()

    check = nagiosplugin.Check(
                Postfix(logfile=args.logfile, mode=args.mode),
                nagiosplugin.ScalarContext(args.mode, args.warning,
                    args.critical),
                LoadSummary(args.mode))
    check.main(timeout=120)

if __name__ == '__main__':
    main()
