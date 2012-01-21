#!/usr/bin/env python

import pyrawmidi

def printcmd(cmd):
    for b in cmd:
        print "%02X " % b ,
    print

pyrawmidi.open("hw:1,0,1")

while 1:
    cmd = pyrawmidi.read()
    printcmd(cmd)
