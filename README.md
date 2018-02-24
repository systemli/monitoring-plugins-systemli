# monitoring-plugins-systemli

The monitoring plugins for Icinga/Nagios are developed and used by
systemli.org.

## check_etherpad.py

`check_etherpad.py` gets two metrics from an Etherpad instance:

* *padcount*: Count of pads
* *padpage*: Unix timestamp of the oldest `lastEdited` time (We use it
  to monitor automatic pad cleanup - we delete unchanged pads after some
  time for privacy reasons.)

## check_postfix.py

`check_postfix.py` determines the mail throughput from a postfix log
file (usually `/var/log/mail.log`).

* *Sent*, *received*, *greylisted* and *rejected* messages are counted
  seperately.
* Last *minute*, *hour*, *day* and *week* are supported as time frame
  (can be set via `--mode`).

Technical detail: the log is parsed by using a binary search for
performance reasons.

## check_prosody.py

`check_prosody.py` gets various metrics from a Prosody XMPP server.
Supported modes are:

* *c2s*: current client to server connections (*secure* and *insecure*)
* *s2s*: current server to server connections (*incoming* and *outgoing*)
* *presence*: client presence (*available*, *chat*, *away*, *xa*, *dnd*)
* *uptime*: Prosody uptime in days
* *users*: number of registered users

# License

The systemli monitoring plugins are licensed under the GNU GPLv3.
