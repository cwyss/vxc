
"""  VirusXControl -- midi part



"""


import sys, time, thread, pyrawmidi, pickle, re

# ctrlid is a tuple
#   ctrlid = (ctrlpage, ctrlnumber)
# each page contains ctrlnumbers from 0 to 127
# controller page types:

CTRL_VOID = -1
CTRL_A = 0
CTRL_B = 1
CTRL_C = 2
CTRL_6E = 3


CTRL_NAMES = {CTRL_A: 'Ctrl_A',
              CTRL_B: 'Ctrl_B',
              CTRL_C: 'Ctrl_C',
              CTRL_6E: 'Ctrl_6E'}

def makeCtrlInfoStr(ctrlid,  val, defval=None):
    istr = "%s %d: %d" % (CTRL_NAMES[ctrlid[0]], ctrlid[1], val)
    if defval!=None:
        istr += "  (%d)" % defval
    return istr


DUMP_LENGTH = 514

INDEX_TRANSL = {CTRL_A: 0,
                CTRL_B: 128,
                CTRL_6E: 257}

def ctrlIndex(ctrlid):
    """get index of ctrlid in dump"""
#    try:
    ind = INDEX_TRANSL[ctrlid[0]] + ctrlid[1]
#    except KeyError:
#        ind = -1
    return ind



class SingleProg(object):
    SINGLENAME_START = ctrlIndex((CTRL_B, 112))
    SINGLENAME_END   = ctrlIndex((CTRL_B, 122))

    @classmethod
    def voidDump(cls):
        dump = [0] * DUMP_LENGTH
        name = '-Void-'
        for i in range(cls.SINGLENAME_END-cls.SINGLENAME_START):
            if i<len(name):
                dump[cls.SINGLENAME_START+i] = ord(name[i])
            else:
                dump[cls.SINGLENAME_START+i] = ord(' ')
        return dump

    def __init__(self, dump=None):
        if dump!=None:
            self.dump = dump
        else:
            self.dump = self.voidDump()
        self.name = self.makeName()

    def makeName(self):
        name = ''
        for b in self.dump[self.SINGLENAME_START:self.SINGLENAME_END]:
            name += chr(b)
        return name

    def setName(self, name):
        for i in range(self.SINGLENAME_END-self.SINGLENAME_START):
            if i<len(name):
                self.dump[self.SINGLENAME_START+i] = ord(name[i])
            else:
                self.dump[self.SINGLENAME_START+i] = ord(' ')
        self.name = self.makeName()

    def getCtrl(self, ctrlid):
        ind = ctrlIndex(ctrlid)
        return self.dump[ind]

    def setCtrl(self, ctrlid, value):
        ind = ctrlIndex(ctrlid)
        self.dump[ind] = value

    def dumpToFile(self, file):
        for d in self.dump:
            file.write(chr(d))

    @classmethod
    def readFromFile(cls, file, dumplen=DUMP_LENGTH):
        str = file.read(dumplen)
        dump = [ord(c) for c in str]
        return SingleProg(dump)

    def copy(self):
        return SingleProg(list(self.dump))


class SingleBank(object):
    def __init__(self, name):
        self.name = name
        self.progs = []

    def dumpToFile(self, file):
        pickle.dump((self.name,len(self.progs)), file)
        for p in self.progs:
            p.dumpToFile(file)

    @classmethod
    def loadFromFile(cls, file):
#        print "load single banks"
        name, numprogs = pickle.load(file)
#        print name, numprogs
        bank = SingleBank(name)
        for i in range(numprogs):
            bank.progs.append(SingleProg.readFromFile(file))
#            print "new prog ", bank.progs[-1].makeName()
        return bank


PROGLIB_VERSION_1  = 1

PL_NEWLIB  = 0
PL_NEWBANK = 1
PL_NEWPROG = 2

LIMIT_AND = 0
LIMIT_OR = 1

LIMIT_EQ = 0
LIMIT_GE = 1
LIMIT_LE = 2

