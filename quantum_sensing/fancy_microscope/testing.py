#import AWGcontrol as AWGctrl
import numpy as np, multiprocessing as mp
import matplotlib.pyplot as plt
from cProfile import run
from memory_profiler import profile
import time

@profile
def orig(num):

    t0 = time.time()
    duration = 0.0005
    segmentLength = 8998848
    segmentLength = int((2*duration/0.001)*segmentLength)
    segmentLength = int(segmentLength/8)

    waveform = np.zeros(segmentLength)

    duration = 500
    delay = 400_000
    tot = 500_000
    duration2 = 100

    
    t1 = time.time()
    for i in range(int((delay-duration2)*segmentLength/1e6), int(delay*segmentLength/1e6)):
        waveform[i] += 2

    for i in range(int(tot*segmentLength/1e6)+int((delay-duration2)*segmentLength/1e6), int(tot*segmentLength/1e6)+int(delay*segmentLength/1e6)):
        waveform[i] += 2

    for i in range(0, segmentLength):
        waveform[i] += 4

    t2 = time.time()

    totalWaveform = []
    for i in range(num):
        totalWaveform = np.append(totalWaveform, waveform)

    t3 = time.time()

    for i in range(0, int(duration*segmentLength/1e6)):
        totalWaveform[i] += 1

    markerWave = np.uint8(totalWaveform)
    t4 = time.time()
    print(t1-t0, t2-t1, t3-t2, t4-t3)
    return markerWave

@profile
def fast(num):
    t0 = time.time()
    duration = 0.0005
    segmentLength = 8998848
    segmentLength = int((2*duration/0.001)*segmentLength)//8
    #segmentLength = int(segmentLength/8)

    waveform = np.zeros(segmentLength, dtype=np.uint8)

    duration = 500
    delay = 400_000
    tot = 500_000
    duration2 = 100

    
    t1 = time.time()
    for i in range(int((delay-duration2)*segmentLength/1e6), int(delay*segmentLength/1e6)):
        waveform[i] += 2

    for i in range(int(tot*segmentLength/1e6)+int((delay-duration2)*segmentLength/1e6), int(tot*segmentLength/1e6)+int(delay*segmentLength/1e6)):
        waveform[i] += 2

    '''for i in range(0, segmentLength):
        waveform[i] += 4'''
    waveform += 4

    t2 = time.time()

    totalWaveform = np.array([waveform]*num, dtype=np.uint8).flatten()

    t3 = time.time()

    for i in range(0, int(duration*segmentLength/1e6)):
        totalWaveform[i] += 1

    markerWave = np.uint8(totalWaveform)
    del totalWaveform

    t4 = time.time()
    print(t1-t0, t2-t1, t3-t2, t4-t3)
    return markerWave

if __name__ == '__main__':
    #run('orig(100)', sort='cumtime')
    #run('fast(100)', sort='cumtime')
    fast(500)
    #orig(100)
