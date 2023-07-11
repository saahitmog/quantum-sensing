import sys, time, math, os, inspect, clr
import numpy as np
from multiprocessing import Pool
from scipy import signal as sg
from ctypes import *
from utils import *

if __name__ == '__main__':
    datapath = os.path.dirname(sys.argv[0])
    maxScpiResponse = 65535

    if datapath: datapath += "\\"
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
        # if print_line:
        #     print(line)
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
    SendScpi(inst, ":OUTP ON", query_syst_err)

def makeMarker(inst, segmentLength):
    #MARKER CODE >>>>
    SendScpi(inst, ":MARK OFF")
    SendScpi(inst, ":MARK:SEL 3")
      
    # enble marker 1 CH 1
    segmentLength=(int(segmentLength/8))
    time =  np.linspace(0, segmentLength-1, segmentLength)
    markerWave = np.zeros(segmentLength)
    for i in range(0, int(segmentLength/2)):
        markerWave[i] += 4
    markerWave = np.uint8(markerWave)
       
    prefix = ':MARK:DATA 0,#'
    # print(prefix, end=' .. ')
    res = inst.WriteBinaryData(prefix, markerWave.tobytes())
    Validate(res.ErrCode, __name__, inspect.currentframe().f_back.f_lineno)

    SendScpi(inst, ":MARK:VOLT:PTOP 1.2")
    # SendScpi(inst, ":MARK:SEL 1")
    SendScpi(inst, ":MARK ON")

def makeESRMarker(inst, segmentLength):
    segmentLength = int(segmentLength/8)
    #MARKER CODE >>>>
    SendScpi(inst, ":MARK OFF")
    SendScpi(inst, ":MARK:SEL 1")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")
    # SendScpi(inst, ":MARK:OFFS 0")

    #enble marker 1 CH 1
    time = np.linspace(0, segmentLength-1, segmentLength)
    waveform = np.zeros(segmentLength)

    duration = 500

    for i in range(0, int(duration*segmentLength/1e6)):
        waveform[i] += 1

    delay = 400000
    tot = 500000
    duration2 = 100

    for i in range(int((delay-duration2)*segmentLength/1e6), int(delay*segmentLength/1e6)):
        waveform[i] += 2

    for i in range(int(tot*segmentLength/1e6)+int((delay-duration2)*segmentLength/1e6), int(tot*segmentLength/1e6)+int(delay*segmentLength/1e6)):
        waveform[i] += 2
    

    for i in range(0, segmentLength):
        waveform[i] += 4

    markerWave = np.uint8(waveform)
    # print(markerWave.tobytes()[:1000])
    
    prefix = ':MARK:DATA 0,#'
    # print(prefix, end=' .. ')
    res = inst.WriteBinaryData(prefix, markerWave.tobytes())
    # Validate(res.ErrCode, __name__, inspect.currentframe().f_back.f_lineno)

    # res = SendScpi(inst, ":SYST:ERR?", False, False)
    # print(res[1])

    # SendScpi(inst, ":MARK:SEL?")

    SendScpi(inst, ":MARK:VOLT:PTOP 1.2")
    SendScpi(inst, ":MARK ON")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")

    SendScpi(inst, ":MARK:SEL 2")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")
    SendScpi(inst, ":MARK:VOLT:PTOP 0.5")
    SendScpi(inst, ":MARK ON")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")
    SendScpi(inst, ":MARK:SEL 3")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")
    SendScpi(inst, ":MARK:VOLT:PTOP 1.2")
    SendScpi(inst, ":MARK ON")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")

