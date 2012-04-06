#!/usr/bin/env python

import vxcmidi, wx, pickle, sys



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
CT_PREFIXLIST = 12   # valinfo like for CT_PREFIX
CT_LABEL = 13        # unsigned CT_SIGNLABEL
CT_PERCENTLABEL = 14 # valinfo[0]='label VALUE'
CT_KEY = 15

class CtrlDef(object):
    def __init__(self, name='', ctype=CT_STD, valrange=(0,127), 
                 cid=(vxcmidi.CTRL_A,17), modes=[], valinfo={}):
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

    def getValInfo(self, ind):
        return self.valinfo.get(ind, '')


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
MODE_EXCEPT = 3   # like STD, but valinfo[0]='ctrlpage ctrlnum xmin xmax' 
                  # specifies modes valmax+1,..,valmax+1+xmax-xmin that 
                  # take precedence
                  # ctrlpage in ['A','B','C','6E','6F']
MODE_MUTE = 4     # additional mute buttons, no mode controller

MODE_EXCEPT_TRANS = {'A': vxcmidi.CTRL_A, 'B': vxcmidi.CTRL_B, 
                     'C': vxcmidi.CTRL_C,
                     '6E': vxcmidi.CTRL_6E, '6F': vxcmidi.CTRL_6F}

class BlockDef(object):
    def __init__(self, name='', modetype=MODE_NONE, cid=(vxcmidi.CTRL_A,17), 
                 mrange=(0,0), valinfo={}):
        """mrange         tuple (firstmode, lastmode)
        """
        self.name = name
        self.modetype = modetype
        self.cid = cid
        self.valrange = mrange
        self.valinfo = valinfo
        self.ctrldefs = []

    def copy(self):
        return BlockDef(self.name, self.modetype, self.cid, 
                        self.valrange, self.valinfo.copy())

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

    def getNumModes(self):
        if self.modetype==MODE_STD:
            return self.valrange[1]+1
        elif self.modetype==MODE_OPENEND:
            return self.valrange[0]+1
        elif self.modetype==MODE_EXCEPT:
            exmode = self.getExceptMode()
            return self.valrange[1]+2+exmode[2]-exmode[1]
        else:
            return 1

    def getValInfo(self, ind):
        return self.valinfo.get(ind, '')

    def getExceptMode(self):
        try:
            page,num,xmin,xmax = self.valinfo[0].split()
            cid = (MODE_EXCEPT_TRANS[page], int(num))
            xmin = int(xmin)
            xmax = int(xmax)
        except (KeyError, ValueError):
            cid = (vxcmidi.CTRL_6E, 30)
            xmin = 1
            xmax = 1
        return (cid, xmin, xmax)


BDEF_NAME = 0
BDEF_MODE = 1
BDEF_CTRL = 2

MDEF_TYPE = 0
MDEF_ID = 1
MDEF_RANGE = 2
MDEF_INFO = 3


class PageDef(object):
    def __init__(self, name, cols=0, collen={}):
        """
        cols        number of columns with fixed number of blocks
        collen      for each such column: number of blocks
        """
        self.name = name
        self.cols = cols
        self.collength = collen
        self.blocks = []

    def copy(self):
        return PageDef(self.name, self.cols, self.collength.copy())

    def getValInfo(self, col):
        return str(self.collength.get(col, 0))

    def setColLengthStr(self, col, lenstr):
        try:
            self.collength[col] = int(lenstr)
        except ValueError:
            self.collength[col] = 0


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
    (MODE_STD, (vxcmidi.CTRL_6E, 30), (0,7)),
    (('Mode', CT_STD, (0,7), (vxcmidi.CTRL_6E, 30), [0,1,2,3,4,5,6,7]),
     ('Shape', CT_STD, (0,127), (vxcmidi.CTRL_A, 17), [0]),
     ('Density', CT_STD, (0,127), (vxcmidi.CTRL_A, 17), [1]),
     ('Index', CT_STD, (0,127), (vxcmidi.CTRL_A, 17), [2,3,4,5,6,7]),
     ('Wave Sel', CT_STD, (0,63), (vxcmidi.CTRL_A, 19), [0]),
     ('WaveTable', CT_STD, (0,99), (vxcmidi.CTRL_A, 19), [2,3,4,5,6,7]),
     ('Pulse Width', CT_STD, (0,127), (vxcmidi.CTRL_A, 18), [0,3]),
     ('Local Detune', CT_STD, (0,127), (vxcmidi.CTRL_A, 18), [1]),
     )
)

def makeOscBlock():
    block = BlockDef(OSC1_DEF[0], OSC1_DEF[1][0], OSC1_DEF[1][1], 
                     OSC1_DEF[1][2])
    for cdef in OSC1_DEF[2]:
        block.ctrldefs.append(CtrlDef(*cdef))
    return block



class CtrlGUI(wx.Panel):
    def __init__(self, parent, interface, cdef):
        wx.Panel.__init__(self, parent)
        self.interface = interface
        self.cdef = cdef
        interface.addListener(cdef.cid, self.setVal)

        self.label = wx.StaticText(parent, label=cdef.name)

    def setVal(self, val):
        pass

    def onGUI(self, val):
        try:
            self.interface.setCtrl(self.cdef.cid, val)
        except StandardError as error:
            showError(str(error))

    def Show(self, show=True):
        wx.Panel.Show(self, show)
        self.label.Show(show)

    def Hide(self):
        wx.Panel.Hide(self)
        self.label.Hide()


class StdCtrlGUI(CtrlGUI):
    def __init__(self, parent, interface, cdef):
        CtrlGUI.__init__(self, parent, interface, cdef)

        self.slider = wx.Slider(parent=self, minValue=cdef.valrange[0],
                                maxValue=cdef.valrange[1],
                                size=(60,-1),
                                style=wx.SL_HORIZONTAL)
        self.slider.SetPageSize((cdef.valrange[1]-cdef.valrange[0]+1)/16)
        self.valtext \
            = wx.StaticText(parent=self,
                            label=self.getValSpareText())
