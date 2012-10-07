

class CtrlMapping(object):
    """Defines a specific translation of the raw midi controller 
       values (0..127), e.g. to percent-values or labels"""
    pass

class CtrlDataType(object):
    """Defines a specific type of controller in terms
       of its possible controller values and their meaning/mapping"""

    def __init__(self):
        name = ''
        range = (0,127)
        mapping = None


class CtrlDef(object):
    """Defines a Virus controller with midi address and datatype

    address = (PageNumber, CtrlNumber)"""

    def __init__(self):
        familyname = ''
        name = ''
        address = None
        datatype = None


class CtrlInstance(object):
    """Defines a controller instance in vxc which tracks a certain
       Virus controller (CtrlDef) on a certain multi part/midi channel"""

    def __init__(self):
        name = ''
        ctrldef = None
        part = 0

class CtrlBlock(object):
    """Groups several CtrlInstance objects together"""

    def __init__(self):
        name = ''

class CtrlPage(object):
    """Groups several CtrlBlock objects together"""

    def __init__(self):
        name = ''


class CtrlGUI(object):
    """wxPython realisation of CtrlInstance"""

    def __init__(self):
        ctrlinstance = None

class BlockGUI(object):
    """wxPython realisation of CtrlBlock"""
    pass

class PageGUI(object):
    """wxPython realisation of CtrlPage"""
    pass
