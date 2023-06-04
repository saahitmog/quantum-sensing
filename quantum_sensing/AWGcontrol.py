# import PBcontrol as PBctl
# import sequenceControl as seqCtl
#import ESRconfig as ESR
# from spinapi import *
from ctypes import *
import numpy as np
import sys
# import DAQ_Analog as DAQ #NOTE THIS CHANGE FROM PHOTODIODE CODE
# import SRScontrol as SRSctl
# from PBinit import initPB
import time
import copy
import pandas as pd

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style

import os
import inspect
import clr
import array
from System import Array, Char, Int16
from scipy import constants
from scipy import signal as sg
import time

datapath = os.path.dirname(sys.argv[0])
maxScpiResponse = 65535

if (datapath):
    datapath = datapath + "\\"
print(datapath)

def OnLoggerEvent(sender, e):
    del sender
    print(e.Message.Trim())
    if (e.Level <= LogLevel.Warning):  # @UndefinedVariable
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        print(e.Message.Trim())
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~")


def Validate(rc, condExpr, funcName="", lineNumber=0):
    _ = condExpr

    # cond = (rc == 0)

    if rc != 0:
        errMsg = "Assertion \"{0}\" Failed at line {1} of {2}."
        errMsg = errMsg.format(rc, lineNumber, funcName)
        raise Exception(errMsg)

def getSlotId(admin):
    try:
        if admin.IsOpen():
            rc = admin.Close()
            Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)

        rc = admin.Open()
        Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)

        slotIds = admin.GetSlotIds()
        n = 0
        for i in range(0, slotIds.Length, 1):
            slotId = slotIds[i]
            slotInfo = admin.GetSlotInfo(slotId)
            if slotInfo:
                if not slotInfo.IsDummySlot:
                    n = n + 1
                    print(("{0}. Slot-ID {1} [chassis {2}, slot {3}], "
                           "IsDummy={4}, IsInUse={5}, IDN=\'{6}\'").
                          format(i + 1,
                                 slotId,
                                 slotInfo.ChassisIndex,
                                 slotInfo.SlotNumber,
                                 'Yes' if slotInfo.IsDummySlot != 0 else 'No',
                                 'Yes' if slotInfo.IsSlotInUse != 0 else 'No',
                                 slotInfo.GetIdnStr()))
                else:
                    dummy = 1
                    # print("{0}. Slot-ID {1} - Failed to acquire Slot Info".
                    # .format(i + 1,slotId))

        if n == 1:
            sel = slotIds[0]
        else:
            sel = input("Please select slot-Id:")
        slotId = np.uint32(sel)
    except Exception as e:  # pylint: disable=broad-except
        print(e)
    return slotId


def loadDLL():

    # Load .NET DLL into memory
    # The R lets python interpret the string RAW
    # So you can put in Windows paths easy
    # clr.AddReference(R'D:\Projects\Alexey\ProteusAwg\PyScpiTest\TEPAdmin.dll')

    #winpath = os.path.join(os.environ['WINDIR'], 'System32')
  
    winpath = R'C:\Windows\System32'

    winpath = os.path.join(winpath, 'TEPAdmin.dll')

    clr.AddReference(winpath)

    # pylint: disable=import-error
    from TaborElec.Proteus.CLI.Admin import CProteusAdmin  # @UnresolvedImport

    from TaborElec.Proteus.CLI.Admin import IProteusInstrument  # @UnusedImport @UnresolvedImport @IgnorePep8

    return CProteusAdmin(OnLoggerEvent)


def SendBinScpi(inst, prefix, path, query_err=False):

    err_code, resp_str = -1, ''
    try:
        print(prefix)
        inBinDat = bytearray(path, "utf8")
        inBinDatSz = np.uint64(len(inBinDat))
        DummyParam = np.uint64(0)
        res = inst.WriteBinaryData(prefix, inBinDat, inBinDatSz, DummyParam)

        err_code = int(res.ErrCode)
        resp_str = str(res.RespStr).strip()

        if 0 != err_code:
            print("Error {0} ({1})".format(err_code, resp_str))
        elif len(resp_str) > 0:
            print("{0}".format(resp_str))
        if query_err:
            err = inst.SendScpi(':SYST:ERR?')
            if not err.RespStr.startswith('0'):
                print(err.RespStr)
                err = inst.SendScpi('*CLS')

    except Exception as e:  # pylint: disable=broad-except
        print(e)

    return err_code, resp_str


