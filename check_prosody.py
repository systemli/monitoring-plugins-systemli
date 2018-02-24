#!/usr/bin/python3

# check_prosody.py - Nagios/Icinga check script for Prosody XMPP server
#
# Derived from 'prosody_' Munin plugin by Christoph Heer
#
# Licensed under the GNU GPLv3
# (c) 2018 doobry@systemli.org

import argparse
import nagiosplugin
import os
import re
import requests
import telnetlib

class Prosody(nagiosplugin.Resource):
    """Domain model: Get metrics from Prosody XMPP server.

    Determines different metrics from Prosody XMPP server.
    """

    def __init__(self, host='localhost', port=5582, mode='users'):
        self.host = host
        self.port = port
        self.mode = mode

    def listDirs(self, directory):
        for x in os.listdir(directory):
            if os.path.isdir(os.path.join(directory, x)):
                yield x

    def listFiles(self, directory):
        for x in os.listdir(directory):
            if os.path.isfile(os.path.join(directory, x)):
                yield x

    def getC2s(self):
        c2s_conn_re = re.compile(r"Total:\s(\d+)\s")
        tn = telnetlib.Telnet(self.host, self.port)

        tn.write("c2s:show_secure()".encode('ascii') + b"\n")
        tn_res = tn.read_until(b"secure client connections", 5)
        parsed = c2s_conn_re.findall(tn_res.decode('utf-8'))
        c_sec = int(parsed[0])

        tn.write("c2s:show_insecure()".encode('ascii') + b"\n")
        tn_res = tn.read_until(b"insecure client connections", 5)
        parsed = c2s_conn_re.findall(tn_res.decode('utf-8'))
        c_insec = int(parsed[0])

        tn.write("quit".encode('ascii') + b"\n")
        c_all = c_sec + c_insec
        return (c_sec, c_insec, c_all)

    def getS2s(self):
        s2s_conn_re = re.compile(r"(\d+) outgoing, (\d+) incoming")
        tn = telnetlib.Telnet(self.host, self.port)
        tn.write("s2s:show()".encode('ascii') + b"\n")
        tn_res = tn.read_until(b"incoming connections", 5)
        parsed = s2s_conn_re.findall(tn_res.decode('utf-8'))
        tn.write("quit".encode('ascii') + b"\n")
        return (int(parsed[0][0]), int(parsed[0][1]))

    def getPresence(self):
        c2s_pres_re = re.compile(r"[-\]] (.*?)\(\d+\)")
        tn = telnetlib.Telnet(self.host, self.port)
        tn.write("c2s:show()".encode('ascii') + b"\n")
        tn_res = tn.read_until(b"clients", 5)
        parsed = c2s_pres_re.findall(tn_res.decode('utf-8'))
        tn.write("quit".encode('ascii') + b"\n")
        return (parsed.count("available"), parsed.count("chat"), parsed.count("away"), parsed.count("xa"), parsed.count("dnd"))

    def getUptime(self):
        uptime_re = re.compile(r"\d+")
        tn = telnetlib.Telnet(self.host, self.port)
        tn.write("server:uptime()".encode('ascii') + b"\n")
        tn_res = tn.read_until(b"minutes (", 5)
        parsed = uptime_re.findall(tn_res.decode('utf-8'))
        tn.write("quit".encode('ascii') + b"\n")
        uptime = float(parsed[0]) + float(parsed[1])/24 + \
                 float(parsed[2])/60/24
        return uptime

    def getUsers(self):
        base_dir = "/var/lib/prosody"
        account = 0
        if os.path.isdir(base_dir):
            vhosts = self.listDirs(base_dir)
            for vhost in vhosts:
                account_dir = os.path.join(base_dir, vhost, "accounts")
                if os.path.isdir(account_dir):
                    vhost = vhost.replace("%2e",".")
                    accounts = len(list(self.listFiles(account_dir)))
        return accounts

    def probe(self):
        if self.mode == 'c2s':
            (c_sec, c_insec, c_all) = self.getC2s()
            return [nagiosplugin.Metric('c2s_secure', c_sec, min=0,
                                    context='c2s'),
                    nagiosplugin.Metric('c2s_insecure', c_insec, min=0,
                                    context='c2s'),
                    nagiosplugin.Metric('c2s_all', c_all, min=0,
                                    context='c2s')]
        if self.mode == 's2s':
            (c_out, c_in) = self.getS2s()
            return [nagiosplugin.Metric('s2s_outgoing', c_out, min=0,
                                    context='s2s'),
                    nagiosplugin.Metric('s2s_incoming', c_in, min=0,
                                    context='s2s')]
        if self.mode == 'presence':
            (avail, chat, away, xa, dnd) = self.getPresence()
            return [nagiosplugin.Metric('available', avail, min=0,
                                    context='presence'),
                    nagiosplugin.Metric('chat', chat, min=0,
                                    context='presence'),
                    nagiosplugin.Metric('away', xa, min=0,
                                    context='presence'),
                    nagiosplugin.Metric('xa', dnd, min=0,
                                    context='presence'),
                    nagiosplugin.Metric('dnd', away, min=0,
                                    context='presence')]
        if self.mode == 'uptime':
            uptime = self.getUptime()
            return [nagiosplugin.Metric('uptime', uptime, min=0,
                                    context='uptime')]
        if self.mode == 'users':
            users = self.getUsers()
            return [nagiosplugin.Metric('users', users, min=0,
                                    context='users')]

class LoadSummary(nagiosplugin.Summary):
    def __init__(self, mode='users'):
        self.mode = mode

    def ok(self, results):
        if self.mode == 'c2s':
            return 'Client to Server connections: {} secure, {} insecure, {} total'.format(
                        results['c2s_secure'].metric,
                        results['c2s_insecure'].metric,
                        results['c2s_all'].metric)
        if self.mode == 's2s':
            return 'Server to Server connections: {} outgoing, {} incoming'.format(
                        results['s2s_outgoing'].metric,
                        results['s2s_incoming'].metric)
        if self.mode == 'presence':
            return 'Client presence: {} available, {} chat, {} away, {} xa, {} dnd'.format(
                        results['available'].metric,
                        results['chat'].metric,
                        results['away'].metric,
                        results['xa'].metric,
                        results['dnd'].metric)
        if self.mode == 'uptime':
            return 'Uptime: {} days'.format(results['uptime'].metric)
        if self.mode == 'users':
            return 'Registered users: {}'.format(results['users'].metric)

    problem = ok

def main():
    argp = argparse.ArgumentParser(description=__doc__)
    argp.add_argument('-H', '--hostname', metavar='HOST', default='localhost',
                help='hostname of the Prosody XMPP server \
                      (default: localhost)')
    argp.add_argument('-p', '--port', metavar='PORT', default='5582',
                help='port of the Prosody XMPP server (default: 5582)')
    argp.add_argument('-m', '--mode', metavar='MODE', default='users',
                help='mode to check: c2s, s2s, presence, uptime, users \
                      (default: users)')
    argp.add_argument('-w', '--warning', metavar='RANGE', default='',
                help='return warning if value is outside RANGE')
    argp.add_argument('-c', '--critical', metavar='RANGE', default='',
                help='return critical if value is outside RANGE')
    args = argp.parse_args()

    check = nagiosplugin.Check(
                Prosody(host=args.hostname, port=args.port, mode=args.mode),
                nagiosplugin.ScalarContext(args.mode, args.warning,
                    args.critical),
                LoadSummary(args.mode))
    check.main()

if __name__ == '__main__':
    main()
