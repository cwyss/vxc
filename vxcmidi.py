
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



class ChunkError(Exception):
    def __init__(self):
        Exception.__init__(self)

def writeChunk(file, name, data):
    file.write(name[0:4])
    length = len(data)%2**16
    file.write(chr(length/256)+chr(length%256))
    file.write(data[0:length])

def readChunk(file):
    buf = file.read(6)
    if buf=='':
        raise EOFError
    elif len(buf)<6:
        raise ChunkError
    name = buf[0:4]
    length = ord(buf[4])*256 + ord(buf[5])
    data = file.read(length)
    if len(data)<length:
        raise ChunkError
    return (name,data)

def chunkMakeStr(string):
    strlen = len(string) & 0xFF
    return chr(strlen)+string[:strlen]

def chunkGetStr(data):
    strlen = ord(data[0])
    return data[1:strlen+1]



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
        if dump!=None and len(dump)==DUMP_LENGTH:
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

    def makeChunk(self):
        data = ''
        for d in self.dump:
            data += chr(d)
        return data

    @classmethod
    def fromChunk(cls, data):
        dump = [ord(c) for c in data]
        return SingleProg(dump)

    def copy(self):
        return SingleProg(list(self.dump))


class SingleBank(object):
    def __init__(self, name):
        self.name = name
        self.progs = []

    def makeChunk(self):
        return chunkMakeStr(self.name)

    @classmethod
    def fromChunk(cls, data):
        return SingleBank(chunkGetStr(data))


PROGLIB_VERSION_1  = 1

PL_LIBCHNG  = 0
PL_NEWBANK  = 1
PL_BANKCHNG = 2

PL_DUMPCONT = 0
PL_DUMPCHK  = 1
PL_DUMPADD  = 2

LIMIT_AND = 0
LIMIT_OR = 1
LIMITBOOL_NAMES = {LIMIT_AND: "and", LIMIT_OR: "or"}

LIMIT_EQ = 0
LIMIT_GE = 1
LIMIT_LE = 2
LIMITREL_NAMES = {LIMIT_EQ: "=", LIMIT_GE: ">=", LIMIT_LE: "<="}