def SendScpi(inst, line, query_err=False, print_line=True):

    err_code, resp_str = -1, ''
    try:
        if print_line:
            print(line)
        line = line + "\n"
        res = inst.SendScpi(str(line))
        err_code = int(res.ErrCode)
        resp_str = str(res.RespStr).strip()

        if 0 != err_code:
            if not print_line:
                print(line.strip())
            print("Error {0} - ({1})".format(err_code, resp_str))
        elif len(resp_str) > 0 and print_line:
            print("{0}".format(resp_str))
        if query_err:
            err = inst.SendScpi(':SYST:ERR?')
            if not err.RespStr.startswith('0'):
                print(err.RespStr)
                err = inst.SendScpi('*CLS')
    except Exception as e:  # pylint: disable=broad-except
        print(e)

    return err_code, resp_str
    
def scaleWaveform(rawSignal, model):

    if model == "P9082M":  # 9GS/s
        bits = 8
        wpt_type = np.uint8
    else:  # 2GS/s or 1.25GS/s models
        bits = 16
        wpt_type = np.uint16

    maxSig = max(rawSignal)
    verticalScale = ((pow(2, bits))/2)-1
    vertScaled = (rawSignal/maxSig) * verticalScale
    dacSignal = (vertScaled + verticalScale)
    dacSignal = dacSignal.astype(wpt_type)
    
    if max(dacSignal) > 256:
        dacSignal16 = []
        for i in range(0,len(dacSignal)*2):
            dacSignal16.append(0)
            
        j=0
        for i in range(0,len(dacSignal)):
            dacSignal16[j] = dacSignal[i] & 0x0f
            dacSignal16[j+1] = dacSignal[i] >> 8
            j=j+2
        dacSignal = dacSignal16
    
    return(dacSignal);
    
def pulseWave(segmentLength, cycles, onTime):
    
    segmentLengthOn = int(onTime * segmentLength)
    segmentLengthOff = int((1-onTime) * segmentLength)
    time = np.linspace(0, segmentLengthOn-1, segmentLengthOn)
    omega = 2 * np.pi * cycles
    rawSignalOn = np.sin(omega*time/segmentLength)
    rawSignalOff = np.array(np.zeros(segmentLengthOff)) 
    rawSignal = np.concatenate([rawSignalOn,rawSignalOff])
    
    return(rawSignal);

def instrumentSetup(inst, sampleRateDAC = 9E9):
    
    query_syst_err = True      
    
    res = SendScpi(inst, ":SYST:INF:MODel?")
    
    model = res[1]

    # Module 1
    SendScpi(inst, ":INST:ACTive 1", query_syst_err)

    # get hw option
    SendScpi(inst, "*IDN?")
    SendScpi(inst, "*OPT?")
    # reset - must!
    SendScpi(inst, "*CLS", query_syst_err)
    # reset - must!
    SendScpi(inst, "*RST", query_syst_err)

    # set sampling DAC freq.
    SendScpi(inst, ":FREQ:RAST {0}".format(sampleRateDAC), query_syst_err)  
    
    #^^^^ set once

