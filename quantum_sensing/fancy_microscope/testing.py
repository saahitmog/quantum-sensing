import sys
import numpy as np
from memory_profiler import profile
import cProfile

#@profile
def sine(segmentLength, sinCycles, amp):

    t = np.arange(segmentLength, step=1)
    omegaSin = 2 * np.pi * sinCycles
    sq = np.concatenate((np.ones(int(segmentLength/2), dtype=int), np.zeros(int(segmentLength/2), dtype=int)))
    sn = np.sin(omegaSin*t/segmentLength)
    rawSignal = sq * amp * sn
    dacSignal = np.uint8((rawSignal/amp*127)+127)
    del t, sq, sn, rawSignal
    return dacSignal

@profile
def ESRSweep(freqs):
    seg = 8998848
    waveform = np.array([], dtype=np.uint8)
    for f in freqs:
        waveform = np.append(waveform, sine(seg, f*seg, 1))
    return waveform

#@profile
def test(N):
    #x = np.linspace(0, N-1, N)
    #y = np.array(range(N))
    z = np.arange(N, step=1)

if __name__ == '__main__':
    #cProfile.run('sinePulse(8998848, 8998848*3, 1)', sort='cumtime')
    #cProfile.run('')
    freqs = np.linspace(2.5, 3, 100)
    result = ESRSweep(freqs)

    #cProfile.run('ESRSweep(np.linspace(2.5, 3, 100))')