#                            style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)
        self.valtext.SetMinSize(self.valtext.GetSize())

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.slider, 1, wx.ALIGN_CENTER)
        self.sizer.Add(self.valtext, 0, wx.ALIGN_CENTER)
        self.SetSizer(self.sizer)
#        self.Layout()
        self.sizer.SetSizeHints(self)

        self.updateValText()

        self.Bind(wx.EVT_SCROLL, self.onSlider)

    def onSlider(self, evt):
        if evt.GetEventType()==wx.wxEVT_SCROLL_CHANGED or \
                evt.GetEventType()==wx.wxEVT_SCROLL_THUMBTRACK:
            self.updateValText()
            self.onGUI(self.slider.GetValue())

    def setVal(self, val):
        if val!=self.slider.GetValue():
            self.slider.SetValue(val)
            self.updateValText()

    def updateValText(self):
        val = self.slider.GetValue()
        self.valtext.SetLabel(str(val))

    def getValSpareText(self):
        return '127'

class SignCtrlGUI(StdCtrlGUI):
    def __init__(self, parent, interface, cdef):
        StdCtrlGUI.__init__(self, parent, interface, cdef)

    def updateValText(self):
        val = self.slider.GetValue()-64
        self.valtext.SetLabel(str(val))

    def getValSpareText(self):
        return '127'

class SignPercentCtrlGUI(StdCtrlGUI):
    def __init__(self, parent, interface, cdef):
        self.negspan = 64 - cdef.valrange[0]
        self.posspan = cdef.valrange[1] - 64
        StdCtrlGUI.__init__(self, parent, interface, cdef)

    def updateValText(self):
        val = self.slider.GetValue()-64
        if val<0:
            val = val*100/self.negspan
        else:
            val = val*100/self.posspan
        self.valtext.SetLabel(str(val)+'%')

    def getValSpareText(self):
        return '-100%'

class SignLabelCtrlGUI(StdCtrlGUI):
    def __init__(self, parent, interface, cdef):
        self.lbl,val = cdef.valinfo.get(0,'x 0').split()
        self.lblval = int(val)
        StdCtrlGUI.__init__(self, parent, interface, cdef)

    def updateValText(self):
        val = self.slider.GetValue()-64
        if val==self.lblval:
            self.valtext.SetLabel(self.lbl)
        else:
            self.valtext.SetLabel(str(val))

    def getValSpareText(self):
        if len(self.lbl)>3:
            return self.lbl
        else:
            return '127'

class LabelCtrlGUI(StdCtrlGUI):
    def __init__(self, parent, interface, cdef):
        self.lbl,val = cdef.valinfo.get(0,'x 0').split()
        self.lblval = int(val)
        StdCtrlGUI.__init__(self, parent, interface, cdef)

    def updateValText(self):
        val = self.slider.GetValue()
        if val==self.lblval:
            self.valtext.SetLabel(self.lbl)
        else:
            self.valtext.SetLabel(str(val))

    def getValSpareText(self):
        if len(self.lbl)>3:
            return self.lbl
        else:
            return '127'

class PercentCtrlGUI(StdCtrlGUI):
    def __init__(self, parent, interface, cdef):
        self.minflt = int(cdef.valinfo.get(0,'0'))
        self.minval = cdef.valrange[0]
        maxflt = int(cdef.valinfo.get(1,'100'))
        self.factor = float(maxflt-self.minflt) \
            / (cdef.valrange[1]-self.minval)
        StdCtrlGUI.__init__(self, parent, interface, cdef)

    def updateValText(self):
        val = (self.slider.GetValue()-self.minval)*self.factor+self.minflt
        self.valtext.SetLabel('%.1f%%' % val)

    def getValSpareText(self):
        return '100.0%'

class PercentLabelCtrlGUI(StdCtrlGUI):
    def __init__(self, parent, interface, cdef):
        self.lbl,val = cdef.valinfo.get(0,'x 0').split()
        self.lblval = int(val)
        self.minval = cdef.valrange[0]
        self.factor = 100. / (cdef.valrange[1]-self.minval)
        StdCtrlGUI.__init__(self, parent, interface, cdef)

    def updateValText(self):
        val = self.slider.GetValue()
        if val==self.lblval:
            self.valtext.SetLabel(self.lbl)
        else:
            val = (val-self.minval)*self.factor
            self.valtext.SetLabel('%.1f%%' % val)

    def getValSpareText(self):
        if len(self.lbl)>6:
            return self.lbl
        else:
            return '100.0%'

class InterpolCtrlGUI(StdCtrlGUI):
    def __init__(self, parent, interface, cdef):
        self.setupInterpol(cdef)
        StdCtrlGUI.__init__(self, parent, interface, cdef)

    def setupInterpol(self, cdef):
        self.interpol = []
        preval = -1
        try:
            for entry in cdef.valinfo.values():
                flt,val = entry.split()
                flt = float(flt)
                val = int(val)
                if preval>=0:
                    m = (flt-preflt)/(val-preval)
                    self.interpol.append((preval,val,preflt,m))
                preflt = flt
                preval = val
        except ValueError as error:
            showError("While setting up InterpolCtrlGUI %s:\n%s" \
                          % (cdef.name, str(error)))

    def updateValText(self):
        val = self.slider.GetValue()
        for entry in self.interpol:
            minval,maxval,b,m = entry
            if val<=maxval:
                val = (val-minval)*m+b
                self.valtext.SetLabel('%.1f' % val)
                return

    def getValSpareText(self):
        return '99.9'

class NegCtrlGUI(StdCtrlGUI):
    def __init__(self, parent, interface, cdef):
        StdCtrlGUI.__init__(self, parent, interface, cdef)

    def updateValText(self):
        val = self.slider.GetValue()
        self.valtext.SetLabel('-%d' % val)

    def getValSpareText(self):
        return '-127'
    