def instrumentCallsFast(inst, waveform, vpp=0.001, offset=0):
    query_syst_err = True  
    
    dacSignal = waveform
    
    # ---------------------------------------------------------------------
    # DAC functions CH 1 
    # ---------------------------------------------------------------------

    # select channel
    #SendScpi(inst, ":INST:CHAN 1", query_syst_err)

    # load I waveform into instrument
    segNum = 1
    SendScpi(inst, ":TRACe:DEF {0},{1}".format(segNum, len(dacSignal)), query_syst_err)
    SendScpi(inst, ":TRACe:SEL {0}".format(segNum), query_syst_err)

    prefix = ':TRAC:DATA 0,#'
    print(prefix, end=' .. ')

    res = inst.WriteBinaryData(prefix, dacSignal.tobytes())
    Validate(res.ErrCode, __name__, inspect.currentframe().f_back.f_lineno)

    res = SendScpi(inst, ":SYST:ERR?", False, False)
    print(res[1])

    # Vpp for output
    #SendScpi(inst, ":VOLT:OFFS 0")
    #SendScpi(inst, ":VOLT:OFFS?")
    SendScpi(inst, ":SOUR:VOLT {0}".format(vpp))
    #SendScpi(inst, ":VOLT?")

    # sel segment 1 - play I
    SendScpi(inst, ":SOUR:FUNC:MODE:SEGM {0}".format(segNum), query_syst_err) 
    
    trig_lev = 128
    enableTrigger(inst, trig_lev, 1)

    # connect ouput
    #SendScpi(inst, ":OUTP ON", query_syst_err)

    #MARKER CODE >>>>
    # SendScpi(inst, ":MARK OFF")
      
    # # enble marker 1 CH 1
    # offTime = offset
    # onTime = int(len(dacSignal)/8)-offset
    # markerWave = []
    # for i in range(0,offTime):
    #     markerWave.append(0)
    # for i in range(0,onTime):
    #     markerWave.append(1)  
    # markerWave = np.uint8(markerWave)
       
    # prefix = ':MARK:DATA 0,#'
    # print(prefix, end=' .. ')
    # res = inst.WriteBinaryData(prefix, markerWave.tobytes())
    # Validate(res.ErrCode, __name__, inspect.currentframe().f_back.f_lineno)

    # SendScpi(inst, ":MARK:VOLT:PTOP 1")
    # SendScpi(inst, ":MARK:SEL 1")
    # SendScpi(inst, ":MARK ON")



def instrumentCalls(inst, waveform, vpp=0.001, offset=0):
    query_syst_err = True  
    
    dacSignal = waveform
    
    # ---------------------------------------------------------------------
    # DAC functions CH 1 
    # ---------------------------------------------------------------------

    # select channel
    SendScpi(inst, ":INST:CHAN 1", query_syst_err)

    # load I waveform into instrument
    segNum = 1
    SendScpi(inst, ":TRACe:DEF {0},{1}".format(segNum, len(dacSignal)), query_syst_err)
    SendScpi(inst, ":TRACe:SEL {0}".format(segNum), query_syst_err)

    prefix = ':TRAC:DATA 0,#'
    print(prefix, end=' .. ')

    res = inst.WriteBinaryData(prefix, dacSignal.tobytes())
    Validate(res.ErrCode, __name__, inspect.currentframe().f_back.f_lineno)

    res = SendScpi(inst, ":SYST:ERR?", False, False)
    print(res[1])

    # Vpp for output
    SendScpi(inst, ":VOLT:OFFS 0")
    #SendScpi(inst, ":VOLT:OFFS?")
    SendScpi(inst, ":SOUR:VOLT {0}".format(vpp))
    #SendScpi(inst, ":VOLT?")

    # sel segment 1 - play I
    SendScpi(inst, ":SOUR:FUNC:MODE:SEGM {0}".format(segNum), query_syst_err) 
    
    trig_lev = 128
    enableTrigger(inst, trig_lev, 1)

    # connect ouput
    SendScpi(inst, ":OUTP ON", query_syst_err)

    #MARKER CODE >>>>
    SendScpi(inst, ":MARK OFF")
      
    # enble marker 1 CH 1
    offTime = offset
    onTime = int(len(dacSignal)/8)-offset
    markerWave = []
    for i in range(0,offTime):
        markerWave.append(0)
    for i in range(0,onTime):
        markerWave.append(1)  
    markerWave = np.uint8(markerWave)
       
    prefix = ':MARK:DATA 0,#'
    print(prefix, end=' .. ')
    res = inst.WriteBinaryData(prefix, markerWave.tobytes())
    Validate(res.ErrCode, __name__, inspect.currentframe().f_back.f_lineno)

    SendScpi(inst, ":MARK:VOLT:PTOP 1")
    SendScpi(inst, ":MARK:SEL 1")
    SendScpi(inst, ":MARK ON")

