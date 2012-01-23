
import sys, time, thread, pyrawmidi, pickle


CTRL_VOID = 0
CTRL_PAGE_A = 1
CTRL_PAGE_B = 2
CTRL_PAGE_C = 3
CTRL_SYSEX_6E = 4

CtrlTypeName = {CTRL_VOID: 'void',
                CTRL_PAGE_A: 'page A',
                CTRL_PAGE_B: 'page B',
                CTRL_PAGE_C: 'page C',
                CTRL_SYSEX_6E: 'sysex 6E'}


def printcmd(cmd):
    for b in cmd:
        print "%02X " % b ,
    print

def findindeces(x, val, indbase=None):
    i = -1
    ind = []

    try:
        while True:
            i = x.index(val, i+1)
            if indbase==None:
                ind.append(i)
            elif i in indbase:
                ind.append(i)
    except ValueError:
        pass

    return ind


class CtrlDef(object):
    def __init__(self):
        self.name = ""
        self.type = CTRL_VOID
        self.nr = 0
        self.dumpind = -1
        self.range = (0,0)
        self.transl = {}

    def __str__(self):
        return "%-20s  %s  dump %d" % (self.name, self.getdescription(),
                                      self.dumpind)

    def getdescription(self):
        return "%8s %3d %-10s" % (CtrlTypeName[self.type], self.nr,
                                 self.range)

    def updaterange(self, val):
        if val<self.range[0]:
            self.range = (val, self.range[1])
        elif val>self.range[1]:
            self.range = (self.range[0], val)

    def makemsg(self, val):
        if self.type==CTRL_PAGE_A:
            return [0xB0, self.nr, val]
        elif self.type==CTRL_PAGE_B:
            return [0xF0, 0, 0x20, 0x33, 0x01, 0x10,
                    0x71, 0x40, self.nr, val, 0xF7]
        elif self.type==CTRL_SYSEX_6E:
            return [0xF0, 0, 0x20, 0x33, 0x01, 0x10,
                    0x6E, 0x40, self.nr, val, 0xF7]


class MidiInThread(object):
    def __init__(self):
        self.ctrldef = CtrlDef()
        self.dump = None

        self.lock = thread.allocate_lock()
        self.run = True
        self.running = False
        thread.start_new_thread(self.threadfunc, ())

    def updatectrlinfo(self, ctype, nr, val):
        match = False
        self.lock.acquire()

        if self.ctrldef.type==CTRL_VOID:
            self.ctrldef.type = ctype
            self.ctrldef.nr = nr
            self.ctrldef.range = (val,val)
            match = True
        elif self.ctrldef.type==ctype and self.ctrldef.nr==nr:
            self.ctrldef.updaterange(val)
            match = True

        if match:
            print self.ctrldef.getdescription(), val

        self.lock.release()
        return match

    def replace_ctrldef(self, newcdef):
        self.lock.acquire()
        cdef = self.ctrldef
        self.ctrldef = newcdef
        self.lock.release()
        return cdef

    def finddumpind(self):
        val = self.ctrldef.range[0]
        pos = None
        for i in range(4):
            pyrawmidi.write(self.ctrldef.makemsg(val))
            self.reqsingledump()
            while self.dump==None:
                time.sleep(.1)
            pos = findindeces(self.dump, val, pos)
            print "%d: %s" % (i,pos)
            if len(pos)==1:
                print "found dump index: ", pos[0]
                self.ctrldef.dumpind = pos[0]
                return
            elif len(pos)==0:
                break
            val += 1
            if val>self.ctrldef.range[1]:
                break
        print "dump index not found"

    def reqsingledump(self):
        self.dump = None
        pyrawmidi.write([0xF0, 0, 0x20, 0x33, 0x01, 0x10,
                         0x30, 0, 0x40, 0xF7])

    def rcvsingledump(self, msg):
        if msg[1]==0 and msg[2]==0x40:
            self.lock.acquire()
            if self.dump==None:
                self.dump = msg[3:]
            self.lock.release()
        #        print "%02X %02X %02X  %d" % (msg[0],msg[1],msg[2],len(msg))
            return True
        else:
            return False

    def analyse(self, msg):
        sb = msg[0] & 0xF0
        if sb==0xB0:
            return self.updatectrlinfo(CTRL_PAGE_A, msg[1], msg[2])
        elif msg[0]==0xF0 and msg[1]==0 and msg[2]==0x20 and msg[3]==0x33 \
                and msg[4]==1:
            if msg[6]==0x6E:
                return self.updatectrlinfo(CTRL_SYSEX_6E, msg[8], msg[9])
            elif msg[6]==0x71:
                return self.updatectrlinfo(CTRL_PAGE_B, msg[8], msg[9])
            elif msg[6]==0x72:
                return self.updatectrlinfo(CTRL_PAGE_C, msg[8], msg[9])
            elif msg[6]==0x10:
                return self.rcvsingledump(msg[6:])
            else:
                return False
        else:
            return False

    def threadfunc(self):
        self.running = True
        while True:
            msg = pyrawmidi.read()
            if not self.run:
                break
            if not self.analyse(msg):
                printcmd(msg)
        self.running = False

    def stop(self):
        self.run = False

        # next midi msg makes virus produce some midi msgs, causing threadfunc
        # to return from pyrawmidi.read() and terminate
        pyrawmidi.write([0xf0,0,0x20,0x33,0x01,0x10,0x73,0,0,0,0xf7])

        # wait for thread to terminate
        while self.running:
            time.sleep(.1)