class ProgLibrary(object):
    def __init__(self, progChange, libChange):
        self.version = PROGLIB_VERSION_1
        self.banks = []
        self.progChange = progChange
        self.libChange = libChange
        self.visible = []
        self.current_bank = 0
        self.current_prog = 0
        self.nolimit = True

    # ctrlcond = list of lists
    # [boolop, ctrlid, relatop, val]
    def setLimitCrit(self, namepat, ctrlcond):
        self.nolimit = True
        if namepat!='':
            repl = lambda m: '\\'+m.group(0)
            namepat = re.sub(r'[.^$+?{}\[\]|()]', repl, namepat.lower())
            repl = lambda m: '.'+m.group(0)
            namepat = re.sub(r'\*', repl, namepat)
            self.namepat = namepat + '$'
            self.nolimit = False
        else:
            self.namepat = ''
        if ctrlcond!=[]:
            ctrlcond[0][0] = -1
            self.ctrlcond = ctrlcond
            self.nolimit = False
        else:
            ctrlcond = []
        self.updateVisible()
        if self.current_bank>=len(self.visible):
            self.current_bank = 0
        self.libChange(PL_NEWLIB)

    def matchProg(self, prog):
        b1 = True
        b2 = True
        for cc in self.ctrlcond:
            val = prog.getCtrl(cc[1])
            relop = cc[2]
            if relop==LIMIT_EQ:
                bb = val==cc[3]
            elif relop==LIMIT_GE:
                bb = val>=cc[3]
            elif relop==LIMIT_LE:
                bb = val<=cc[3]
            boolop = cc[0]
            if boolop==LIMIT_OR:
                b2 = b2 or bb
            elif boolop==LIMIT_AND:
                b1 = b1 and b2
                b2 = bb
            else:
                b2 = bb
        b1 = b1 and b2
        return b1 and bool(re.match(self.namepat, prog.name.lower()))

    def updateVisible(self):
        self.visible = []
        for bi,bank in enumerate(self.banks):
            bv = []
            for pi,prog in enumerate(bank.progs):
                if self.nolimit or self.matchProg(prog):
                    bv.append(pi)
            if self.nolimit or len(bv)>0:
                self.visible.append((bi,bv))

    def appendVisible(self, bankind):
        bi,bv = self.visible[bankind]
        proglist = self.banks[bi].progs
        pi = len(proglist)-1
        # if self.nolimit or re.match(self.namepat, proglist[pi].name.lower()):
        bv.append(pi)
        return len(bv)-1

    def getCurrentBank(self):
        return self.current_bank
    def getCurrentProg(self):
        return self.current_prog
    
    def getBankNames(self):
        names = []
        for bi,bv in self.visible:
            names.append(self.banks[bi].name)
        return names

    def getBankContents(self, bankind):
        bi,bv = self.visible[bankind]
        bank = self.banks[bi]
        contents = []
        for pi in bv:
            contents.append((bank.progs[pi].name, 0))
        return contents

    def getProg(self, progind, bankind):
        try:
            bi,bv = self.visible[bankind]
            pi = bv[progind]
            return self.banks[bi].progs[pi]
        except IndexError:
            return None

    def setBank(self, bank):
        self.current_bank = bank

    def setProg(self, prog, bank=-1):
        if bank==-1:
            bank = self.current_bank
        self.current_bank = bank
        self.current_prog = prog
        p = self.getProg(prog, bank)
        if p:
            self.progChange(p.copy(), sendmidi=True)

    def nextProg(self):
        maxbank = len(self.visible)
        prog,bank = (self.current_prog, self.current_bank)
        prog += 1
        while bank<maxbank:
            bi,bv = self.visible[bank]
            if prog<len(bv):
                break
            else:
                bank += 1
                prog = 0
        if bank<maxbank:
            self.setProg(prog, bank)

    def prevProg(self):
        prog,bank = (self.current_prog, self.current_bank)
        if bank>=len(self.visible):
            bank = len(self.visible)-1
            if bank<0:
                return
        bi,bv = self.visible[bank]
        if prog>=len(bv):
            prog = len(bv)-1
        else:
            prog -= 1
        while prog<0:
            bank -= 1
            if bank<0:
                break
            prog = len(self.visible[bank][1]) - 1
        if prog>=0:
            self.setProg(prog, bank)

    def saveToFile(self, filename):
        f = open(filename, 'w')
        pickle.dump((self.version, len(self.banks)), f)
        for b in self.banks:
            b.dumpToFile(f)
        f.close()

    def loadFromFile(self, filename):
        f = open(filename, 'r')
        self.banks = []
        self.version, numbanks = pickle.load(f)