class ShapeCtrlGUI(CtrlGUI):
    def __init__(self, parent, interface, cdef):
        CtrlGUI.__init__(self, parent, interface, cdef)
        span = cdef.valrange[1] - cdef.valrange[0] + 1
        self.halfspan = span/2
        self.valmax = cdef.valrange[1]
        self.labels = [cdef.valinfo.get(i,'') for i in range(5)]

        self.slider = wx.Slider(parent=self, minValue=cdef.valrange[0],
                                maxValue=cdef.valrange[1],
                                size=(60,-1),
                                style=wx.SL_HORIZONTAL)
        self.slider.SetPageSize(span/16)
        self.valtext \
            = wx.StaticText(parent=self,
                            label=self.getValSpareText())
#                            style=wx.ALIGN_CENTER|wx.ST_NO_AUTORESIZE)
#        self.valtext.SetMinSize(self.valtext.GetSize())

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.slider, 0, wx.EXPAND)
        self.sizer.Add(self.valtext, 0, wx.ALIGN_CENTER)
        self.SetSizer(self.sizer)
        self.sizer.SetSizeHints(self)
#        self.Fit()

        self.updateValText()

        self.Bind(wx.EVT_SCROLL, self.onSlider)

    def onSlider(self, evt):
        if evt.GetEventType()==wx.wxEVT_SCROLL_CHANGED or \
                evt.GetEventType()==wx.wxEVT_SCROLL_THUMBTRACK:
            self.updateValText()
            self.onGUI(self.slider.GetValue())

    def setVal(self, val):
        if val!=self.slider.GetValue():
            self.slider.SetValue(val)
            self.updateValText()

    def updateValText(self):
        val = self.slider.GetValue()
        if val==0:
            text = self.labels[0]
        elif val<self.halfspan:
            text = self.labels[1] + ' %d%%' % (val*100/self.halfspan)
        elif val==self.halfspan:
            text = self.labels[2]
        elif val<self.valmax:
            text = self.labels[3] + ' %d%%' % \
                ((val-self.halfspan)*100/(self.halfspan-1))
        else:
            text = self.labels[4]
        self.valtext.SetLabel(text)
        self.Layout()

    def getValSpareText(self):
        if len(self.labels[1])>len(self.labels[3]):
            return self.labels[1]+' 99%'
        else:
            return self.labels[3]+' 99%'

class PrefixCtrlGUI(CtrlGUI):
    def __init__(self, parent, interface, cdef):
        CtrlGUI.__init__(self, parent, interface, cdef)
        self.setupLabels(cdef)

        self.slider = wx.Slider(parent=self, minValue=0,
                                maxValue=cdef.valrange[1],
                                size=(60,-1),
                                style=wx.SL_HORIZONTAL)
        self.valtext \
            = wx.StaticText(parent=self,
                            label=self.getValSpareText())
#                            style=wx.ALIGN_CENTER|wx.ST_NO_AUTORESIZE)
        self.valtext.SetMinSize(self.valtext.GetSize())

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.slider, 1)
        self.sizer.Add(self.valtext, 0, wx.ALIGN_CENTER)
        self.SetSizer(self.sizer)
        self.sizer.SetSizeHints(self)
#        self.Fit()

        self.updateValText()

        self.Bind(wx.EVT_SCROLL, self.onSlider)

    def setupLabels(self, cdef):
        try:
            self.prefixind = cdef.valrange[0]
            self.labels = [cdef.valinfo.get(i,'')
                           for i in range(self.prefixind)]
            template = cdef.valinfo.get(self.prefixind, 'x 0').split()
            self.labels.append(template[0])
            self.indexOffset = int(template[1])-self.prefixind
        except IndexError as error:
            self.labels = ['']
            self.prefixind = 0
            self.indexOffset = 0
            showError("While setting up PrefixCtrlGUI %s:\n%s" \
                          % (cdef.name, str(error)))

    def onSlider(self, evt):
        if evt.GetEventType()==wx.wxEVT_SCROLL_CHANGED or \
                evt.GetEventType()==wx.wxEVT_SCROLL_THUMBTRACK:
            self.updateValText()
            self.onGUI(self.slider.GetValue())

    def setVal(self, val):
        if val!=self.slider.GetValue():
            self.slider.SetValue(val)
            self.updateValText()

    def updateValText(self):
        val = self.slider.GetValue()
        if val<self.prefixind:
            text = self.labels[val]
        else:
            text = self.labels[self.prefixind] + ' %d' % (val+self.indexOffset)
        self.valtext.SetLabel(text)

    def getValSpareText(self):
        return self.labels[self.prefixind] + \
            ' %d' % (self.cdef.valrange[1]+self.indexOffset)

class ListCtrlGUI(CtrlGUI):
    def __init__(self, parent, interface, cdef):
        CtrlGUI.__init__(self, parent, interface, cdef)

        self.offset = cdef.valrange[0]
        lbls = [('%d:  ' % i) + cdef.valinfo.get(i,'') 
                for i in range(cdef.valrange[0], cdef.valrange[1]+1)]
        self.choice = wx.Choice(self, -1, choices=lbls)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.choice,0)
        self.SetSizer(sizer)
#        sizer.SetSizeHints(self)
        self.Bind(wx.EVT_CHOICE, self.onChoice)

    def onChoice(self, evt):
        self.onGUI(self.choice.GetSelection()+self.offset)

    def setVal(self, val):
        self.choice.SetSelection(val-self.offset)

class PrefixListCtrlGUI(CtrlGUI):
    def __init__(self, parent, interface, cdef):
        CtrlGUI.__init__(self, parent, interface, cdef)

        self.choice = wx.Choice(self, -1, choices=self.makeLabels())
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.choice,0)
        self.SetSizer(sizer)