def makeRabiMarker(inst, segmentLength):
    segmentLength = int(segmentLength/8)
    #MARKER CODE >>>>
    SendScpi(inst, ":MARK OFF")
    SendScpi(inst, ":MARK:SEL 1")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")
    # SendScpi(inst, ":MARK:OFFS 0")



    #enble marker 1 CH 1
    waveform = np.zeros(segmentLength)

    duration = 300

    for i in range(0, int(duration*segmentLength/2e6)):
        waveform[i] += 1

    delay = 1000000
    duration2 = 500000

    for i in range(int((delay-duration2)*segmentLength/2e6), int(delay*segmentLength/2e6)):
        waveform[i] += 4

    for i in range(int((2*delay-duration2)*segmentLength/2e6), int(2*delay*segmentLength/2e6)):
        waveform[i] += 4
    
    # delay = 1000000
    # duration = 300
    delay = 900000
    tot = 1000000
    duration = 100

    for i in range(int((delay-duration)*segmentLength/2e6), int(delay*segmentLength/2e6)):
        waveform[i] += 2

    for i in range(int(tot*segmentLength/2e6)+int((delay-duration)*segmentLength/2e6), int(tot*segmentLength/2e6)+int(delay*segmentLength/2e6)):
        waveform[i] += 2

    markerWave = np.uint8(waveform)
    # print(markerWave.tobytes()[:1000])
    
    prefix = ':MARK:DATA 0,#'
    # print(prefix, end=' .. ')
    res = inst.WriteBinaryData(prefix, markerWave.tobytes())
    Validate(res.ErrCode, __name__, inspect.currentframe().f_back.f_lineno)

    # res = SendScpi(inst, ":SYST:ERR?", False, False)
    # print(res[1])

    # SendScpi(inst, ":MARK:SEL?")

    SendScpi(inst, ":MARK:VOLT:PTOP 1.2")
    SendScpi(inst, ":MARK ON")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")

    SendScpi(inst, ":MARK:SEL 2")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")
    SendScpi(inst, ":MARK:VOLT:PTOP 0.5")
    SendScpi(inst, ":MARK ON")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")
    SendScpi(inst, ":MARK:SEL 3")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")
    SendScpi(inst, ":MARK:VOLT:PTOP 1.2")
    SendScpi(inst, ":MARK ON")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")

def makeT1Marker(inst, segmentLength, t_delay, t_readoutDelay, t_AOM):
    segmentLength = int(segmentLength/8)
    #MARKER CODE >>>>
    SendScpi(inst, ":MARK OFF")
    SendScpi(inst, ":MARK:SEL 1")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")
    # SendScpi(inst, ":MARK:OFFS 0")



    #enble marker 1 CH 1
    waveform = np.zeros(segmentLength)

    duration = 300

    for i in range(0, int(duration*segmentLength/1e6)):
        waveform[i] += 1

    for i in range(int((t_delay)*segmentLength/1e6), int((t_delay+t_AOM)*segmentLength/1e6)):
        waveform[i] += 4

    for i in range(int((2*t_delay+t_AOM)*segmentLength/1e6), int((2*t_delay+2*t_AOM)*segmentLength/1e6)):
        waveform[i] += 4

    for i in range(int((t_delay+t_readoutDelay)*segmentLength/1e6), int((t_delay+t_readoutDelay+duration)*segmentLength/1e6)):
        waveform[i] += 2

    for i in range(int((2*t_delay+t_AOM+t_readoutDelay)*segmentLength/1e6), int((2*t_delay+t_AOM+t_readoutDelay+duration)*segmentLength/1e6)):
        waveform[i] += 2

    markerWave = np.uint8(waveform)
    # print(markerWave.tobytes()[:1000])
    
    prefix = ':MARK:DATA 0,#'
    # print(prefix, end=' .. ')
    res = inst.WriteBinaryData(prefix, markerWave.tobytes())
    Validate(res.ErrCode, __name__, inspect.currentframe().f_back.f_lineno)

    res = SendScpi(inst, ":SYST:ERR?", False, False)
    print(res[1])

    # SendScpi(inst, ":MARK:SEL?")

    SendScpi(inst, ":MARK:VOLT:PTOP 1.2")
    SendScpi(inst, ":MARK ON")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")

    SendScpi(inst, ":MARK:SEL 2")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")
    SendScpi(inst, ":MARK:VOLT:PTOP 0.5")
    SendScpi(inst, ":MARK ON")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")
    SendScpi(inst, ":MARK:SEL 3")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")
    SendScpi(inst, ":MARK:VOLT:PTOP 1.2")
    SendScpi(inst, ":MARK ON")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")
    
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

    #print('Setup segment:', currtime-lasttime, ' seconds')

    with timer('------> AWG Write: '): res = inst.WriteBinaryData(prefix, dacSignal.tobytes())
    #print('Write segment:', currtime-lasttime, ' seconds')
    #print(f'Write speed: {dacSignal.nbytes * 1e-9  / (currtime-lasttime)} GB/s')

    # Validate(res.ErrCode, __name__, inspect.currentframe().f_back.f_lineno)

    # res = SendScpi(inst, ":SYST:ERR?", False, False)
    # print(res[1])

    # lasttime=currtime
    # currtime=time.time()
    # print('Validate error:', currtime-lasttime, ' seconds')

    # Vpp for output
    # SendScpi(inst, ":VOLT:OFFS 0")
    # SendScpi(inst, ":VOLT:OFFS?")
    SendScpi(inst, ":SOUR:VOLT {0}".format(vpp))
    #SendScpi(inst, ":VOLT?")

    # sel segment 1 - play I
    SendScpi(inst, ":SOUR:FUNC:MODE:SEGM {0}".format(segNum), query_syst_err) 
    

    # SendScpi(inst, ":TRIG:STAT OFF") # Enable trigger state (CH specific)
    # SendScpi(inst, ":INIT:CONT ON") # Enable trigger mode (CH specific)
    # trig_lev = 128
    # enableTrigger(inst, trig_lev, 1)

    # connect ouput
    SendScpi(inst, ":OUTP ON", query_syst_err)

    # lasttime=currtime
    # currtime=time.time()
    # print('Set settings and toggle output:', currtime-lasttime, ' seconds')

