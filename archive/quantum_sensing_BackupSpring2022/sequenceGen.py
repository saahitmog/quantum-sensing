import os
import sys
import inspect
import sys
import clr
import ctypes
import time
import numpy as np
from scipy import signal as sg
import matplotlib.pyplot as plt

sys.path.append('..')

from taborTools.instFunction import *
from taborTools.waveFunction import *

def openInstrument():
    admin = loadDLL()
    slotId = getSlotId(admin)
    instId = None
    if not slotId:
        print("Invalid choice!")
    else:
        inst = admin.OpenInstrument(slotId) 
        if  not inst:
            print("Failed to Open instrument with slot-Id {0}".format(slotId))
            print("\n")
        else:
            instId = inst.InstrId
    return instId, admin, inst

def closeInstrument(instId, admin):
    rc = admin.CloseInstrument(instId)
    Validate(rc,__name__,inspect.currentframe().f_back.f_lineno)

def adminClose(admin):
    rc = admin.Close()
    Validate(rc,__name__,inspect.currentframe().f_back.f_lineno)

def intializeInstrument(inst, sclk):
    trig_lev = getSclkTrigLev(inst)
    
    # Module 1
    SendScpi(inst, ":INST:ACTive 1")
    
    # get hw option
    SendScpi(inst, "*OPT?")
    # reset - must!
    SendScpi(inst, "*RST")
    # set sampling DAC freq.
    SendScpi(inst, ":FREQ:RAST {0}".format(sclk))
    # delete all segments in RAM
    SendScpi(inst, ":TRAC:DEL 1")
    # define user mode
    SendScpi(inst, ":SOUR:FUNC:MODE ARB")
    # common segment defs
    SendScpi(inst, ":TRAC:DEF:TYPE NORM")
    
    # select channel
    SendScpi(inst, ":INST:CHAN 1")
    # Vpp for output = 1V
    SendScpi(inst, ":SOUR:VOLT 1.0")
    # Arbitrary waveform generation, no trigger
    SendScpi(inst, ":INIT:CONT ON") 


def generateSignal(inst, sclk, waveform, segNum=1):
    segmentLength = len(waveform)

    waveArry = []
    for i in range(0, segmentLength):
        waveArry.append(waveform[i])
        
    f = open("temp.seg", 'wb')
    binary_format = bytearray(waveArry)
    f.write(binary_format)
    f.close()
    
    res = SendScpi(inst, ":TRACe:DEF {0},{1}".format(segNum, segmentLength))
    res = SendScpi(inst, ":TRACe:SEL {0}".format(segNum)) 
    start_time = time.time() 
    res = SendBinScpi(inst, ":TRAC:FNAM 0 , #", "temp.seg")
    print("--- bin downloading %i points, time: %s seconds ---" % (segmentLength, time.time() - start_time) )
    os.remove("temp.seg")

    # sel segment 1
    SendScpi(inst, ":SOUR:FUNC:SEG {0}".format(segNum)) 
    # connect ouput
    SendScpi(inst, ":OUTP ON")

def sinePulse(segmentLength, bits, squareCycles, sinCycles, duty, amp):
    
    time = np.linspace(0, segmentLength-1, segmentLength)
    omegaSquare = 2 * np.pi * squareCycles
    omegaSin = 2 * np.pi * sinCycles
    rawSignal = ((sg.square(omegaSquare*time/segmentLength, duty)+1)/2) *amp*np.sin(omegaSin*time/segmentLength)

    dacSignal = scaleWaveform(rawSignal, bits)

    return(dacSignal);
    
def makeESRseq(t_duration, mw_duration, freq):
    #t_duration is total duration
    #mw_duration is microwave duration
    #Frequency (MHz) 10-1000 Integer val
    segmentLength = 2499968
    cycles = int(freq * segmentLength * 1e6 / 9e9)
    squares = int((1/(t_duration / 1e6)) * segmentLength / 9e9)
    duty = mw_duration / t_duration
    return sinePulse(segmentLength, 8, squares, cycles, duty, 1)

def makeReadoutDelaySweep(t_readoutDelay, t_AOM):
    return
def makeRabiSeq(t_uW,t_AOM,t_readoutDelay):
    return
def makeT1Seq(t_delay,t_AOM,t_readoutDelay,t_pi):
    return
def makeT2Seq(t_delay,t_AOM,t_readoutDelay,t_pi,IQpadding, numberOfPiPulses):
    return
def makeXY8seq(t_delay,t_AOM,t_readoutDelay,t_pi,IQpadding, numberOfRepeats):
    return
def makecorrelationSpectSeq(t_delay_betweenXY8seqs,t_delay, t_AOM,t_readoutDelay,t_pi,IQpadding,numberOfRepeats):
    return
def makeCPMGpulses(start_delay,numberOfPiPulses,t_delay,t_pi, t_piby2,IQpadding):
    return
def makeXY8pulses(start_delay,numberOfRepeats,t_delay,t_pi, t_piby2,IQpadding):
    return