def enableTrigger(inst, trig_lev, trig_channel):
    SendScpi(inst, ":TRIG:SOUR:ENAB TRG{0}".format(trig_channel)) # Set tigger enable signal to TRIG1 (CH specific)
    SendScpi(inst, ":TRIG:SEL TRG1") # Select trigger for programming (CH specific)
    SendScpi(inst, ":TRIG:LEV 0.1") # Set trigger level
    SendScpi(inst, ":TRIG:COUN 1") # Set number of waveform cycles (1) to generate (CH specific)
    SendScpi(inst, ":TRIG:IDLE DC") # Set output idle level to DC (CH specific)
    SendScpi(inst, ":TRIG:IDLE:LEV {0}".format(trig_lev)) # Set DC level in DAC value (CH specific)
    SendScpi(inst, ":TRIG:STAT ON") # Enable trigger state (CH specific)
    SendScpi(inst, ":INIT:CONT OFF") # Enable trigger mode (CH specific)
    SendScpi(inst, ":TRIG:GATE:STAT OFF") #Disable trigger gated mode

    # SendScpi(inst, ":TRIG:SOUR:ENAB TRG{0}".format(trig_channel)) # Set tigger enable signal to TRIG1 (CH specific)
    # SendScpi(inst, ":TRIG:SEL TRG1") # Select trigger for programming (CH specific)
    # #SendScpi(inst, ":TRIG:LEV 0.5") # Set trigger level
    # SendScpi(inst, ":TRIG:COUN 0") # Set number of waveform cycles (1) to generate (CH specific)
    # SendScpi(inst, ":TRIG:IDLE DC") # Set output idle level to DC (CH specific)
    # SendScpi(inst, ":TRIG:IDLE:LEV {0}".format(trig_lev)) # Set DC level in DAC value (CH specific)
    # SendScpi(inst, ":TRIG:STAT ON") # Enable trigger state (CH specific)
    # SendScpi(inst, ":INIT:CONT OFF") # Enable trigger mode (CH specific)
    # SendScpi(inst, ":TRIG:GATE:STAT OFF") #Disable trigger gated mode

def sinePulse(segmentLength, bits, squareCycles, sinCycles, duty, amp):
    
    time = np.linspace(0, segmentLength-1, segmentLength)
    omegaSquare = 2 * np.pi * squareCycles
    omegaSin = 2 * np.pi * sinCycles
    rawSignal = ((sg.square(omegaSquare*time/segmentLength, duty)+1)/2) *amp*np.sin(omegaSin*time/segmentLength)

    dacSignal = scaleWaveform(rawSignal, "P9082M")

    return(dacSignal);

def squareWave(segmentLength):
    time = np.linspace(0, segmentLength-1, segmentLength)
    print(sg.square(time))
    return scaleWaveform(sg.square(time),"P9082M")


def sinePulseOffset(segmentLength, bits, squareCycles, sinCycles, duty, amp, offset):
    time = np.linspace(0, segmentLength-1, segmentLength)
    omegaSquare = 2 * np.pi * squareCycles
    omegaSin = 2 * np.pi * sinCycles
    squareSignal = np.roll((sg.square(omegaSquare*time/segmentLength, duty)+1)/2, offset)
    squareSignal[:offset] = [0] * offset
    rawSignal = (squareSignal*amp*np.sin(omegaSin*time/segmentLength))
    
    dacSignal = scaleWaveform(rawSignal, "P9082M")

    return(dacSignal);