def testinstrumentCalls(inst, waveform, vpp=0.001, offset=0):
    starttime=time.time()
    query_syst_err = True  
    dacSignal = waveform
    SendScpi(inst, ":INST:CHAN 1", query_syst_err)

    # load I waveform into instrument
    segNum = 1
    SendScpi(inst, ":TRACe:DEF {0},{1}".format(segNum, len(dacSignal)), query_syst_err)
    SendScpi(inst, ":TRACe:SEL {0}".format(segNum), query_syst_err)

    lasttime=starttime
    currtime=time.time()
    # print('Setup segment:', currtime-lasttime, ' seconds')
    with timer('------> AWG Write: '):
        prefix = '*OPC?; :TRAC:DATA'
        with open(".waveform","wb") as f:
            f.write(waveform.tobytes())
        res = inst.WriteBinaryData(prefix, '.waveform')

    #print(f'Write speed: {dacSignal.nbytes * 1e-9  / (currtime-lasttime)} GB/s')
    SendScpi(inst, ":SOUR:VOLT {0}".format(vpp))
    #SendScpi(inst, ":VOLT?")

    # sel segment 1 - play I
    SendScpi(inst, ":SOUR:FUNC:MODE:SEGM {0}".format(segNum), query_syst_err) 

    # connect ouput
    SendScpi(inst, ":OUTP ON", query_syst_err)

    lasttime=currtime
    currtime=time.time()
    #print('Set settings and toggle output:', currtime-lasttime, ' seconds')

def enableTrigger(inst, trig_lev, trig_channel):
    SendScpi(inst, ":TRIG:SOUR:ENAB TRG{0}".format(trig_channel)) # Set tigger enable signal to TRIG1 (CH specific)
    SendScpi(inst, ":TRIG:SEL TRG1") # Select trigger for programming (CH specific)
    SendScpi(inst, ":TRIG:LEV 0.1") # Set trigger level
    SendScpi(inst, ":TRIG:COUN 1") # Set number of waveform cycles (1) to generate (CH specific)
    SendScpi(inst, ":TRIG:IDLE DC") # Set output idle level to DC (CH specific)
    SendScpi(inst, ":TRIG:IDLE:LEV {0}".format(trig_lev)) # Set DC level in DAC value (CH specific)
    SendScpi(inst, ":TRIG:SLOP POS")


    # SendScpi(inst, ":TRIG:HOLD?")
    # SendScpi(inst, ":TRIG:TIME 500e-06")
    # SendScpi(inst, ":TRIG:SOUR:ENAB INT") # Set tigger enable signal to TRIG1 (CH specific)
    # SendScpi(inst, ":TRIG:SEL INT") # Select trigger for programming (CH specific)
    # SendScpi(inst, ":TRIG:LEV 0.1") # Set trigger level
    # SendScpi(inst, ":TRIG:COUN 1") # Set number of waveform cycles (1) to generate (CH specific)
    # SendScpi(inst, ":TRIG:IDLE DC") # Set output idle level to DC (CH specific)
    # SendScpi(inst, ":TRIG:IDLE:LEV {0}".format(trig_lev)) # Set DC level in DAC value (CH specific)

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

