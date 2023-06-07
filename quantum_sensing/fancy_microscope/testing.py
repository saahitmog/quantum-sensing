import sys, time
import numpy as np
from memory_profiler import profile
import cProfile
from multiprocessing import Pool

def timer(func):
    def wrapper(*args, **kwargs):
        t1 = time.process_time()
        result = func(*args, **kwargs)
        t2 = time.process_time()
        print(f'{(t2-t1):.4f} s')
        return result
    return wrapper

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

@timer
@profile
def ESRSweep(freqs):
    seg = 8998848
    waveform = np.array([], dtype=np.uint8)
    for f in freqs:
        waveform = np.append(waveform, sine(seg, f*seg, 1))
    return waveform

@timer
@profile
def ESRSweepfast(freqs):
    seg = 8998848
    args = np.array([np.full(freqs.shape, seg), seg*freqs, np.ones(freqs.shape)]).T
    with Pool() as pool:
        waveform = np.array(pool.starmap(sine, args), dtype=np.uint8).flatten()   
    return waveform

if __name__ == '__main__':
    #cProfile.run('sinePulse(8998848, 8998848*3, 1)', sort='cumtime')
    #cProfile.run('')
    #freqs = np.linspace(2.5, 3, 100)
    #result = ESRSweep(freqs)
    freqs = np.linspace(2.5, 3, 500)
    #cProfile.run('ESRSweep(np.linspace(2.5, 3, 100))')
    slow = ESRSweep(freqs)
    print(slow.nbytes)
    
    fast = ESRSweepfast(freqs)
    print(fast.nbytes)
