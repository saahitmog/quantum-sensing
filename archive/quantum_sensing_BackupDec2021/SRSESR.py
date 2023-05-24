# import PBcontrol as PBctl
# import sequenceControl as seqCtl
#import ESRconfig as ESR
# from spinapi import *
from ctypes import *
import numpy as np
import sys
import DAQ_Analog as DAQ #NOTE THIS CHANGE FROM PHOTODIODE CODE
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


#Define number of measurements to throw away before starting experiment 
NThrow = 0

#def main():
    #For running experiment normally
    #global config
    #config = {}
    #Constants for PulseBlaster
    #config['t_AOM'] = 50000 * ns
    #config['sequence_name'] = "ESRseq"

    #Defines the frequency that the SRS will sweep (in GHz)
    #config['START_FREQUENCY'] = 2.5
    #config['END_FREQUENCY'] = 3.5
    #config['N_pts'] = 101

    #runExperiment()

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
def instrumentCalls(inst, waveform, offset=0):
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
    SendScpi(inst, ":SOUR:VOLT 1")

    # sel segment 1 - play I
    SendScpi(inst, ":SOUR:FUNC:MODE:SEGM {0}".format(segNum), query_syst_err) 
    
    trig_lev = 128
    enableTrigger(inst, trig_lev, 1)

    # connect ouput
    SendScpi(inst, ":OUTP ON", query_syst_err)
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
    SendScpi(inst, ":TRIG:LEV 0") # Set trigger level
    SendScpi(inst, ":TRIG:COUN 1") # Set number of waveform cycles (1) to generate (CH specific)
    SendScpi(inst, ":TRIG:IDLE DC") # Set output idle level to DC (CH specific)
    SendScpi(inst, ":TRIG:IDLE:LEV {0}".format(trig_lev)) # Set DC level in DAC value (CH specific)
    SendScpi(inst, ":TRIG:STAT ON") # Enable trigger state (CH specific)
    SendScpi(inst, ":INIT:CONT OFF") # Enable trigger mode (CH specific)
    SendScpi(inst, ":TRIG:GATE:STAT OFF") #Disable trigger gated mode

def sinePulse(segmentLength, bits, squareCycles, sinCycles, duty, amp):
    
    time = np.linspace(0, segmentLength-1, segmentLength)
    omegaSquare = 2 * np.pi * squareCycles
    omegaSin = 2 * np.pi * sinCycles
    rawSignal = ((sg.square(omegaSquare*time/segmentLength, duty)+1)/2) *amp*np.sin(omegaSin*time/segmentLength)

    dacSignal = scaleWaveform(rawSignal, "P9082M")

    return(dacSignal);

def sinePulseOffset(segmentLength, bits, squareCycles, sinCycles, duty, amp, offset):
    time = np.linspace(0, segmentLength-1, segmentLength)
    omegaSquare = 2 * np.pi * squareCycles
    omegaSin = 2 * np.pi * sinCycles
    squareSignal = np.roll((sg.square(omegaSquare*time/segmentLength, duty)+1)/2, offset)
    squareSignal[:offset] = [0] * offset
    rawSignal = (squareSignal*amp*np.sin(omegaSin*time/segmentLength))
    
    dacSignal = scaleWaveform(rawSignal, "P9082M")

    return(dacSignal);

def makeESRseq(inst, t_duration, mw_duration, startFreq, endFreq, freqStep=1):
    #t_duration is total duration
    #mw_duration is microwave duration
    #Frequency (MHz) 10-1000 Integer val
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
        cycles = int(freq * segmentLength * 1e6 / 9e9)
        squares = int((1/(t_duration / 1e6)) * segmentLength / 9e9)
        duty = mw_duration / t_duration
        print('Frequency: {0} MHz'.format(freq))
        instrumentCalls(inst, sinePulse(segmentLength, 8, squares, cycles, duty, 1))
        freq += freqStep

def makeSingleESRSeq(inst, duration, freq):
    segmentLength = 4999936
    segmentLength = 8998848 #this segment length is optimized for 1kHz trigger signal
    cycles = int(freq * segmentLength * 1e6 / 9e9)
    squares = int((1/(duration / 1e6)) * segmentLength / 9e9)
    duty = 0.5
    print('Frequency: {0} MHz'.format(freq))
    instrumentCalls(inst, sinePulse(segmentLength, 8, squares, cycles, duty, 1))

def makeReadoutDelaySweep(inst, t_duration, mw_duration, freq, delayStart, delayStop, delayStep=0.1):
    #delay in microseconds
    instrumentSetup(inst)
    t_readoutDelay = delayStart
    while t_readoutDelay <= delayStop:
        tot_duration = t_duration + t_readoutDelay
        segmentLength = 4999936
        cycles = int(freq * segmentLength * 1e6 / 9e9)
        squares = int((1/(tot_duration / 1e6)) * segmentLength / 9e9)
        duty = mw_duration / tot_duration
        offset = int(2*np.pi*t_readoutDelay/tot_duration)
        print('Delay: {0} us'.format(t_readoutDelay))
        instrumentCalls(inst, sinePulseOffset(segmentLength, 8, squares, cycles, duty, 1, offset))
        t_readoutDelay += delayStep
        time.sleep(5)