#        print self.version, numbanks
        for i in range(numbanks):
            self.banks.append(SingleBank.loadFromFile(f))
        f.close()
        self.updateVisible()
        self.libChange(PL_NEWLIB)
        self.setProg(0,0)

    def newBank(self, name):
        self.banks.append(SingleBank(name))
        if self.nolimit:
            self.updateVisible()
            self.libChange(PL_NEWBANK, name)

    def deleteBank(self, bankind=-1):
        if bankind==-1:
            bankind = self.current_bank
        if bankind<len(self.visible):
            del self.banks[self.visible[bankind][0]]
        self.updateVisible()
        self.libChange(PL_NEWLIB)

    def appendProg(self, midimsg):
        bi = self.len(banks)-1
        bank = self.banks[bi]
        prog = SingleProg(midimsg.getSingleDump())
        bank.progs.append(prog)
        if self.nolimit:
            self.appendVisible(bi)
            self.libChange(PL_NEWPROG, prog.name)

    def storeProg(self, prog, progind, bankind, name):
        prog.setName(name)
        if bankind>=len(self.visible):
            return
        bi,bv = self.visible[bankind]
        bank = self.banks[bi]
        if progind>=0 and progind<len(bv):
            bank.progs[bv[progind]] = prog
        else:
            bank.progs.append(prog)
            progind = self.appendVisible(bankind)
        self.libChange(PL_NEWPROG)
        self.setProg(progind, bankind)



def ctrlKey(ctrlid):
    return ctrlid[0]*128 + ctrlid[1]

def ctrlInvKey(key):
    return (key/128, key%128)


REQ_NONE    = 0
REQ_SINGLE  = 1
REQ_SINGLE_QUEUED = 2
REQ_BANK    = 3
REQ_ABORT   = 4