def makeESRseq(inst, t_duration, mw_duration, startFreq, endFreq, vpp = 0.001, freqStep=1):
    #t_duration is total duration
    #mw_duration is microwave duration
    #Frequency (GHz) 10-1000 Integer val
    # freq = startFreq
    # while freq < endFreq:
    #     segmentLength = 2499968
    #     cycles = int(freq * segmentLength * 1e6 / 9e9)
    #     squares = int((1/(t_duration / 1e6)) * segmentLength / 9e9)
    #     duty = mw_duration / t_duration
    #     instrumentCalls(inst, sinePulse(segmentLength, 8, squares, cycles, duty, 1))
    #     freq += freqStep
    freq = startFreq
    instrumentSetup(inst)
    while freq <= endFreq:
        segmentLength = 4999936
        cycles = int(freq * segmentLength * 1e9 / 9e9)
        squares = int((1/(t_duration / 1e6)) * segmentLength / 9e9)
        duty = mw_duration / t_duration
        print('Frequency: {0} GHz'.format(freq))
        instrumentCalls(inst, sinePulse(segmentLength, 8, squares, cycles, duty, 1), vpp)
        freq += freqStep

def makeSingleESRSeqFast(inst, duration, freq, vpp = 0.001):
    segmentLength = 4999936
    segmentLength = 8998848 #this segment length is optimized for 1kHz trigger signal
    cycles = int(freq * segmentLength * 1e9 / 9e9)
    squares = int((1/(duration / 1e6)) * segmentLength / 9e9)
    duty = 0.5
    print('Frequency: {0} GHz'.format(freq))
    instrumentCallsFast(inst, sinePulse(segmentLength, 8, squares, cycles, duty, 1), vpp)


def makeSingleESRSeq(inst, duration, freq, vpp = 0.001):
    segmentLength = 4999936
    segmentLength = 8998848 #this segment length is optimized for 1kHz trigger signal
    cycles = int(freq * segmentLength * 1e9 / 9e9)
    squares = int((1/(duration / 1e6)) * segmentLength / 9e9)
    duty = 0.5
    print('Frequency: {0} GHz'.format(freq))
    instrumentCalls(inst, sinePulse(segmentLength, 8, squares, cycles, duty, 1), vpp)

def makeReadoutDelaySweep(inst, t_duration, mw_duration, freq, delayStart, delayStop, vpp = 0.001, delayStep=0.1):
    #delay in microseconds
    instrumentSetup(inst)
    t_readoutDelay = delayStart
    while t_readoutDelay <= delayStop:
        tot_duration = t_duration + t_readoutDelay
        segmentLength = 4999936
        cycles = int(freq * segmentLength * 1e9 / 9e9)
        squares = int((1/(tot_duration / 1e6)) * segmentLength / 9e9)
        duty = mw_duration / tot_duration
        offset = int(2*np.pi*t_readoutDelay/tot_duration)
        print('Delay: {0} us'.format(t_readoutDelay))
        instrumentCalls(inst, sinePulseOffset(segmentLength, 8, squares, cycles, duty, 1, offset), vpp)
        t_readoutDelay += delayStep
        time.sleep(5)

def makeRabiSeq(inst, t_duration, freq, mwStart, mwStop, vpp = 0.001, mwStep=0.1):
    #delay in microseconds
    instrumentSetup(inst)
    mw_duration = mwStart
    while mw_duration <= mwStop:
        segmentLength = 4999936
        segmentLength = 8998848 #this segment length is optimized for 1kHz trigger signal
        cycles = int(freq * segmentLength * 1e9 / 9e9)
        squares = int((1/(t_duration / 1e6)) * segmentLength / 9e9)
        duty = mw_duration / t_duration
        # offset = int(2*np.pi*t_readoutDelay/t_duration)
        offset = 0
        print('MW duration: {0} us'.format(mw_duration))
        instrumentCalls(inst, sinePulseOffset(segmentLength, 8, squares, cycles, duty, 1, offset), vpp)
        mw_duration += mwStep
        time.sleep(5)

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
