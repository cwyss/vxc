
class A(object):
    def __init__(self):
        self.buf = [0,1,2]

    def __getitem__(self, ind):
        return self.buf[ind]

    def __setitem__(self, ind, val):
        if type(ind)==slice:
            (start,stop,step) = ind.indices(len(self.buf))
            print (start,stop,step), (stop+step-1-start)/step
            