class ProgInterface(object):
    def __init__(self, gui):
        self.gui = gui
        self.midiint = MidiInterface(gui)
        self.current = SingleProg()
        self.has_changed = False
        self.proglib = ProgLibrary(self.progChange, self.libChange)
        self.listeners = {}
        self.prgchng_lst = []
        self.libchng_lst = []
        self.req = REQ_NONE
        self.alwaysrecv = False

        gui.setNotify(self.midiNotify)

    def addListener(self, ctrlid, func):
        key = ctrlKey(ctrlid)
        llist = self.listeners.get(key, [])
        llist.append(func)
        self.listeners[key] = llist

    def notify(self, ctrlid, val):
        key = ctrlKey(ctrlid)
        for f in self.listeners.get(key, []):
            f(val)

    def addPrgChngListener(self, func):
        self.prgchng_lst.append(func)

    def progChange(self, prog, changed=False, sendmidi=False):
        self.current = prog
        self.has_changed = changed
        for func in self.prgchng_lst:
            func()
        if sendmidi and self.midiint.isOpen():
            self.midiint.sendsingleedit(prog.dump)
    
    def progHasChanged(self):
        return self.has_changed

    def storeProg(self, prognr, banknr, name):
        self.proglib.storeProg(self.current.copy(), prognr, banknr, name)

    def addLibChngListener(self, func):
        self.libchng_lst.append(func)

    def libChange(self, newpart, appendName=None):
        for func in self.libchng_lst:
            func(newpart, appendName)

    def getCtrl(self, ctrlid):
        return self.current.getCtrl(ctrlid)

    def setCtrl(self, ctrlid, val):
        self.current.setCtrl(ctrlid, val)
        self.notify(ctrlid, val)
        if self.midiint.isOpen():
            self.midiint.writeCtrl(ctrlid, val)
        self.gui.setMidiMsg(makeCtrlInfoStr(ctrlid, val))
        if not self.has_changed:
            self.progChange(self.current, changed=True)

    def onController(self, ctrlid, value):
        self.current.setCtrl(ctrlid, value)
        self.notify(ctrlid, value)
        if not self.has_changed:
            self.progChange(self.current, changed=True)

    def connect(self, devname, filter):
        if not self.midiint.isOpen():
            self.req = REQ_NONE
            self.midiint.start(devname, filter)
            if self.alwaysrecv:
                self.readSingleVirus()
            else:
                self.midiint.sendsingleedit(self.current.dump)

    def disconnect(self):
        self.midiint.stop()

    def getAlwaysReceive(self):
        return self.alwaysrecv
    def setAlwaysReceive(self, recv):
        self.alwaysrecv = recv

    def readSingleVirus(self):
        if self.req==REQ_NONE:
            self.midiint.reqsingledump()
            self.req = REQ_SINGLE
        elif self.req==REQ_SINGLE:
            self.req = REQ_SINGLE_QUEUED

    def rcvSingleVirus(self, midimsg):
        if self.req in (REQ_NONE, REQ_SINGLE, REQ_SINGLE_QUEUED):
            self.progChange(SingleProg(midimsg.getSingleDump()))
            if self.req==REQ_SINGLE:
                self.req = REQ_NONE
            elif self.req==REQ_SINGLE_QUEUED:
                self.req = REQ_SINGLE
                self.midiint.reqsingledump()
        elif self.req==REQ_ABORT:
            self.req = REQ_NONE

    def readBankListVirus(self, reqlist):
        """reqlist = list of tuples (banknr, bankname)
           banknr = 1..4  RAM A - D
                    5...  ROM A - """
        self.req = REQ_BANK
        self.bankreqlist = reqlist
        self.reqNextBank(init=True)

    def reqNextBank(self, init=False):
        if not self.req==REQ_BANK:
            return
        if init:
            self.bankreqind = 0
        else:
            self.bankreqind += 1
        if self.bankreqind >= len(self.bankreqlist):
            self.req = REQ_NONE
            return
        (bank,name) = self.bankreqlist[self.bankreqind]
        self.midiint.reqbankdump(bank)
        self.proglib.newBank(name)

    def abortBankRead(self):
        self.req = REQ_ABORT
        self.midiint.reqsingledump()

    def midiNotify(self, midimsg):
        if midimsg.isController():
            self.onController(*midimsg.getCtrlData())
        elif midimsg.isSingleDump():
            self.rcvSingleVirus(midimsg)
        elif midimsg.isSingleChange():
            if self.alwaysrecv:
                self.readSingleVirus()
        elif midimsg.isBankDump():
            self.proglib.appendProg(midimsg)
            if midimsg.getProgNr()==127:
                self.reqNextBank()


##
##  interface end
##



def makeSysEx(msg):
    sysex = [0xF0, 0, 0x20, 0x33, 1, 0x10]
    sysex.extend(msg)
    sysex.append(0xF7)
    return sysex

def printcmd(cmd):
    for b in cmd:
        print "%02X " % b ,
    print



MIDI_VOID = 0
MIDI_NTOFF = 1
MIDI_NTON  = 2
MIDI_CTRL_A  = 3
MIDI_CHNPRES = 4
MIDI_PITCH = 5
MIDI_CTRL_B = 6
MIDI_CTRL_C = 7
MIDI_CTRL_6E = 8
MIDI_SINGLEDUMP = 9
MIDI_SINGLECHG = 10
MIDI_MULTICHG = 11

