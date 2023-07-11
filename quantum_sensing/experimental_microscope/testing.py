import time
from utils import *
import warnings, numpy as np
from multiprocessing import Pool
from matplotlib import pyplot as plt
from cProfile import run

def slow(segmentLength, bits, sinCycles, mw_delay, mw_duration, amp):
    time = np.linspace(0, segmentLength-1, segmentLength)
    omegaSin = 2 * np.pi * sinCycles
    pulseProfile = np.zeros(segmentLength)
    count = 0
    for i in range(int((mw_delay-mw_duration)*segmentLength/1e6), int(mw_delay*segmentLength/1e6)):
        pulseProfile[i] = 1
        count += 1
    print(count)
    rawSignal = pulseProfile*amp*np.sin(omegaSin*time/segmentLength)
    dacSignal = np.uint8((rawSignal/amp*127)+127)
    return dacSignal

def fast(seg, bits, cyc, mw_delay, mw_duration, amp):
    t = np.arange(seg, step=1)
    omegaSin = 2 * np.pi * cyc
    pre, pulse, post = int((mw_delay-mw_duration)*seg//1e6), int(round(mw_duration*seg/1e6)), int(seg-mw_delay*seg//1e6)
    pre, pulse, post = np.zeros(pre, dtype=int), np.ones(pulse, dtype=int), np.zeros(post, dtype=int)
    print(pre.size, pulse.size, post.size)
    sq = np.concatenate((pre, pulse, post))
    sn = np.sin(omegaSin*t/seg)
    rawSignal = sq * amp * sn
    dacSignal = np.uint8((rawSignal/amp*127)+127)
    del t, sq, sn, rawSignal
    return dacSignal

if __name__ == '__main__':
    args, N = (8998848*2, 8, 5999232, 250000, 5, 1), 1
    s, f = slow(*args), fast(*args)
    print(all(s == f))
    run('[slow(*args) for _ in range(N)]', sort='cumtime')
    run('[fast(*args) for _ in range(N)]', sort='cumtime')
