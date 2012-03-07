#!/usr/bin/env python

import vxcmidi, vxcgui, pickle

from vxcmidi import CTRL_A,CTRL_B,CTRL_C,CTRL_6E


# controller widget types:

CT_STD = 0        # valinfo unused
CT_LIST = 1       # valinfo = dictionary ctrl_value -> value_name
CT_SHAPE = 2      # valinfo = {0:label0, ..., 4:label4}
CT_PREFIX = 3     # valinfo[valmin] is prefix for values in valrange
                  # valinfo[0]..[valmin-1] are taken as is
CT_SIGN = 4       # value 64 -> 0
CT_SIGNPERCENT = 5
CT_SIGNLABEL = 6  # valinfo[0]='label VALUE' yields label at VALUE
CT_PERCENT = 7    # valinfo[0]=minpercent, valinfo[1]=maxpercent
CT_INTERPOL = 8   # valinfo[i]='fltval VALUE'
CT_CHECKBOX = 9
CT_NEGATIVE = 10
CT_SEPARATOR = 11

class CtrlDef(object):
    def __init__(self, name='', ctype=CT_STD, valrange=(0,127), 
                 cid=(CTRL_A,17), modes=[], valinfo={}):
        """ctrltype,      controller widget type, see below
        ctrlname,
        valrange,      (valmin, valmax)
        ctrlid,        (ctrlpage, ctrlnumber)
        modes,         list of modes where this controller is active
        valinfo        for value translation"""
        self.name = name
        self.ctype = ctype
        self.valrange = valrange
        self.cid = cid
        self.modes = modes
        self.valinfo = valinfo

    def copy(self):
        return CtrlDef(self.name, self.ctype, self.valrange, self.cid,
                       self.modes, self.valinfo.copy())

    def getModeStr(self):
        str = ''
        if len(self.modes)>0:
            str = '%d' % self.modes[0]
        for m in self.modes[1:]:
            str += ',%d' % m
        return str

    def setModeStr(self, modestr):
        self.modes = []
        for m in modestr.split(','):
            try:
                self.modes.append(int(m))
            except ValueError:
                pass

    def setRange(self, min=-1, max=-1):
        if min==-1:
            min = self.valrange[0]
        if max==-1:
            max = self.valrange[1]
        self.valrange = (min,max)

    def setcid(self, page=-1, number=-1):
        if page==-1:
            page = self.cid[0]
        if number==-1:
            number = self.cid[1]
        self.cid = (page, number)

CDEF_TYPE = 1
CDEF_NAME = 0
CDEF_RANGE = 2
CDEF_ID = 3
CDEF_MODES = 4
CDEF_INFO = 5


# mode types

MODE_NONE = 0     # no mode controller
MODE_STD = 1      # mode range is range of mode controller
MODE_OPENEND = 2  # modes from 0 to valmin, values from valmin to valmax
                  # yields single mode valmin

class BlockDef(object):
    def __init__(self, name='', modetype=MODE_NONE, cid=(CTRL_A,17), 
                 mrange=(0,0), info=None):
        """mrange         tuple (firstmode, lastmode)
        """
        self.name = name
        self.modetype = modetype
        self.cid = cid
        self.valrange = mrange
        self.info = info
        self.ctrldefs = []

    def copy(self):
        return BlockDef(self.name, self.modetype, self.cid, 
                        self.valrange, self.info)

    def setRange(self, min=-1, max=-1):
        if min==-1:
            min = self.valrange[0]
        if max==-1:
            max = self.valrange[1]
        self.valrange = (min,max)

    def setcid(self, page=-1, number=-1):
        if page==-1:
            page = self.cid[0]
        if number==-1:
            number = self.cid[1]
        self.cid = (page, number)

BDEF_NAME = 0
BDEF_MODE = 1
BDEF_CTRL = 2

MDEF_TYPE = 0
MDEF_ID = 1
MDEF_RANGE = 2
MDEF_INFO = 3


class PageDef(object):
    def __init__(self, name):
        self.name = name
        self.blocks = []

    def copy(self):
        return PageDef(self.name)

class CtrlPages(object):
    def __init__(self):
        self.pages = []

    def init2(self):
        page = PageDef('Osc')
        page.blocks.append(makeOscBlock())
        self.pages.append(page)

    def loadFromFile(self, filename):
        f = open(filename, "r")
        self.pages = pickle.load(f)

    def saveToFile(self, filename):
        f = open(filename, "w")
        pickle.dump(self.pages, f)


OSC1_DEF = (
    'Osc 1',
    (MODE_STD, (CTRL_6E, 30), (0,7)),
    (('Mode', CT_STD, (0,7), (CTRL_6E, 30), [0,1,2,3,4,5,6,7]),
     ('Shape', CT_STD, (0,127), (CTRL_A, 17), [0]),
     ('Density', CT_STD, (0,127), (CTRL_A, 17), [1]),
     ('Index', CT_STD, (0,127), (CTRL_A, 17), [2,3,4,5,6,7]),
     ('Wave Sel', CT_STD, (0,63), (CTRL_A, 19), [0]),
     ('WaveTable', CT_STD, (0,99), (CTRL_A, 19), [2,3,4,5,6,7]),
     ('Pulse Width', CT_STD, (0,127), (CTRL_A, 18), [0,3]),
     ('Local Detune', CT_STD, (0,127), (CTRL_A, 18), [1]),
     )
)

def makeOscBlock():
    block = BlockDef(OSC1_DEF[0], OSC1_DEF[1][0], OSC1_DEF[1][1], 
                     OSC1_DEF[1][2])
    for cdef in OSC1_DEF[2]:
        block.ctrldefs.append(CtrlDef(*cdef))
    return block

# class CtrlBlock(object):
#     def __init__(self, guibox, interface, blockdef):
#         self.guibox = guibox
#         self.interface = interface
#         self.name = blockdef[BDEF_NAME]

#         self.initModeCtrl(blockdef[BDEF_MODE])

#         self.controllers = []
#         for cdef in blockdef[BDEF_CTRL]:
#             self.buildCtrl(cdef)
#         guibox.Fit()

#     def initModeCtrl(self, modedef):
#         self.modedef = modedef
#         if modedef[MDEF_TYPE]==MODE_STD:
#             self.mode = self.interface.getCtrl(modedef[MDEF_ID])
#             self.interface.addListener(modedef[MDEF_ID], self.onMode)
#         else:
#             self.mode = 0

#     def buildCtrl(self, cdef):
#         notify = lambda val: self.onGUI(cdef[CDEF_ID], val)
#         ctrl = vxcgui.StdCtrlGUI(self.guibox, cdef[CDEF_NAME],
#                                  cdef[CDEF_RANGE], notify)
#         self.interface.addListener(cdef[CDEF_ID], ctrl.setVal)
#         centry = (cdef, ctrl)
#         self.controllers.append(centry)
#         self.updateCtrl(centry)

#     def updateCtrl(self, centry):
#         cdef,ctrl = centry
#         if self.mode in cdef[CDEF_MODES]:
#             ctrl.setVal(self.interface.getCtrl(cdef[CDEF_ID]))
#             ctrl.Show()
#             self.guibox.add(ctrl)
#         else:
#             ctrl.Hide()

#     def updateActive(self):
#         self.guibox.clear()
#         for centry in self.controllers:
#             self.updateCtrl(centry)
#         self.guibox.Fit()
# #        self.guibox.Layout()

#     def onGUI(self, ctrlid, val):
#         self.interface.setCtrl(ctrlid, val)

#     def onMode(self, val):
#         self.mode = val
#         self.updateActive()