SYSEX_OFFSET = 6

class MidiMsg(object):
    def __init__(self, msg):
        self.msg = msg
        self.analyseType()

    def analyseType(self):
        self.type = MIDI_VOID
        self.issysex = False

        sb = self.msg[0] & 0xF0
        if sb==0x80:
            self.type = MIDI_NTOFF
        elif sb==0x90:
            self.type = MIDI_NTON
        elif sb==0xB0:
            self.type = MIDI_CTRL_A
        elif sb==0xD0:
            self.type = MIDI_CHNPRES
        elif sb==0xE0:
            self.type = MIDI_PITCH
        elif self.msg[0:5]==[0xF0,0,0x20,0x33,1]:
            self.issysex = True
            sb = self.msg[SYSEX_OFFSET]
            if sb==0x6E:
                self.type = MIDI_CTRL_6E
            elif sb==0x71:
                self.type = MIDI_CTRL_B
            elif sb==0x72:
                self.type = MIDI_CTRL_C
            elif sb==0x10:
                self.type = MIDI_SINGLEDUMP
            elif sb==0x73:
                if self.msg[SYSEX_OFFSET+1]==0x40:
                    self.type = MIDI_SINGLECHG
                elif self.msg[SYSEX_OFFSET+1]==0:
                    self.type = MIDI_MULTICHG

    def getRawStr(self):
        if self.issysex==True:
            rstr = 'sysex '
            start = SYSEX_OFFSET
        else:
            rstr = ''
            start = 0

        msg = self.msg
        stop = min(len(msg),start+8)
        for i in range(start,stop):
            rstr += '%02X ' % msg[i]
        if stop<len(msg):
            rstr += '...'
        return rstr

    def getInfoStr(self):
        if self.type==MIDI_SINGLEDUMP:
            bank = self.getBankNr()
            prog = self.getProgNr()
            if bank==0:
                if prog==0x40:
                    return 'rcv single prog'
                else:
                    return 'rcv multi part %d' % (prog)
            elif bank<=4:
                return 'rcv bank RAM %c, prog %d' % (ord('A')+bank-1,prog)
            else:
                return 'rcv bank ROM %c, prog %d' % (ord('A')+bank-5,prog)
        elif self.type==MIDI_CTRL_A:
            return makeCtrlInfoStr((CTRL_A,self.msg[1]), self.msg[2])
        elif self.type==MIDI_CTRL_B:
            return makeCtrlInfoStr((CTRL_B,self.msg[SYSEX_OFFSET+2]),
                                   self.msg[SYSEX_OFFSET+3])
        elif self.type==MIDI_CTRL_6E:
            return makeCtrlInfoStr((CTRL_6E,self.msg[SYSEX_OFFSET+2]),
                                   self.msg[SYSEX_OFFSET+3])
        else:
            return self.getRawStr()

    def isController(self):
        if self.type in (MIDI_CTRL_A,MIDI_CTRL_B,#MIDI_CTRL_C,
                         MIDI_CTRL_6E):
            return True
        else:
            return False

    def getCtrlData(self):
        if self.type==MIDI_CTRL_A:
            return ((CTRL_A, self.msg[1]), self.msg[2])
        elif self.type==MIDI_CTRL_6E:
            return ((CTRL_6E, self.msg[SYSEX_OFFSET+2]), 
                    self.msg[SYSEX_OFFSET+3])
        elif self.type==MIDI_CTRL_B:
            return ((CTRL_B, self.msg[SYSEX_OFFSET+2]), 
                    self.msg[SYSEX_OFFSET+3])
        elif self.type==MIDI_CTRL_C:
            return ((CTRL_C, self.msg[SYSEX_OFFSET+2]), 
                    self.msg[SYSEX_OFFSET+3])

    def getBankNr(self):
        return self.msg[SYSEX_OFFSET+1]
    def getProgNr(self):
        return self.msg[SYSEX_OFFSET+2]

    def isSingleDump(self):
        return self.type==MIDI_SINGLEDUMP \
            and self.getBankNr()==0 and self.getProgNr()==0x40

    def isBankDump(self):
        return self.type==MIDI_SINGLEDUMP \
            and self.getBankNr()>0

    def getSingleDump(self):
        return self.msg[SYSEX_OFFSET+3:-1]

    def isSingleChange(self):
        return self.type==MIDI_SINGLECHG