class ProgLibError(Exception):
    def __init__(self, filename, 
                 description="Not a valid program library"):
        Exception.__init__(self)
        self.filename = filename
        self.description = description

    def __str__(self):
        return  self.description+': '+self.filename


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
        self.visProgCnt = 0

    def setLimitCrit(self, namepat, ctrlcond):
        """ ctrlcond = list of lists
          [boolop, ctrlid, relatop, val] 
          """
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
            self.ctrlcond = ctrlcond
            self.nolimit = False
        else:
            self.ctrlcond = []
        self.updateVisible()
        if self.current_bank>=len(self.visible):
            self.current_bank = 0
        self.libChange(PL_LIBCHNG)

    def matchCond(self, prog, cc):
        val = prog.getCtrl(cc[1])
        relop = cc[2]
        if relop==LIMIT_EQ:
            return val==cc[3]
        elif relop==LIMIT_GE:
            return val>=cc[3]
        elif relop==LIMIT_LE:
            return val<=cc[3]

    def matchProg(self, prog):
        b1 = True
        b2 = True
        for (i,cc) in enumerate(self.ctrlcond):
            bb = self.matchCond(prog, cc)
            boolop = cc[0]
            if i==0:
                b2 = bb
            elif boolop==LIMIT_OR:
                b2 = b2 or bb
            elif boolop==LIMIT_AND:
                b1 = b1 and b2
                b2 = bb
        b1 = b1 and b2
        return b1 and bool(re.match(self.namepat, prog.name.lower()))

    def updateVisible(self):
        currprog = self.getProg(self.current_prog, self.current_bank)
        self.visible = []
        self.current_prog = 0
        self.current_bank = 0
        self.visProgCnt = 0
        for bi,bank in enumerate(self.banks):
            bv = []
            for pi,prog in enumerate(bank.progs):
                if self.nolimit or self.matchProg(prog):
                    bv.append(pi)
                    if currprog==prog:
                        self.current_bank = len(self.visible)
                        self.current_prog = len(bv)-1
            if self.nolimit or len(bv)>0:
                self.visible.append((bi,bv))
            self.visProgCnt += len(bv)

    def appendVisible(self, bankind):
        bi,bv = self.visible[bankind]
        proglist = self.banks[bi].progs
        pi = len(proglist)-1
        # if self.nolimit or re.match(self.namepat, proglist[pi].name.lower()):
        bv.append(pi)
        self.visProgCnt += 1
        return len(bv)-1

    def getCurrentBank(self):
        return self.current_bank
    def getCurrentProg(self):
        return self.current_prog

    def getVisibleInfo(self):
        return (self.visProgCnt, len(self.visible), self.nolimit)

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
            contents.append((bank.progs[pi].name, pi))
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
        writeChunk(f, 'PLIB', chr(self.version))
        for b in self.banks:
            writeChunk(f, 'BANK', b.makeChunk())
            for p in b.progs:
                writeChunk(f, 'PROG', p.makeChunk())
        f.close()

    def loadFromFile(self, filename):
        newbanks = []
        bank = None
        try:
            f = open(filename, 'r')
            (chnk,data) = readChunk(f)
            if chnk!='PLIB' or len(data)==0:
                raise ProgLibError(filename)
            # version = ord(data[0])
            while True:
                try:
                    (chnk,data) = readChunk(f)
                except EOFError:
                    break
                if chnk=='BANK':
                    bank = SingleBank.fromChunk(data)
                    newbanks.append(bank)
                elif chnk=='PROG':
                    if bank:
                        bank.progs.append(SingleProg.fromChunk(data))
                    else:
                        raise ProgLibError(filename)
            f.close()
        except (EOFError, ChunkError):
            raise ProgLibError(filename)
        self.banks = newbanks
        self.updateVisible()
        self.libChange(PL_LIBCHNG)
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
        self.libChange(PL_LIBCHNG)

    def bankDumpInit(self, name, banknr):
        self.newBank(name)
        self.bankdumpnr = banknr
        self.bankdumpbi = len(self.banks)-1
        self.bankdumpmiss = []

    def bankDumpAddProg(self, midimsg):
        bi = self.bankdumpbi
        bank = self.banks[bi]
        if self.bankdumpnr!=midimsg.getBankNr():
            return PL_DUMPCONT
        prognr = midimsg.getProgNr()
        prog = SingleProg(midimsg.getSingleDump())
        if prognr<len(bank.progs):
            bank.progs[prognr] = prog
            if self.nolimit:
                self.libChange(PL_BANKCHNG)
            result = PL_DUMPADD
        else:
            while len(bank.progs)<prognr:
                self.bankdumpmiss.append((self.bankdumpnr,len(bank.progs)))
                bank.progs.append(SingleProg())
                if self.nolimit:
                    self.appendVisible(bi)
                    self.libChange(PL_BANKCHNG, bank.progs[-1].name)
            bank.progs.append(prog)
            if self.nolimit:
                self.appendVisible(bi)
                self.libChange(PL_BANKCHNG, prog.name)
            if len(bank.progs)==128:
                result = PL_DUMPCHK
            else:
                result = PL_DUMPCONT
        return result

    def bankDumpGetMissing(self, targetlen=128):
        bi = self.bankdumpbi
        bank = self.banks[bi]
        while len(bank.progs)<targetlen:
            self.bankdumpmiss.append((self.bankdumpnr,len(bank.progs)))
            bank.progs.append(SingleProg())
            if self.nolimit:
                self.appendVisible(bi)
                self.libChange(PL_BANKCHNG, bank.progs[-1].name)
        return self.bankdumpmiss

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
        self.libChange(PL_BANKCHNG)
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
        self.is_modified = False
        self.proglib = ProgLibrary(self.progChange, self.libChange)
        self.listeners = {}
        self.prgchng_lst = []
        self.libchng_lst = []
        self.req = REQ_NONE
        self.bankreqlist = None
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

    def progChange(self, prog, modified=False, sendmidi=False):
        self.current = prog
        self.is_modified = modified
        for func in self.prgchng_lst:
            func()
        if sendmidi and self.midiint.isOpen():
            self.midiint.sendsingleedit(prog.dump)
    
    def progModified(self):
        return self.is_modified

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
        if not self.is_modified:
            self.progChange(self.current, modified=True)

    def onController(self, ctrlid, value):
        self.current.setCtrl(ctrlid, value)
        self.notify(ctrlid, value)
        if not self.is_modified:
            self.progChange(self.current, modified=True)

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
            if midimsg.validDump():
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
        self.rereadlist = []
        self.reqNextBank()

    def reqNextBank(self):
        if self.req!=REQ_BANK:
            return
        if len(self.rereadlist)>0:
            (banknr,prognr) = self.rereadlist.pop(0)
            self.midiint.reqsingledump(banknr, prognr)
        elif len(self.bankreqlist)>0:
            (bank,name) = self.bankreqlist.pop(0)
            self.midiint.reqbankdump(bank)
            self.proglib.bankDumpInit(name, bank)
        else:
            self.req = REQ_NONE

    def rcvBankDump(self, midimsg):
        if midimsg.validDump():
            result = self.proglib.bankDumpAddProg(midimsg)
            if result==PL_DUMPCHK:
                self.rereadlist = self.proglib.bankDumpGetMissing()
                self.reqNextBank()
            elif result==PL_DUMPADD:
                self.reqNextBank()

    def stopBankRead(self):
        self.req = REQ_ABORT
        self.midiint.reqsingledump()

    def resumeBankRead(self):
        if self.bankreqlist!=None:
            self.req = REQ_BANK
            self.rereadlist = self.proglib.bankDumpGetMissing()
            self.reqNextBank()

    def midiNotify(self, midimsg):
        if midimsg.isController():
            self.onController(*midimsg.getCtrlData())
        elif midimsg.isSingleDump():
            self.rcvSingleVirus(midimsg)
        elif midimsg.isSingleChange():
            if self.alwaysrecv:
                self.readSingleVirus()
        elif midimsg.isBankDump():
            self.rcvBankDump(midimsg)


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

    def validDump(self):
        return len(self.msg)==SYSEX_OFFSET+4+DUMP_LENGTH

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

    def reqsingledump(self, banknr=0, prognr=0x40):
#        self.dump = None
        msg = makeSysEx([0x30, banknr, prognr])
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
