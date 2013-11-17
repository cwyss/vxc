
import pickle


class CtrlMapping(object):
    """Defines a specific translation of the raw midi controller 
       values (0..127), e.g. to percent-values or labels"""

    @classmethod
    def deserialise(cls, serial):
        pass

class CtrlDataType(object):
    """Defines a specific type of controller in terms
       of its possible controller values and their meaning/mapping"""

    def __init__(self, name, range=(0,127)):
        self.name = name
        self.range = range
        self.mapping = None

    def serialise(self):
        return [self.name, self.range]

    @classmethod
    def deserialise(cls, serial, mapdict):
        return CtrlDataType(serial[0], serial[1])

    def debugout(self):
        print '  '+self.name+': ', self.range


class CtrlDef(object):
    """Defines a Virus controller with midi address and datatype

    address = (PageNumber, CtrlNumber)"""

    def __init__(self, familyname, ctrlname, address=(0,0),
                 datatype=None):
        self.familyname = familyname
        self.ctrlname = ctrlname
        self.address = address
        self.datatype = datatype

    @property
    def name(self):
        return self.familyname+'.'+self.ctrlname

    @property
    def dtname(self):
        if self.datatype:
            return self.datatype.name
        else:
            return ''

    def serialise(self):
        return [self.familyname, self.ctrlname, self.address,
                self.dtname]

    @classmethod
    def deserialise(cls, serial, dtdict):
        if len(serial[3])>0:
            datatype = dtdict[serial[3]]
        else:
            datatype = None
        return CtrlDef(serial[0], serial[1], serial[2], datatype)

    def debugout(self):
        print '  ' + self.name + ': ', self.address, self.dtname


class CtrlInstance(object):
    """Defines a controller instance in vxc which tracks a certain
       Virus controller (CtrlDef) on a certain multi part/midi channel"""

    def __init__(self, name, ctrldef, part):
        self.name = name
        self.ctrldef = ctrldef
        self.part = part

    @property
    def cdefname(self):
        return self.ctrldef.name

    def serialise(self):
        return [self.name, self.cdefname, self.part]

    @classmethod
    def deserialise(cls, serial, cdefdict):
        return CtrlInstance(serial[0], cdefdict[serial[1]], serial[2])


class CtrlBlock(object):
    """Groups several CtrlInstance objects together"""

    def __init__(self, name):
        self.name = name
        self.ctrls = []

    def serialise(self):
        cs = [c.serialise() for c in self.ctrls]
        return [self.name, cs]

    @classmethod
    def deserialise(cls, serial, cdefdict):
        blk = CtrlBlock(serial[0])
        for cserial in serial[1]:
            blk.ctrls.append(CtrlInstance.deserialise(cserial, cdefdict))
        return blk


class CtrlPage(object):
    """Groups several CtrlBlock objects together"""

    def __init__(self, name):
        self.name = name
        self.blocks = []

    def serialise(self):
        bs = [b.serialise() for b in self.blocks]
        return [self.name, bs]

    @classmethod
    def deserialise(cls, serial, cdefdict):
        page = CtrlPage(serial[0])
        for bserial in serial[1]:
            page.blocks.append(CtrlBlock.deserialise(bserial, cdefdict))
        return page


class ControllerDefs(object):
    """A complete set of controller definitions"""
    def __init__(self):
        self.mappings = {}
        self.datatypes = {}
        self.ctrldefs = {}
        self.pages = []

    def addctrldef(self, cdef):
        self.ctrldefs[cdef.name] = cdef
    def adddatatype(self, dt):
        self.datatypes[dt.name] = dt
        
    def save(self, filename):
        mserial = [m.serialise() for m  in self.mappings.itervalues()]
        dserial = [d.serialise() for d  in self.datatypes.itervalues()]
        cserial = [c.serialise() for c  in self.ctrldefs.itervalues()]
        pserial = [p.serialise() for p  in self.pages]
        f = open(filename, 'w')
        pickle.dump([mserial, dserial, cserial, pserial], f)

    @classmethod
    def load(cls, filename):
        f = open(filename, 'r')
        serial = pickle.load(f)
        defs = ControllerDefs()

        for s in serial[0]:
            m = CtrlMapping.deserialise(s)
            defs.mappings[m.name] = m
        for s in serial[1]:
            d = CtrlDataType.deserialise(s, defs.mappings)
            defs.datatypes[d.name] = d
        for s in serial[2]:
            c = CtrlDef.deserialise(s, defs.datatypes)
            defs.ctrldefs[c.name] = c
        for s in serial[3]:
            defs.pages.append(CtrlPage.deserialise(s, defs.ctrldefs))
            
        return defs

    def debugout(self):
        print "mappings: ", self.mappings.keys()
        print "datatypes: "
        for d in self.datatypes.itervalues():
            d.debugout()
        print "ctrldefs: "
        for c in self.ctrldefs.itervalues():
            c.debugout()
        for p in self.pages:
            p.debugout()



class CtrlGUI(object):
    """wxPython realisation of CtrlInstance"""

    def __init__(self):
        self.ctrlinstance = None

class BlockGUI(object):
    """wxPython realisation of CtrlBlock"""
    pass

class PageGUI(object):
    """wxPython realisation of CtrlPage"""
    pass