FILTER_NOTE = 1
FILTER_CHNPRESS = 2
FILTER_PITCH = 4
FILTER_MOD = 8

class MidiInterface(object):
    def __init__(self, gui):
        self.gui = gui
        # self.lock = thread.allocate_lock()
        self.threadid = 0

    def __del__(self):
        self.stop()

    def writeCtrl(self, ctrlid, value):
        page, number = ctrlid
        if page==CTRL_A:
            msg = [0xB0, number, value]
        else:
            if page==CTRL_B:
                msg = [0x71, 0x40, number, value]
            elif page==CTRL_6E:
                msg = [0x6E, 0x40, number, value]
            msg = makeSysEx(msg)

        #    printcmd(msg)
        pyrawmidi.write(msg)

    def start(self, devname="hw:1,0,1", filter=0):
        try:
            pyrawmidi.open(devname)
            pyrawmidi.setfilter(filter, 0)
            self.threadid = thread.start_new_thread(self.threadfunc, ())
        except (IOError, MemoryError):
            pyrawmidi.close()
            raise

    def stop(self):
        if self.threadid:
            self.threadid = 0
            self.terminated = False

            # next midi msg makes virus produce some midi msgs, 
            # causing threadfunc
            # to return from pyrawmidi.read() and terminate
            try:
                pyrawmidi.write([0xf0,0,0x20,0x33,0x01,0x10,0x73,0,0,0,0xf7])
            except IOError:
                pass

            # wait for thread to terminate
            for i in range(8):
                if self.terminated:
                    break
                time.sleep(.1)

        pyrawmidi.close()

    def threadfunc(self):
        while True:
            msg = pyrawmidi.read()
            if self.threadid!=thread.get_ident():
                break
            midimsg = MidiMsg(msg)
            self.gui.postEvent(midimsg)
        self.terminated = True

    def isOpen(self):
        return self.threadid!=0

    def reqsingledump(self):
#        self.dump = None
        msg = makeSysEx([0x30, 0, 0x40])
        pyrawmidi.write(msg)
#        while self.dump==None:
#            time.sleep(.1)
#        return self.dump[3:-1]

    # def rcvsingledump(self, msg):
    #     if msg[1]==0 and msg[2]==0x40:
    #         self.lock.acquire()
    #         if self.dump==None:
    #             self.dump = msg
    #         self.lock.release()

    def reqbankdump(self, bank):
        msg = makeSysEx([0x32,bank])
        pyrawmidi.write(msg)

    def sendsingleedit(self, dump):
        singledump = [0x10, 0, 0x40]
        singledump.extend(dump)
        pyrawmidi.write(makeSysEx(singledump))
        

def create():
    lib = ProgLibrary()
    bank1 = SingleBank('ram A')
    bank1.progs.append(SingleProg())
    bank1.progs.append(SingleProg())
    lib.banks.append(bank1)
    bank2 = SingleBank('ram A')
    bank2.progs.append(SingleProg())
    bank2.progs.append(SingleProg())
    bank2.progs.append(SingleProg())
    bank2.progs.append(SingleProg())
    lib.banks.append(bank2)

    lib.dumpToFile('proglib.lib')

def read():
    lib = ProgLibrary()
    lib.loadFromFile('proglib.lib')

    print lib.version
    for b in lib.banks:
        print b.name, len(b.progs)
        for p in b.progs:
            print ' >', p.name, len(p.dump)
