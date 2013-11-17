#!/usr/bin/env python

import pyrawmidi,thread

def printcmd(cmd):
    for b in cmd:
        print "%02X " % b ,
    print

def midiinthread():
    while 1:
        cmd = pyrawmidi.read()
        printcmd(cmd)


pyrawmidi.open("hw:1,0,1")

thread.start_new_thread(midiinthread, ())

while 1:
    s = raw_input()
    if s=='q':
        break
    elif s.startswith('f'):
        f = s.split()
        pyrawmidi.setfilter(int(f[1]),int(f[2]))

pyrawmidi.close()
pyrawmidi.wait()
pyrawmidi.wait()
