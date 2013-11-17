
"""  VirusXControl -- midi interface


"""

import vxclib


def str2lst(s):
    return [ord(c) for c in s]


MIDI_TYPEMASK = 0xF0

MIDITYPE_PERFORM = 1
# comprises:
MIDI_NOTEOFF = 0x80
MIDI_NOTEON = 0x90
MIDI_POLYPRESS = 0xA0
MIDI_CHNPRESS = 0xD0
MIDI_PITCH = 0xE0
MIDI_PERFCTRL = 0xB0

MIDITYPE_CTRL = 2
# comprises:
MIDI_CTRL = 0xB0
MIDI_SYSEX = 0xF0

MIDITYPE_OTHER = 3
# comprises:
MIDI_PRGCHG = 0xC0
MIDI_SYSCOMMON = 0xF0


class MidiMsgError(Exception):
    def __init__(self):
        Exception.__init__(self, 'midi msg incomplete')


class MidiProcessor(object):
    def __init__(self):
        self.msg = []

    def doFinish(self):
        pass
    def doSysEx(self):
        pass

    def dettype(self):
        t = self.msg[0] & MIDI_TYPEMASK
        if t in [MIDI_NOTEOFF, MIDI_NOTEON, MIDI_POLYPRESS,
                 MIDI_CHNPRESS, MIDI_PITCH]:
            self.type = MIDITYPE_PERFORM
        elif t==MIDI_CTRL:
            c = self.msg[1] 
            if c<=4 or c==11 or (c>=64 and c<=66):
                self.type = MIDITYPE_PERFORM
            else:
                self.type = MIDITYPE_CTRL
        elif self.msg[0]==MIDI_SYSEX:
            self.type = MIDITYPE_CTRL
            if self.msgstream:
                self.getSysExEnd()
        else:
            self.type = MIDITYPE_OTHER

    def getSysExEnd(self):
        try:
            self.msglen = self.msg.index(0xF7)+1
        except ValueError:
            raise MidiMsgError

    def processtype(self):
        if self.msg[0]==MIDI_SYSEX:
            self.doSysEx()

    def nextmsg(self):
        i = self.msglen
        if i==0:
            i = 1
        while i<len(self.msg):
            if self.msg[i]&MIDI_TYPEMASK:
                del self.msg[:i]
                self.msglen = 0
                return True
            i += 1
        return False

    def processMsg(self, midimsg, msgstream=False):
        self.msg = midimsg
        self.msgstream = msgstream
        if not msgstream:
            self.dettype()
            self.processtype()
        else:
            self.msglen = 0
            while len(self.msg)>=2:
                self.dettype()
                self.processtype()
                if not self.nextmsg():
                    break

    def processSysExFile(self, sxfile):
        buf = sxfile.read()
        self.processMsg(str2lst(buf), msgstream=True)
        self.doFinish()

    def processMidiFile(self, midifile):
        pass


class NoVirusMidiError(Exception):
    def __init__(self):
        Exception.__init__(self, 'not a Virus midi msg')

class VirusMidiProcessor(MidiProcessor):
    def __init__(self):
        MidiProcessor.__init__(self)
        self.proglist = []
    
    BASE_LEN = 6

    def doSysEx(self):
        msg = self.msg
        if msg[1:5]!=[0,0x20,0x33,1]:
            raise NoVirusMidiError
        if self.msglen<self.BASE_LEN+1:
            raise MidiMsgError
        msgid = msg[6]
        if msgid==0x10:
            self.doSingleDump()

    SINGLEDUMP_BASE = BASE_LEN+3
    SINGLEDUMP_OLDLEN = SINGLEDUMP_BASE+257+1
    SINGLEDUMP_LEN = SINGLEDUMP_OLDLEN+257

    def doSingleDump(self):
        if self.msglen==self.SINGLEDUMP_OLDLEN:
            dump = self.msg[self.SINGLEDUMP_BASE:self.SINGLEDUMP_BASE+256]
        elif self.msglen==self.SINGLEDUMP_LEN:
            dump = self.msg[self.SINGLEDUMP_BASE:self.SINGLEDUMP_BASE+256]
            dump.extend(self.msg[self.SINGLEDUMP_BASE+257:
                                     self.SINGLEDUMP_BASE+513])
        else:
            raise MidiMsgError
        prog = vxclib.SingleProg(dump)
        prog.bpnr = (self.msg[self.BASE_LEN+1], self.msg[self.BASE_LEN+2])
        self.proglist.append(prog)

    def syxtest(self, filename):
        f = open(filename)
        self.proglist = []
        self.processSysExFile(f)