#        sizer.SetSizeHints(self)
        self.Bind(wx.EVT_CHOICE, self.onChoice)

    def makeLabels(self):
        try:
            prefixind = self.cdef.valrange[0]
            labels = [('%d:  ' % i) + self.cdef.valinfo.get(i,'')
                           for i in range(prefixind)]
            template = self.cdef.valinfo.get(prefixind, 'x 0').split()
            offset = int(template[1])-prefixind
            labels.extend(['%d:  %s %d' % (i,template[0],i+offset)
                           for i in range(prefixind, self.cdef.valrange[1]+1)])
        except IndexError as error:
            labels = ['']
            showError("While setting up PrefixListCtrlGUI %s:\n%s" \
                          % (self.cdef.name, str(error)))
        return labels

    def onChoice(self, evt):
        self.onGUI(self.choice.GetSelection())

    def setVal(self, val):
        self.choice.SetSelection(val)

KeyNames = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','H']

class KeyCtrlGUI(StdCtrlGUI):
    def __init__(self, parent, interface, cdef):
        StdCtrlGUI.__init__(self, parent, interface, cdef)

    def updateValText(self):
        val = self.slider.GetValue()
        octave = val/12 - 1
        key = val%12
        self.valtext.SetLabel("%s%d" % (KeyNames[key], octave))

    def getValSpareText(self):
        return 'C#-1'

class CheckCtrlGUI(CtrlGUI):
    def __init__(self, parent, interface, cdef):
        CtrlGUI.__init__(self, parent, interface, cdef)

        self.checkbox = wx.CheckBox(self, -1)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.checkbox,0)
        self.SetSizer(sizer)

        self.Bind(wx.EVT_CHECKBOX, self.onCheck)

    def onCheck(self, evt):
        self.onGUI(int(self.checkbox.GetValue()))

    def setVal(self, val):
        self.checkbox.SetValue(val)


class SeparatorGUI(wx.StaticLine):
    def __init__(self, parent, gaps):
        wx.StaticLine.__init__(self, parent)
        self.gaps = gaps
    def getGap(self, mode):
        return self.gaps[mode]


class CtrlBoxBase(wx.Panel):
    ctrlguidict = {
        CT_STD: StdCtrlGUI,
        CT_LIST: ListCtrlGUI,
        CT_SHAPE: ShapeCtrlGUI,
        CT_PREFIX: PrefixCtrlGUI,
        CT_SIGN: SignCtrlGUI,
        CT_SIGNPERCENT: SignPercentCtrlGUI,
        CT_SIGNLABEL: SignLabelCtrlGUI,
        CT_PERCENT: PercentCtrlGUI,
        CT_INTERPOL: InterpolCtrlGUI,
        CT_CHECKBOX: CheckCtrlGUI,
        CT_NEGATIVE: NegCtrlGUI,
        CT_PREFIXLIST: PrefixListCtrlGUI,
        CT_LABEL: LabelCtrlGUI,
        CT_PERCENTLABEL: PercentLabelCtrlGUI,
        CT_KEY: KeyCtrlGUI,
        }

    def __init__(self, pagegui, interface, blockdef):
        wx.Panel.__init__(self, pagegui)
        self.pagegui = pagegui
        self.interface = interface
        self.blockdef = blockdef

        box = wx.StaticBox(self, -1, blockdef.name)
        self.boxsizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        self.SetSizer(self.boxsizer)
        self.hgap = 5
        self.vgap = 4
        self.controllers = []
        self.nummodes = self.blockdef.getNumModes()
        self.vsize = [0]*self.nummodes

    def build(self):
        for cdef in self.blockdef.ctrldefs:
            self.buildCtrl(cdef)

    def buildCtrl(self, cdef):
        if cdef.ctype!=CT_SEPARATOR:
            ctrl = self.ctrlguidict[cdef.ctype](self, self.interface, cdef)
            ctrl.Fit()
            for m in range(self.nummodes):
                if m in cdef.modes:
                    self.vsize[m] += ctrl.GetSize()[1]+self.vgap
        else:
            maxsize = max(self.vsize)
            ctrl = SeparatorGUI(self, [maxsize-s for s in self.vsize])
            self.vsize = [0]*self.nummodes
        centry = (cdef, ctrl)
        self.controllers.append(centry)

    def update(self):
        pass