class CtrlMap(object):
    def __init__(self):
        self.map = []

    def printmap(self):
        for i in range(len(self.map)):
            print "%3d:  %s" % (i, self.map[i])

    def save(self, filename):
        f = open(filename, "wb")
        pickle.dump(self.map, f)
        f.close()

    def load(self, filename):
        f = open(filename, "rb")
        self.map = pickle.load(f)
        f.close()

    def openmidi(self):
        pyrawmidi.open("hw:1,0,1")
        pyrawmidi.setfilter(0,0)
        return MidiInThread()

    def closemidi(self, midithread):
        sys.stdout.write("terminating midi thread...")
        sys.stdout.flush()
        midithread.stop()
        sys.stdout.write("\n")
        pyrawmidi.close()

    def learn(self):
        midithread = self.openmidi()

        while True:
            c = raw_input()
            if c=='q':
                break
            elif c.startswith('n'):
                midithread.ctrldef.name = c[1:].lstrip()
            elif c.startswith('s'):
                cdef = midithread.replace_ctrldef(CtrlDef())
                try:
                    i = int(c[1:])
                    self.map[i] = cdef
                except (ValueError, IndexError):
                    self.map.append(cdef)
                    i = len(self.map)-1
                print "%3d:  %s" % (i, cdef)
            elif c=='l':
                self.printmap()
            elif c.startswith('e'):
                try:
                    i = int(c[1:])
                    midithread.replace_ctrldef(self.map[i])
                except (ValueError, IndexError):
                    print "invalid index"
                print midithread.ctrldef
            elif c=='c':
                midithread.replace_ctrldef(CtrlDef())
            elif c.startswith('del'):
                try:
                    i = int(c[3:])
                    self.map.pop(i)
                except (ValueError, IndexError):
                    print 'invalid index'
            elif c.startswith('f'):
                try:
                    i = int(c[1:])
                    midithread.replace_ctrldef(self.map[i])
                except (ValueError, IndexError):
                    print "invalid index"
                    continue
                midithread.finddumpind()
            else:
                print midithread.ctrldef

        self.closemidi(midithread)


def loadmap(filename):
    ctrlmap = CtrlMap()
    ctrlmap.load(filename)
    return ctrlmap

def runtest():
    ctrlmap = CtrlMap()
    ctrlmap.learn()

