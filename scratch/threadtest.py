#!/usr/bin/env python

import thread,math,sys



def threadfunc(n):
    i=0
    while i<n:
        i += 1
        x = math.exp(math.sin(i))
        y = math.exp(-1/x/x)
    print "fertig"


n = 1000
if len(sys.argv)>1:
    n = int(sys.argv[1])
print n
thread.start_new_thread(threadfunc, (n,))
threadfunc(n)