class CtrlBoxGUI(CtrlBoxBase):
    def __init__(self, pagegui, interface, blockdef):
        CtrlBoxBase.__init__(self, pagegui, interface, blockdef)

        self.sizer = wx.FlexGridSizer(cols=2, hgap=self.hgap, vgap=self.vgap)
        self.sizer.AddGrowableCol(1)
        self.boxsizer.Add(self.sizer, 0, wx.EXPAND)

        self.initModeCtrl(blockdef)
        self.build()
        self.updateActive()

    def initModeCtrl(self, blockdef):
        self.modetype = blockdef.modetype
        if blockdef.modetype==MODE_EXCEPT:
            self.exceptmode = blockdef.getExceptMode()
            self.interface.addListener(self.exceptmode[0], self.onExcept)
        if blockdef.modetype!=MODE_NONE:
            self.interface.addListener(blockdef.cid, self.onMode)
            self.readMode()
        else:
            self.mode = 0

    def readMode(self):
        modeval = self.interface.getCtrl(self.blockdef.cid)
        if self.modetype==MODE_EXCEPT:
            exceptval = self.interface.getCtrl(self.exceptmode[0])
            self.updateMode(modeval, exceptval)
        elif self.modetype!=MODE_NONE:
            self.updateMode(modeval)

    def updateMode(self, modeval=None, exceptval=None):
        if self.modetype==MODE_STD:
            self.mode = modeval
        elif self.modetype==MODE_OPENEND:
            if modeval>self.blockdef.valrange[0]:
                self.mode = self.blockdef.valrange[0]
            else:
                self.mode = modeval
        elif self.modetype==MODE_EXCEPT:
            if exceptval!=None:
                if exceptval>=self.exceptmode[1] \
                        and exceptval<=self.exceptmode[2]:
                    self.mode = self.blockdef.valrange[1]+1 \
                        + exceptval-self.exceptmode[1]
                else:
                    if modeval==None:
                        modeval = self.interface.getCtrl(self.blockdef.cid)
                    self.mode = modeval
            elif self.mode<=self.blockdef.valrange[1]:
                self.mode = modeval

    def updateCtrl(self, centry):
        cdef,ctrl = centry
        if cdef.ctype!=CT_SEPARATOR:
            if self.modetype==MODE_NONE \
                    or self.mode in cdef.modes:
                ctrl.setVal(self.interface.getCtrl(cdef.cid))
                ctrl.Show()
                self.sizer.Add(ctrl.label, 0, 
                               wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
                self.sizer.Add(ctrl, 0, wx.EXPAND)
            else:
                ctrl.Hide()
        else:
            self.sizer.Add((1,1))
            self.sizer.Add(ctrl, 0, wx.EXPAND|wx.TOP, ctrl.getGap(self.mode))

    def updateActive(self):
        self.sizer.Clear()
        for centry in self.controllers:
            self.updateCtrl(centry)
 #       self.boxsizer.SetSizeHints(self)

    def update(self):
        self.readMode()
        self.updateActive()

    def onMode(self, val):
        self.updateMode(val)
        self.updateActive()
        self.pagegui.Layout()

    def onExcept(self, val):
        self.updateMode(exceptval=val)
        self.updateActive()
        self.pagegui.Layout()


class MuteBitmaps(object):
    def __init__(self, winobj):
        self.size = winobj.ConvertDialogSizeToPixels((10,6))
        self.activebmp = self.makeBMC('green')
        self.inactivebmp = self.makeBMC('yellow')
        self.mutebmp = self.makeBMC('red')

    def makeBMC(self, color):
        bmp = wx.EmptyBitmap(*self.size)
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        dc.SetBackground(wx.Brush(color))
        dc.Clear()
        dc.SelectObject(wx.NullBitmap)
        return bmp


MB_INACTIVE = 0
MB_MUTE = 1
MB_ACTIVE = 2

class MuteButton(wx.BitmapButton):
    def __init__(self, parent, interface, cid, ctrl, onmute, ind, mutebitmaps):
        wx.BitmapButton.__init__(self, parent, -1, mutebitmaps.inactivebmp)
        self.cval = 0
        self.state = MB_INACTIVE
        self.onmute = onmute
        self.ind = ind
        self.mutebitmaps = mutebitmaps
        self.interface = interface
        self.cid = cid
        self.ctrl = ctrl
        self.Bind(wx.EVT_BUTTON, self.onGUI)
        
        interface.addListener(cid, self.onCtrl)

    def onGUI(self, evt):
        if self.state==MB_MUTE:
            self.setMute(False)
        else:
            self.setMute(True)
        self.onmute(self.state, self.ind)

    def onCtrl(self, val):
        self.setState(val)
        self.onmute(self.state, self.ind)

    def setMute(self, mute):
        if mute:
            cval = self.interface.getCtrl(self.cid)
            if cval:
                self.state = MB_MUTE
                self.SetBitmapLabel(self.mutebitmaps.mutebmp)
                self.cval = cval
                self.interface.setCtrl(self.cid, 0)
        elif self.state==MB_MUTE:
            self.interface.setCtrl(self.cid, self.cval)
            # note that setCtrl() triggers setState()

    def setState(self, cval, forceunmute=False):
        if cval:
            self.state = MB_ACTIVE
            self.SetBitmapLabel(self.mutebitmaps.activebmp)
        elif self.state!=MB_MUTE or forceunmute:
            self.state = MB_INACTIVE
            self.SetBitmapLabel(self.mutebitmaps.inactivebmp)

    def update(self):
        cval = self.interface.getCtrl(self.cid)
        self.setState(cval, forceunmute=True)
        self.ctrl.setVal(cval)


class MuteBoxGUI(CtrlBoxBase):
    def __init__(self, pagegui, interface, blockdef):
        CtrlBoxBase.__init__(self, pagegui, interface, blockdef)

        self.sizer = wx.FlexGridSizer(cols=3, hgap=self.hgap, vgap=self.vgap)
        self.sizer.AddGrowableCol(2)
        self.boxsizer.Add(self.sizer, 0, wx.EXPAND)

        self.build()
        self.build2()
        self.update()

    def build2(self):
        self.mutes = []
        mutebitmaps = MuteBitmaps(self)
        for cdef,ctrl in self.controllers:
            if cdef.ctype!=CT_SEPARATOR:
                ind = len(self.mutes)
                mute = MuteButton(self, self.interface, cdef.cid, ctrl,
                                  self.onMuteBut, ind, mutebitmaps)
                self.mutes.append(mute)

                ctrl.Show()
                self.sizer.Add(ctrl.label, 0, 
                               wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
                self.sizer.Add(mute, 0, wx.ALIGN_CENTER_VERTICAL)
                self.sizer.Add(ctrl, 0, wx.EXPAND)
            else:
                self.sizer.Add((1,1))
                self.sizer.Add((1,1))
                self.sizer.Add(ctrl, 0, wx.EXPAND|wx.TOP, 0)

    def update(self):
        for mutebut in self.mutes:
            mutebut.update()

    def onMuteBut(self, mute, ind):
        pass



class CtrlPageGUI(wx.Panel):
    def __init__(self, parent, interface, pagedef):
        wx.Panel.__init__(self, parent)
        self.boxes = []
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)

        colsizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(colsizer, 1)
        col = 0
        cnt = 0
        for blockdef in pagedef.blocks:
            if col<pagedef.cols and cnt>=pagedef.collength.get(col,0):
                colsizer = wx.BoxSizer(wx.VERTICAL)
                self.sizer.Add(colsizer, 1, wx.LEFT, 4)
                col += 1
                cnt = 0
            if blockdef.modetype==MODE_MUTE:
                box = MuteBoxGUI(self, interface, blockdef)
            else:
                box = CtrlBoxGUI(self, interface, blockdef)
            if cnt>=1:
                colsizer.Add(box, 0, wx.EXPAND|wx.TOP, 4)
            else:
                colsizer.Add(box, 0, wx.EXPAND)
            self.boxes.append(box)
            cnt += 1
                
#        self.Layout()
#        self.sizer.SetSizeHints(self)

    def update(self):
        for box in self.boxes:
            box.update()
        self.Layout()


class ControllersGUI(object):
    def __init__(self, notebook, interface):
        self.notebook = notebook
        self.interface = interface
        interface.addPrgChngListener(self.onProgChange)

    def setup(self, ctrlpages):
        self.pages = []
        self.interface.clearAllListeners()
        try:
            print "building pages: ",
            for pagedef in ctrlpages.pages:
                if not pagedef.name.startswith('.'):
                    print "%s.." % pagedef.name,
                    sys.stdout.flush()
                    page = CtrlPageGUI(self.notebook, self.interface, pagedef)
                    self.notebook.AddPage(page, pagedef.name)
                    self.pages.append(page)
            print "done"
        except StandardError as error:
            raise
#            showError(str(error))

    def onProgChange(self):
        for page in self.pages:
            page.update()


class CtrlDefDialog(wx.Dialog):
    def __init__(self, ctrlpages):
        wx.Dialog.__init__(self, None, title="Setup Controller Definitions",
                           style=wx.RESIZE_BORDER)
        self.setupDialog(ctrlpages)
        self.save = False

    def setupDialog(self, ctrlpages):
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        treesizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(treesizer, 1, wx.EXPAND|wx.ALL, 5)
        self.tree = wx.TreeCtrl(self)
        self.setupTree(ctrlpages)
        treesizer.Add(self.tree, 1, wx.EXPAND|wx.RIGHT, 5)
        butsizer = wx.BoxSizer(wx.VERTICAL)
        treesizer.Add(butsizer, 1, wx.EXPAND|wx.RIGHT, 5)
        self.setupCDef(butsizer)
        self.selNone()

        butsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.setupButtons(butsizer)
        sizer.Add(butsizer, 0, wx.EXPAND|wx.ALL, 5)
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.onTreeSel)
        self.Fit()
        sizer.SetSizeHints(self)

    def setupButtons(self, butsizer):
        but = wx.Button(self, -1, "Add Child")
        but.Bind(wx.EVT_BUTTON, self.onAddChild)
        butsizer.Add(but, 0)
        but = wx.Button(self, -1, "Add Before")
        but.Bind(wx.EVT_BUTTON, self.onAddBefore)
        butsizer.Add(but, 0)
        self.copybut = wx.ToggleButton(self, -1, "Copy")
        self.copybut.Bind(wx.EVT_TOGGLEBUTTON, self.onCopy)
        butsizer.Add(self.copybut, 0, wx.EXPAND)
        but = wx.Button(self, -1, "Delete")
        but.Bind(wx.EVT_BUTTON, self.onDelete)
        butsizer.Add(but, 0, wx.ALIGN_LEFT)
        butsizer.Add((1,10), 1)
        but = wx.Button(self, wx.ID_CANCEL, "Cancel")
        butsizer.Add(but, 0, wx.ALIGN_RIGHT)
        but = wx.Button(self, wx.ID_OK, "Use")
        butsizer.Add(but, 0)
        but = wx.Button(self, -1, "Save")
        but.Bind(wx.EVT_BUTTON, self.onSave)
        butsizer.Add(but, 0)

    def setupCDef(self, butsizer):
        label = wx.StaticText(self, label='Name')
        self.name = wx.TextCtrl(self)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        sizer.Add(self.name, 1)
        butsizer.Add(sizer, 0, wx.EXPAND|wx.TOP, 5)

        label = wx.StaticText(self, label='Mode Type')
        self.modetype = wx.Choice(self, choices=['None', 'Standard',
                                                 'OpenEnd','Except',
                                                 'Mute'])
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        sizer.Add(self.modetype, 0)
        butsizer.Add(sizer, 0, wx.TOP, 5)

        label = wx.StaticText(self, label='Ctrl Type')
        self.ctype = wx.Choice(self, 
                               choices=['Standard','List', 'Shape',
                                        'Prefix', 'Sign', 'SignPercent',
                                        'SignLabel', 'Percent', 'Interpol', 
                                        'Checkbox', 'Negative', 'Separator',
                                        'PrefixList', 'Label','PercentLabel',
                                        'Key'])
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        sizer.Add(self.ctype, 0)
        butsizer.Add(sizer, 0, wx.TOP, 5)

        label = wx.StaticText(self, label='Ctrl Id')
        self.idpage = wx.Choice(self, 
                                choices=vxcmidi.CTRL_NAMES)
        self.idnumber = wx.SpinCtrl(self, max=127)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.idpage, 0, wx.LEFT|wx.RIGHT, 5)
        sizer.Add(self.idnumber, 0)
        butsizer.Add(sizer, 0, wx.TOP, 5)

        label = wx.StaticText(self, label='Range min')
        self.rangemin = wx.SpinCtrl(self, max=127)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        sizer.Add(self.rangemin, 0, wx.RIGHT, 10)
        label = wx.StaticText(self, label='max')
        self.rangemax = wx.SpinCtrl(self, max=127)
        sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        sizer.Add(self.rangemax, 0)
        butsizer.Add(sizer, 0, wx.TOP, 5)

        label = wx.StaticText(self, label='Active modes')
        self.modes = wx.TextCtrl(self)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        sizer.Add(self.modes, 1)
        butsizer.Add(sizer, 0, wx.EXPAND|wx.TOP, 5)

        self.valinfo = wx.ListCtrl(self, style=wx.LC_REPORT)
        self.valinfo.InsertColumn(0, '#')
        self.valinfo.InsertColumn(1, 'ValInfo', width=150)
        butsizer.Add(self.valinfo, 1, wx.EXPAND|wx.TOP, 5)

        self.name.Bind(wx.EVT_TEXT, self.onName)
        self.modetype.Bind(wx.EVT_CHOICE, self.onModeType)
        self.ctype.Bind(wx.EVT_CHOICE, self.onType)
        self.idpage.Bind(wx.EVT_CHOICE, self.onIdPage)
        self.idnumber.Bind(wx.EVT_SPINCTRL, self.onIdNumber)
        self.rangemin.Bind(wx.EVT_SPINCTRL, self.onRangeMin)
        self.rangemax.Bind(wx.EVT_SPINCTRL, self.onRangeMax)
        self.modes.Bind(wx.EVT_TEXT, self.onModes)
        self.valinfo.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onValInfo)

    def setupTree(self, ctrlpages):
        rootid = self.tree.AddRoot("Pages")
        for page in ctrlpages.pages:
            pageid = self.tree.AppendItem(rootid, '')
            self.insertPage(pageid, page)