def makeRabiSeq(inst, t_duration, freq, mwStart, mwStop, mwStep=0.1):
    #delay in microseconds
    instrumentSetup(inst)
    mw_duration = mwStart
    while mw_duration <= mwStop:
        segmentLength = 4999936
        cycles = int(freq * segmentLength * 1e6 / 9e9)
        squares = int((1/(t_duration / 1e6)) * segmentLength / 9e9)
        duty = mw_duration / t_duration
        # offset = int(2*np.pi*t_readoutDelay/t_duration)
        offset = 0
        print('MW duration: {0} us'.format(mw_duration))
        instrumentCalls(inst, sinePulseOffset(segmentLength, 8, squares, cycles, duty, 1, offset))
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

def run(config_dic):
    global config
    config = config_dic
    runExperiment()

def runExperiment():
    try:
         #start the start time to measure length of program execution
        start = time.process_time()

        config['N_pts'] = int(config['N_pts'])
        config['N_samples'] = int(config['N_samples'])
        #Setup plotting style
        style.use("fivethirtyeight")

        #create figure and subplot, figsize can be changed in the global configuration document
        fig = plt.figure(figsize = (config['figsize_x'], config['figsize_y']))
        ax = fig.add_subplot(111)

        #sweep is a np array of frequency values that we will sweep across, step_size is the size of steps between
        sweep, step_size = np.linspace(config['START_FREQUENCY'], config['END_FREQUENCY'], num = config['N_pts'], retstep = True)
        #sweep = np.arange(config['START_FREQUENCY'], config['END_FREQUENCY'] + config['STEP_FREQUENCY'], config['STEP_FREQUENCY'])

        #create a dictionary that will save signal and background information and will be exported to pandas df and then to a csv
        save_dict = {}
        save_dict['Frequency'] = sweep


        #create arrays to hold the average values across averaging runs
        length = config['N_pts']
        total_pts = length * config['Navg']
        average_x = sweep
        average_y = np.zeros(length)

        #create arrays to hold realtime values during an averaging run, xs and ys will be plotted while signal and background are saved
        signal = np.zeros(length)
        background = np.zeros(length)
        xs = sweep
        ys = np.zeros(length)

        #the data array holds new samples that come from a DAQ read since we're using stream readers
        data = np.zeros(config['N_samples'] * 4)

        #plot the data for the first time and get the line variable (which isn't really used)
        line, = ax.plot(xs, ys, 'b-')
        
        print('debug')
        # #initiate RF generator with channel and model type; set amplitude
        my_SRS = SRSctl.initSRS(27, 'SG384')

        SRSctl.setSRS_RFAmplitude(my_SRS, config['mw_power'], units = "Vpp") 

        # #set test frequency and modulation; ESR has no modulation but that's handled in the modulation function
        SRSctl.setSRS_Freq(my_SRS, config['START_FREQUENCY'], 'GHz') 
        SRSctl.setupSRSmodulation(my_SRS, config['sequence_name']) 

        # #run the initPB function from the PBinit file 
        # initPB()

        # #Get the instruction Array
        # instructionArray = PBctl.programPB(config['sequence_name'], [config['t_AOM'] * ns])
        # print(instructionArray)

        # #Program the PulseBlaster
        # status = pb_start_programming(PULSE_PROGRAM)
        # for i in range(0, len(instructionArray)):
        # 	PBctl.pb_inst_pbonly(instructionArray[i][0],instructionArray[i][1],instructionArray[i][2],instructionArray[i][3])
        # pb_stop_programming()

        #Configure the DAQ
        task = DAQ.configureDAQ(config['N_samples'])

        #TURN ON AWG AND INITIALIZE INST
        # print('Process Id = {0}'.format(os.getpid()))
        # admin = loadDLL()
        # slotId = getSlotId(admin)
        # if not slotId:
        #     print("Invalid choice!")
        # else:
        #     inst = admin.OpenInstrument(slotId)
        #     if not inst:
        #         print("Failed to Open instrument with slot-Id {0}".format(slotId))  # @IgnorePep8
        #         print("\n")
        #     else:
        #         instId = inst.InstrId
        # instrumentSetup(inst)
        # #turn on the microwave excitation 
        SRSctl.enableSRS_RFOutput(my_SRS)

        #Function to close all running tasks
        def closeExp():
            # #turn off the microwave excitation
            SRSctl.disableSRS_RFOutput(my_SRS) 

            # #stop the pulse blaster
            # pb_stop()
            # pb_close()
            # pb_reset()
            #rc = admin.CloseInstrument(instId)
            #Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)
            #rc = admin.Close()
            #Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)
            #Close the DAQ once we are done
            DAQ.closeDAQTask(task)
            return

        #Function to save data 
        def save():
            #check if user wants to save the plot
            #saved = input("Save plot? y/n")
            saved = 'y'
            if saved == 'y':
                #name = input("Enter a filename:")
                name = config['folder'] + '/' + config['name'] + '_' + str(config['magnet_power'])
                #save the figure
                plt.savefig(name + '.png')

                #save the pandas dataframe with background, signal, and frequency
                dataset = pd.DataFrame(save_dict)
                dataset.to_csv(name + '.csv')

                #closeExp()
                #sys.exit()

            #elif saved == 'n':
                #closeExp()
                #sys.exit()
                #x=0
            #else:
            #	print('Error, try again')
            #	save()

        #start the pulse blaster with the sequence that was programmed
        #pb_start()
        # makeSingleESRSeq(inst, config['t_AOM'], config['START_FREQUENCY'])
        #Throw away the first NThrow samples to get the photon counter warmed up (not really necessary)
        for i in range(NThrow):
            DAQ.readDAQ(task, config['N_samples'], config['DAQtimeout'])

        #Init function used by FuncAnimation to setup the initial plot; only used if blit = True
        def init():
            line.set_data([], [])
            return line, 

        #Initialize f to be the start frequency, avg_run to be 0, and step to be 0
        f = sweep[0]
        avg_run = 0
        step = 0
        begin = time.time()
        close = True
        #This is the function that runs the experiment and does the plotting
        def animate(k):
            #Defines f,avg_run,step as global variables so we can update between function calls
            nonlocal f
            nonlocal avg_run
            nonlocal step
            nonlocal close

            #If f goes past end frequency, we are done
            if step >= length:
                #Save the signal and background arrays to the dictionary
                save_dict['Signal Run ' + str(int(avg_run))] = copy.deepcopy(signal)
                save_dict['Background Run ' + str(int(avg_run))] = copy.deepcopy(background)

                #if we haven't finished all averaging runs yet, reset all temp variables and continue
                if avg_run < config['Navg'] - 1:
                    f = sweep[0]
                    step = 0
                    avg_run += 1
                    return 

                #get the end of the progress time and calculate time elapsed
                end = time.process_time()
                print('time elapsed: ' + str(end - start))
                closeExp()
                save()
                plt.close(fig)
                close = False
                return None

            #Otherwise, increment the frequency and continue
            else:
                #Get new frequency value
                f = sweep[step]

                #init RF generator with new frequency
                SRSctl.setSRS_Freq(my_SRS, f, 'GHz')
                #init AWG with new frequency
                #makeSingleESRSeq(inst, config['t_AOM'], f)
                
                #Read from the DAQ
                data = DAQ.readDAQ(task, config['N_samples'] * 2, config['DAQtimeout'])
                #the signal is the even points and background is the odd points from the data array
                counts = data[:config['N_samples'] * 2]
                current_signal = counts[0::2]
                current_background = counts[1::2]
                
                if step == 0:
                    print(counts[0:15])
                
                #normalized_counts = np.diff(counts, prepend = counts[0])

                #current_signal = normalized_counts[0::2]
                #current_background = normalized_counts[1::2]
                for i in np.arange(0, int(len(counts)/2), 2):
                    current_signal[i] = counts[i]
                    current_background[i+1] = counts[i+1] - counts[i]

                #average both arrays
                sig_average = np.mean(current_signal)
                back_average = np.mean(current_background)

                #append signal to signal array and background to background array
                signal[step] = sig_average
                background[step] = back_average

                #Depending on the plotting type, either append the signal or the contrast
                if config['plotting_type'] == 'signal':
                    ys[step] = sig_average
                else:
                    ys[step] = sig_average - back_average
                
                #Average the y correctly 
                average_y[step] = ((average_y[step] * avg_run) + ys[step]) / (avg_run+1)

                #plot the new data, we plot the entire average arrays, but we only plot the realtime data up to what we have so far
                ax.clear()
                ax.plot(xs[:step + 1], ys[:step + 1], 'o')
                if avg_run == 0:
                    ax.plot(average_x[:step + 1], average_y[:step + 1], 'r-')
                else:
                    ax.plot(average_x, average_y, 'r-')

                #Make the plot look good
                plt.xticks(rotation=45, ha='right')
                plt.subplots_adjust(bottom=0.30)
                plt.title('Photo Counter Readout vs Frequency')
                plt.ylabel('Photon Counts')
                plt.xlabel('Frequency (GHz)')

                #If we are starting a new averaging run, print it
                if step == 0:
                    print('Starting Averaging Round: ' + str(avg_run))
                step += 1

                #Test code to calculate the % complete and time left for the experiment
                pts_complete = (avg_run * length) + step
                fraction_complete = (pts_complete / total_pts) 
                intermediate_time = time.time()
                time_spent = intermediate_time - begin
                time_left = (time_spent / fraction_complete) - time_spent
                if step % 10 == 0:
                    print('Percent Complete: ' + str(int((fraction_complete * 100))))
                    print('Approx. Time Left (s): ' + str(int(time_left)))
        #Begin the animation - All of the experiment work is done in the animate function
        ani = animation.FuncAnimation(fig, animate, init_func = init, interval = 1, blit = False, frames = int(total_pts) + 2, repeat = False) 
        plt.show()
        return None
    finally:
        return None