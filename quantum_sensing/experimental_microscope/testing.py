import time
from utils import *
import warnings, numpy as np
from multiprocessing import Pool
from matplotlib import pyplot as plt
from cProfile import run
from AWGcontrol import *
from DAQ_Analog import *

def rabi(seg, cyc, mw_delay, mw_duration, amp):
    t = np.arange(seg, step=1)
    omegaSin = 2 * np.pi * cyc
    pre, pulse, post = int((mw_delay-mw_duration)*seg//1e6), int(round(mw_duration*seg/1e6)), int(seg-mw_delay*seg//1e6)
    pre, pulse, post = np.zeros(pre, dtype=int), np.ones(pulse, dtype=int), np.zeros(post, dtype=int)
    print(pre.size, pulse.size, post.size)
    sq = np.concatenate((pre, pulse, post))
    sn = np.sin(omegaSin*t/seg)
    rawSignal = sq * amp * sn
    dacSignal = np.uint8((rawSignal/amp*127)+127)
    del t, sq, sn #, rawSignal
    return rawSignal

def AWGtest(N=100, dur=0.0005, f=2):
    admin = loadDLL()
    slotId = getSlotId(admin)
    if slotId:
        inst = admin.OpenInstrument(slotId)
        if inst: instId = inst.InstrId
    instrumentSetup(inst)
    task = configureDAQ(10)
    for _ in range(N):
        makeSingleESRSeqMarker(inst, dur, f, 0.1)
        readDAQ(task, 10*2, 10)
    #task = configureDAQ(1000*N)
    #makeESRSweep(inst, dur, np.full(N, f), 0.1)
    #readDAQ(task, 1000*N*2, 1000)

    SendScpi(inst, ":OUTP OFF")
    SendScpi(inst, ":MARK OFF")
    admin.CloseInstrument(instId)
    admin.Close()
    closeDAQTask(task)

if __name__ == '__main__':
    '''args, N = (8998848, 5999232, 250000, 5, 1), 1
    plt.plot(np.arange(args[0], step=1), rabi(*args))
    plt.xlim(2.24965e6, 2.249725e6)
    plt.show()'''
    AWGtest(dur=0.005, f=1)