#            self.tree.Expand(pageid)
        self.tree.Expand(rootid)

    def insertPage(self, pageitem, pagedef):
        self.tree.SetItemText(pageitem, pagedef.name)
        self.tree.SetItemPyData(pageitem, pagedef.copy())
        for block in pagedef.blocks:
            blockitem = self.tree.AppendItem(pageitem, block.name)
            self.insertBlock(blockitem, block)

    def insertBlock(self, blockitem, blockdef):
        self.tree.SetItemPyData(blockitem, blockdef.copy())
        for ctrl in blockdef.ctrldefs:
            ctrlitem = self.tree.AppendItem(blockitem, ctrl.name)
            self.insertCtrl(ctrlitem, ctrl)

    def insertCtrl(self, ctrlitem, ctrldef):
        self.tree.SetItemPyData(ctrlitem, ctrldef.copy())

    def onTreeSel(self, evt):
        item = evt.GetItem()
        obj = self.tree.GetItemPyData(item)
        if type(obj)==CtrlDef:
            self.selCtrl(obj)
        elif type(obj)==BlockDef:
            self.selBlock(obj)
        elif type(obj)==PageDef:
            self.selPage(obj)
        else:
            self.selNone()

    def selCtrl(self, ctrldef):
        self.name.Enable()
        self.name.SetValue(ctrldef.name)
        self.modetype.Disable()
        self.ctype.Enable()
        self.ctype.SetSelection(ctrldef.ctype)
        self.idpage.Enable()
        self.idpage.SetSelection(ctrldef.cid[0])
        self.idnumber.Enable()
        self.idnumber.SetValue(ctrldef.cid[1])
        self.rangemin.Enable()
        self.rangemin.SetValue(ctrldef.valrange[0])
        self.rangemax.Enable()
        self.rangemax.SetValue(ctrldef.valrange[1])
        self.modes.Enable()
        self.modes.SetValue(ctrldef.getModeStr())
        self.updateValInfo(ctrldef)
    def selBlock(self, blockdef):
        self.name.Enable()
        self.name.SetValue(blockdef.name)
        self.modetype.Enable()
        self.modetype.SetSelection(blockdef.modetype)
        self.ctype.Disable()
        self.idpage.Enable()
        self.idpage.SetSelection(blockdef.cid[0])
        self.idnumber.Enable()
        self.idnumber.SetValue(blockdef.cid[1])
        self.rangemin.Enable()
        self.rangemin.SetValue(blockdef.valrange[0])
        self.rangemax.Enable()
        self.rangemax.SetValue(blockdef.valrange[1])
        self.modes.Disable()
        self.updateValInfoBlock(blockdef)
    def selPage(self, pagedef):
        self.selNone()
        self.name.Enable()
        self.name.SetValue(pagedef.name)
        self.rangemin.Enable()
        self.rangemin.SetValue(pagedef.cols)
        self.updateValInfoPage(pagedef)
    def selNone(self):
        self.name.Disable()
        self.modetype.Disable()
        self.ctype.Disable()
        self.idpage.Disable()
        self.idnumber.Disable()
        self.rangemin.Disable()
        self.rangemax.Disable()
        self.modes.Disable()
        self.disableValInfo()

    def disableValInfo(self):
        self.valinfo.DeleteAllItems()
        self.valinfo.Disable()
    def setValInfoRange(self, obj, indmin, indmax):
        self.valinfo.Enable()
        self.valinfo.DeleteAllItems()
        for i in range(indmax-indmin+1):
            self.valinfo.InsertStringItem(i, str(i+indmin))
            self.valinfo.SetStringItem(i, 1, obj.getValInfo(i+indmin))
        self.valinfo_offset = indmin
    def updateValInfo(self, ctrldef):
        if ctrldef.ctype==CT_LIST:
            self.setValInfoRange(ctrldef,
                                ctrldef.valrange[0], ctrldef.valrange[1])
        elif ctrldef.ctype==CT_SHAPE:
            self.setValInfoRange(ctrldef, 0, 4)
        elif ctrldef.ctype in [CT_PREFIX,CT_PREFIXLIST]:
            self.setValInfoRange(ctrldef, 0, ctrldef.valrange[0])
        elif ctrldef.ctype in [CT_SIGNLABEL,CT_LABEL,CT_PERCENTLABEL]:
            self.setValInfoRange(ctrldef, 0, 0)
        elif ctrldef.ctype==CT_PERCENT:
            self.setValInfoRange(ctrldef, 0, 1)
        elif ctrldef.ctype==CT_INTERPOL:
            self.setValInfoRange(ctrldef, 0, 11)
        else:
            self.disableValInfo()
    def updateValInfoBlock(self, blockdef):
        if blockdef.modetype==MODE_EXCEPT:
            self.setValInfoRange(blockdef, 0, 0)
        else:
            self.disableValInfo()
    def updateValInfoPage(self, pagedef):
        self.setValInfoRange(pagedef, 0, pagedef.cols-1)

    def onName(self, evt):
        item = self.tree.GetSelection()
        obj = self.tree.GetItemPyData(item)
        self.tree.SetItemText(item, self.name.GetValue())
        obj.name = self.name.GetValue()
    def onModeType(self, evt):
        obj = self.tree.GetItemPyData(self.tree.GetSelection())
        obj.modetype = self.modetype.GetSelection()
        self.updateValInfoBlock(obj)
    def onType(self, evt):
        obj = self.tree.GetItemPyData(self.tree.GetSelection())
        obj.ctype = self.ctype.GetSelection()
        self.updateValInfo(obj)
    def onIdPage(self, evt):
        obj = self.tree.GetItemPyData(self.tree.GetSelection())
        obj.setcid(page=self.idpage.GetSelection())
    def onIdNumber(self, evt):
        obj = self.tree.GetItemPyData(self.tree.GetSelection())
        obj.setcid(number=self.idnumber.GetValue())
    def onRangeMin(self, evt):
        obj = self.tree.GetItemPyData(self.tree.GetSelection())
        if type(obj) in [CtrlDef, BlockDef]:
            obj.setRange(min=self.rangemin.GetValue())
            if type(obj)==CtrlDef:
                self.updateValInfo(obj)
        elif type(obj)==PageDef:
            obj.cols = self.rangemin.GetValue()
            self.updateValInfoPage(obj)
    def onRangeMax(self, evt):
        obj = self.tree.GetItemPyData(self.tree.GetSelection())
        obj.setRange(max=self.rangemax.GetValue())
        if type(obj)==CtrlDef:
            self.updateValInfo(obj)
    def onModes(self, evt):
        obj = self.tree.GetItemPyData(self.tree.GetSelection())
        obj.setModeStr(self.modes.GetValue())
    def onValInfo(self, evt):
        ind = evt.GetIndex()
        item = self.valinfo.GetItem(ind, 1)
        dialogmsg = 'Enter ValInfo %d' % (ind+self.valinfo_offset)
        dialog = wx.TextEntryDialog(None, dialogmsg, 'Edit ValInfo',
                                    item.GetText())
        if dialog.ShowModal()==wx.ID_OK:
            self.valinfo.SetStringItem(ind, 1, dialog.GetValue())
            obj = self.tree.GetItemPyData(self.tree.GetSelection())
            if type(obj) in [CtrlDef, BlockDef]:
                obj.valinfo[ind+self.valinfo_offset] = dialog.GetValue()
            elif type(obj)==PageDef:
                obj.setColLengthStr(ind, dialog.GetValue())
        dialog.Destroy()

    def onAddChild(self, evt):
        item = self.tree.GetSelection()
        obj = self.tree.GetItemPyData(item)
        if type(obj)==CtrlDef:
            item = self.tree.GetItemParent(item)
        newitem = self.tree.AppendItem(item, '')
        if item==self.tree.GetRootItem():
            self.makeNewPage(newitem)
        elif type(obj)==PageDef:
            self.makeNewBlock(newitem)
        else:
            self.makeNewCtrl(newitem)
        self.tree.Expand(item)
        self.tree.SelectItem(newitem)

    def onAddBefore(self, evt):
        item = self.tree.GetSelection()
        obj = self.tree.GetItemPyData(item)
        if item==self.tree.GetRootItem():
            return
        parent = self.tree.GetItemParent(item)
        item = self.tree.GetPrevSibling(item)
        if item:
            newitem = self.tree.InsertItem(parent, item, '')
        else:
            newitem = self.tree.PrependItem(parent, '')
        if type(obj)==PageDef:
            self.makeNewPage(newitem)
        elif type(obj)==BlockDef:
            self.makeNewBlock(newitem)
        else:
            self.makeNewCtrl(newitem)
        self.tree.SelectItem(newitem)

    def onCopy(self, evt):
        if self.copybut.GetValue()==True:
            self.copyitem = self.tree.GetSelection()
    def getCopyObj(self):
        if self.copybut.GetValue()==True:
            self.copybut.SetValue(False)
            return self.tree.GetItemPyData(self.copyitem)
        else:
            return None

    def makeNewPage(self, item):
        page = self.getCopyObj()
        if type(page)==PageDef:
            self.getBlocks(self.copyitem, page)
        else:
            page = PageDef('new page')
        self.insertPage(item, page)
    def makeNewBlock(self, item):
        block = self.getCopyObj()
        if type(block)==BlockDef:
            self.getCtrls(self.copyitem, block)
        else:
            block = BlockDef('new block')
        self.insertBlock(item, block)
    def makeNewCtrl(self, item):
        ctrl = self.getCopyObj()
        if type(ctrl)!=CtrlDef:
            ctrl = CtrlDef('new ctrl')
        self.insertCtrl(item, ctrl)

    def onDelete(self, evt):
        self.copybut.SetValue(False)
        item = self.tree.GetSelection()
        if item!=self.tree.GetRootItem():
            newsel = self.tree.GetNextSibling(item)
            if not newsel:
                newsel = self.tree.GetPrevSibling(item)
            self.tree.SelectItem(newsel)
            self.tree.Delete(item)

    def onSave(self, evt):
        self.save = True
        self.EndModal(wx.ID_OK)

    def getPages(self):
        ctrlpages = CtrlPages()
        root = self.tree.GetRootItem()
        item, cook = self.tree.GetFirstChild(root)
        while item:
            pagedef = self.tree.GetItemPyData(item)
            ctrlpages.pages.append(pagedef)
            self.getBlocks(item, pagedef)
            item, cook = self.tree.GetNextChild(root, cook)
        return ctrlpages

    def getBlocks(self, pageitem, pagedef):
        pagedef.blocks = []
        item, cook = self.tree.GetFirstChild(pageitem)
        while item:
            blockdef = self.tree.GetItemPyData(item)
            pagedef.blocks.append(blockdef)
            self.getCtrls(item, blockdef)
            item, cook = self.tree.GetNextChild(pageitem, cook)

    def getCtrls(self, blockitem, blockdef):
        blockdef.ctrldefs = []
        item, cook = self.tree.GetFirstChild(blockitem)
        while item:
            ctrldef = self.tree.GetItemPyData(item)
            blockdef.ctrldefs.append(ctrldef)
            item, cook = self.tree.GetNextChild(blockitem, cook)


def showError(errstr):
    wx.MessageBox(errstr, "VirusXControl Error", wx.OK | wx.ICON_ERROR)