def sinePulse(segmentLength, squareCycles, sinCycles, duty, amp):
    starttime=time.time()
    
    t = np.linspace(0, segmentLength-1, segmentLength)
    # omegaSquare = 2 * np.pi * squareCycles
    omegaSin = 2 * np.pi * sinCycles

    # sq = (sg.square(omegaSquare*t/segmentLength, duty)+1)/2
    sq = np.append(np.ones(int(segmentLength/2)), np.zeros(int(segmentLength/2)))

    sn = np.sin(omegaSin*t/segmentLength)

    # rawSignal = ((sg.square(omegaSquare*t/segmentLength, duty)+1)/2) *amp*np.sin(omegaSin*t/segmentLength)
    rawSignal = sq * amp * sn

    # lasttime=starttime
    # currtime=time.time()
    # print('Make sine pulse:', currtime-lasttime, ' seconds')

    # dacSignal = scaleWaveform(rawSignal, "P9082M")
    dacSignal = np.uint8((rawSignal/amp*127)+127)

    # lasttime=currtime
    # currtime=time.time()
    # print('Scale waveform:', currtime-lasttime, ' seconds')

    return(dacSignal)

def fastsine(seg, cyc, amp):
    t = np.arange(seg, step=1)
    omegaSin = 2 * np.pi * cyc
    sq = np.concatenate((np.ones(int(seg/2), dtype=int), np.zeros(int(seg/2), dtype=int)))
    sn = np.sin(omegaSin*t/seg)
    rawSignal = sq * amp * sn
    dacSignal = np.uint8((rawSignal/amp*127)+127)
    del t, sq, sn, rawSignal
    return dacSignal

def rabiPulse(segmentLength, bits, sinCycles, mw_delay, mw_duration, amp):
    time = np.linspace(0, segmentLength-1, segmentLength)
    omegaSin = 2 * np.pi * sinCycles
    pulseProfile = np.zeros(segmentLength)

    # print(mw_delay, mw_duration, int((mw_delay-mw_duration)*segmentLength/1e6), int(mw_delay*segmentLength/1e6))

    for i in range(int((mw_delay-mw_duration)*segmentLength/1e6), int(mw_delay*segmentLength/1e6)):
        pulseProfile[i] = 1
    #pulseProfile[:int(len(pulseProfile)/2)] = 1
    rawSignal = pulseProfile*amp*np.sin(omegaSin*time/segmentLength)

    # dacSignal = scaleWaveform(rawSignal, "P9082M")
    dacSignal = np.uint8((rawSignal/amp*127)+127)

    return dacSignal

