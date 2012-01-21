
class A(object):
    N1 = 17

    @classmethod
    def calc(cls):
        return 2*cls.N1

#    N2 = A.calc()

    def get(self):
        return self.calc()