def fastrabi(seg, cyc, delay, dur, amp):
    t = np.arange(seg, step=1)
    omegaSin = 2 * np.pi * cyc
    pre, pulse, post = int((delay-dur)*seg//1e6), int(round(dur*seg/1e6)), int(seg-delay*seg//1e6)
    sq = np.concatenate((np.zeros(pre, dtype=int), np.ones(pulse, dtype=int), np.zeros(post, dtype=int)))
    sn = np.sin(omegaSin*t/seg)
    rawSignal = sq * amp * sn
    dacSignal = np.uint8((rawSignal/amp*127)+127)
    del t, sq, sn, rawSignal
    return dacSignal

def T1Pulse(segmentLength, bits, sinCycles, mw_delay, mw_duration, amp):
    time = np.linspace(0, segmentLength-1, segmentLength)
    omegaSin = 2 * np.pi * sinCycles
    pulseProfile = np.zeros(segmentLength)

    for i in range(int((mw_delay-mw_duration)*segmentLength/1e6), int(mw_delay*segmentLength/1e6)):
        pulseProfile[i] = 1
    #pulseProfile[:int(len(pulseProfile)/2)] = 1
    rawSignal = pulseProfile*amp*np.sin(omegaSin*time/segmentLength)

    # dacSignal = scaleWaveform(rawSignal, "P9082M")
    dacSignal = np.uint8((rawSignal/amp*127)+127)

    return(dacSignal)

def squareWave(segmentLength):
    time = np.linspace(0, segmentLength-1, segmentLength)
    return scaleWaveform(sg.square(time*(2*np.pi)/1e3),"P9082M")

def sinePulseOffset(segmentLength, squareCycles, sinCycles, duty, amp, offset):
    time = np.linspace(0, segmentLength-1, segmentLength)
    omegaSquare = 2 * np.pi * squareCycles
    omegaSin = 2 * np.pi * sinCycles
    squareSignal = np.roll((sg.square(omegaSquare*time/segmentLength, duty)+1)/2, offset)
    squareSignal[:offset] = [0] * offset
    rawSignal = (squareSignal*amp*np.sin(omegaSin*time/segmentLength))
    
    dacSignal = scaleWaveform(rawSignal, "P9082M")

    return(dacSignal)

def makeSingleESRSeqMarker(inst, duration, freq, vpp = 0.001):
    segmentLength = 8998848 #this segment length is optimized for 1kHz trigger signal
    segmentLength = int((2*duration/0.001)*segmentLength)
    cycles = int(freq * segmentLength / 9)

    print(f'--> Frequency: {freq} GHz')
    with timer('----> Waveform calculate/call: '): instrumentCalls(inst, fastsine(segmentLength, cycles, 1), vpp)
    with timer('----> Marker call: '): makeESRMarker(inst, segmentLength)

def makeSingleRabiSeqMarker(inst, mw_duration, mw_delay, freq, vpp=0.001):
    segmentLength = 8998848 * 2 #this segment length is optimized for 1kHz trigger signal
    mw_duration *= 1e9
    mw_delay *= 1e6
    cycles = int(freq * segmentLength / 9)
    print(f'Duration: {mw_duration:.3f} ns, Frequency: {freq} GHz')
    #instrumentCalls(inst, rabiPulse(segmentLength, 8, cycles, int(mw_delay/2*1e3), mw_duration/2, 1), vpp)
    with timer('----> Waveform calculate/call: '): instrumentCalls(inst, fastrabi(segmentLength, cycles, int(mw_delay*1e3//2), mw_duration/2, 1), vpp)
    with timer('----> Marker call: '): makeRabiMarker(inst, segmentLength)

# def makeSingleRabiSeq(inst, mw_duration, mw_delay, freq, vpp=0.001): ### MUST BE FIXED FOR 2KHZ TRIGGER SIGNAL
#     segmentLength = 4999936
#     segmentLength = 8998848 #this segment length is optimized for 1kHz trigger signal
#     segmentLength *= 2 #this segment length is optimized for 2kHz trigger signal
#     cycles = int(freq * segmentLength * 1e9 / 9e9)
#     print('Duration: {0} ns, Frequency: {1} GHz'.format(mw_duration, freq))
#     instrumentCallsFast(inst, rabiPulse(segmentLength, 8, cycles, int(mw_delay*1e3), mw_duration, 1), vpp)

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
        instrumentCalls(inst, sinePulseOffset(segmentLength, squares, cycles, duty, 1, offset), vpp)
        t_readoutDelay += delayStep
        time.sleep(5)

def makeT1SeqMarker(inst, t_delay,t_AOM,t_readoutDelay,t_pi, freq, vpp=0.001):
    segmentLength = 8998848 #this segment length is optimized for 1kHz trigger signal
    t_delay *= 1e6
    t_AOM *= 1e6
    t_readoutDelay *= 1e6
    t_pi *= 1e9
    hscale = 2*(t_delay+t_AOM)/1e3
    segmentLength = int(segmentLength*hscale) + (64-int(segmentLength*hscale)%64)
    cycles = int(freq * segmentLength * 1e9 / 9e9)
    print('Time between Laser Pulses: {0} us, Frequency: {1} GHz'.format(t_delay, freq))
    instrumentCalls(inst, rabiPulse(segmentLength, 8, cycles, (t_delay+t_AOM+t_readoutDelay)/hscale*1e3 + t_pi/hscale, t_pi/hscale, 1), vpp)
    makeT1Marker(inst, segmentLength, t_delay*1e3/hscale, t_readoutDelay*1e3/hscale, t_AOM*1e3/hscale)

def makeESRSweep(inst, duration, freqs, vpp = 0.001):
    segmentLength = 8998848 # this segment length is optimized for 1kHz trigger signal
    segmentLength = int((2*duration/0.001)*segmentLength)

    print(f'--> Sweeping Frequencies {freqs[0]} GHz to {freqs[-1]} GHz at {len(freqs)} points')
    
    args = np.array([np.full(freqs.shape, segmentLength), segmentLength*freqs, np.ones(freqs.shape)]).T
    with timer('----> Waveform calculate: '), hide(), Pool() as pool:
        waveform = np.array(pool.starmap(fastsine, args), dtype=np.uint8).flatten()
    
    with timer('----> Waveform call: '): testinstrumentCalls(inst, np.uint8(waveform), vpp)
    with timer('----> Marker call: '): makeESRSweepMarker(inst, segmentLength, len(freqs))

def makeESRSweepMarker(inst, segmentLength, num):
    segmentLength = segmentLength//8
    #MARKER CODE >>>>
    SendScpi(inst, ":MARK OFF")
    SendScpi(inst, ":MARK:SEL 1")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")
    # SendScpi(inst, ":MARK:OFFS 0")

    #enble marker 1 CH 1
    # time = np.linspace(0, segmentLength-1, segmentLength)

    waveform = np.zeros(segmentLength, dtype=np.uint8)

    duration = 500
    delay = 400_000
    tot = 500_000
    duration2 = 100

    for i in range(int((delay-duration2)*segmentLength/1e6), int(delay*segmentLength/1e6)):
        waveform[i] += 2

    for i in range(int(tot*segmentLength/1e6)+int((delay-duration2)*segmentLength/1e6), int(tot*segmentLength/1e6)+int(delay*segmentLength/1e6)):
        waveform[i] += 2

    waveform += 4

    totalWaveform = np.array([waveform]*num, dtype=np.uint8).flatten()

    for i in range(0, int(duration*segmentLength/1e6)):
        totalWaveform[i] += 1

    markerWave = np.uint8(totalWaveform)
    del totalWaveform

    prefix = '*OPC?; :MARK:DATA'
    # print(prefix, end=' .. ')
    
    with open(".marker","wb") as f:
        f.write(markerWave.tobytes())

    res = inst.WriteBinaryData(prefix, '.marker')
    # Validate(res.ErrCode, __name__, inspect.currentframe().f_back.f_lineno)
    # res = SendScpi(inst, ":SYST:ERR?", False, False)
    # print(res[1])

    # SendScpi(inst, ":MARK:SEL?")

    SendScpi(inst, ":MARK:VOLT:PTOP 1.2")
    SendScpi(inst, ":MARK ON")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")

    SendScpi(inst, ":MARK:SEL 2")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")
    SendScpi(inst, ":MARK:VOLT:PTOP 0.5")
    SendScpi(inst, ":MARK ON")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")
    SendScpi(inst, ":MARK:SEL 3")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")
    SendScpi(inst, ":MARK:VOLT:PTOP 1.2")
    SendScpi(inst, ":MARK ON")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")

def makeT2Seq(inst, t_delay,t_AOM,t_readoutDelay, t_pi, freq, vpp=0.001, IQpadding=0, numberOfPiPulses=1):
    segmentLength = 8998848 #this segment length is optimized for 1kHz trigger signal
    segmentLength *= 2
    cycles = int(freq * segmentLength * 1e9 / 9e9)
    # print('Duration: {0} ns, Frequency: {1} GHz'.format(mw_duration, freq))
    instrumentCalls(inst, T2Pulse(segmentLength, cycles, t_AOM, t_delay, t_pi, 1), vpp)
    makeRabiMarker(inst, segmentLength)

def T2Pulse(segmentLength, cycles, t_AOM, t_delay, t_pi, amp):
    time = np.linspace(0, segmentLength-1, segmentLength)
    omegaSin = 2 * np.pi * cycles
    pulse = np.zeros(int(segmentLength/2))
    for i in range(int((t_pi/2)*segmentLength/2e-3)):
        pulse[int((t_AOM-2*t_delay-2*t_pi)*segmentLength/2e-3)+i] = amp*np.sin(omegaSin*i/segmentLength)
        pulse[int((t_AOM-t_pi/2)*segmentLength/2e-3)+i] = amp*np.sin(omegaSin*i/segmentLength+math.pi)
    for i in range(int((t_pi)*segmentLength/2e-3)):
        pulse[int((t_AOM-t_delay-t_pi-t_pi/2)*segmentLength/2e-3)+i] = amp*np.cos(omegaSin*i/segmentLength)
    # for i in range(int((t_delay-t_pi)*segmentLength/2e-3), int(t_delay*segmentLength/2e-3)):
    #     pulseProfile[i] = 1
    # rawSignal = pulseProfile*amp*np.sin(omegaSin*time/segmentLength-np.pi)
    rawSignal = np.append(pulse, pulse)

    # dacSignal = scaleWaveform(rawSignal, "P9082M")
    dacSignal = np.uint8((rawSignal/amp*127)+127)

    return(dacSignal)

def makeT2Sweep(inst, t_AOM, t_pi, t_readoutDelay, taus, freq, vpp = 0.001):
    starttime=time.time()
    segmentLength = 4999936
    segmentLength = 8998848 #this segment length is optimized for 1kHz trigger signal
    segmentLength = int((4*t_AOM/0.001)*segmentLength)

    cycles = freq * segmentLength * 1e9 / 9e9
    print('Sweeping Taus {0} s to {1} s at {2} points'.format(taus[0], taus[-1], len(taus)))
    waveform=[]
    for i in range(len(taus)):
        waveform = np.append(waveform, T2Pulse(segmentLength, cycles, t_AOM, taus[i], t_pi, 1))
    
    lasttime=starttime
    currtime=time.time()
    print('----> Calculate sequence:', currtime-lasttime, ' seconds')
    
    instrumentCalls(inst, np.uint8(waveform), vpp)
    lasttime=currtime
    currtime=time.time()
    print('----> Waveform call:', currtime-lasttime, ' seconds')
    makeT2SweepMarker(inst, segmentLength, len(taus))
    lasttime=currtime
    currtime=time.time()
    print('----> Marker call:', currtime-lasttime, ' seconds')

def makeT2SweepMarker(inst, segmentLength, num):
    segmentLength = int(segmentLength/8)
    #MARKER CODE >>>>
    SendScpi(inst, ":MARK OFF")
    SendScpi(inst, ":MARK:SEL 1")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")
    # SendScpi(inst, ":MARK:OFFS 0")

    #enble marker 1 CH 1
    waveform = np.zeros(segmentLength)

    duration = 300

    for i in range(0, int(duration*segmentLength/2e6)):
        waveform[i] += 1

    delay = 1000000
    duration2 = 500000

    for i in range(int((delay-duration2)*segmentLength/2e6), int(delay*segmentLength/2e6)):
        waveform[i] += 4

    for i in range(int((2*delay-duration2)*segmentLength/2e6), int(2*delay*segmentLength/2e6)):
        waveform[i] += 4
    
    # delay = 1000000
    # duration = 300
    delay = 900000
    tot = 1000000
    duration = 100

    for i in range(int((delay-duration)*segmentLength/2e6), int(delay*segmentLength/2e6)):
        waveform[i] += 2

    for i in range(int(tot*segmentLength/2e6)+int((delay-duration)*segmentLength/2e6), int(tot*segmentLength/2e6)+int(delay*segmentLength/2e6)):
        waveform[i] += 2


    totalWaveform = []
    for i in range(num):
        totalWaveform = np.append(totalWaveform, waveform)

    for i in range(0, int(duration*segmentLength/1e6)):
        totalWaveform[i] += 1

    markerWave = np.uint8(totalWaveform)
    # print(markerWave.tobytes()[:1000])
    
    prefix = ':MARK:DATA 0,#'
    # print(prefix, end=' .. ')
    res = inst.WriteBinaryData(prefix, markerWave.tobytes())
    # Validate(res.ErrCode, __name__, inspect.currentframe().f_back.f_lineno)

    # res = SendScpi(inst, ":SYST:ERR?", False, False)
    # print(res[1])

    # SendScpi(inst, ":MARK:SEL?")

    SendScpi(inst, ":MARK:VOLT:PTOP 1.2")
    SendScpi(inst, ":MARK ON")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")

    SendScpi(inst, ":MARK:SEL 2")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")
    SendScpi(inst, ":MARK:VOLT:PTOP 0.5")
    SendScpi(inst, ":MARK ON")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")
    SendScpi(inst, ":MARK:SEL 3")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")
    SendScpi(inst, ":MARK:VOLT:PTOP 1.2")
    SendScpi(inst, ":MARK ON")
    # SendScpi(inst, ":MARK:SEL?")
    # SendScpi(inst, ":MARK?")

def makeXY8seq(t_delay,t_AOM,t_readoutDelay,t_pi,IQpadding, numberOfRepeats):
    return

def makecorrelationSpectSeq(t_delay_betweenXY8seqs,t_delay, t_AOM,t_readoutDelay,t_pi,IQpadding,numberOfRepeats):
    return