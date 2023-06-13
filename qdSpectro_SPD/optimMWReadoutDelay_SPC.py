# optimMWReadoutDelay.py
# Copyright 2018 Diana Prado Lopes Aude Craik

## modified 2022 - Zhao Hao

# Permission is hereby granted, free of charge, to any person 
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use, copy,
# modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Optmize Readout Delay script

This script can be used to find the optimum delay between the start of the AOM pulse and the start of the DAQ pulse (see step 54 of the protocol). The script plots fluorescence emitted by an NV diamond sample as a function of the scanned delay, and saves the data as a tabulated text file (see below for saving options). 

To run this script:
 1) Edit connectionConfig.py to define the PulseBlaster and DAQ channel connections being used in your setup.
 2) Edit the user inputs section below.
 3) Run the script. From a windows command prompt, the script can be run by calling python optimizeReadoutDelay.py
 
 User inputs:
 -->Note: t_min is defined as the time resolution of your PulseBlaster card (i.e.t_min = 1/(clock frequency)). E.g. for a 500MHz card, t_min = 2ns. 
 *startDelay: shortest delay in scan, in nanoseconds (must be >=5*t_min).
 *endDelay:  longest delay in scan, in nanoseconds.
 *N_scanPts: number of points in the scan.
 *t_AOM: duration of AOM pulse, in ns.
 *Nsamples: number of fluorescence measurement samples to take at each delay point.
 *DAQtimeout: amount of time (in seconds) for which the DAQ will wait for the requested number of samples to become available (ie. to be acquired)
 *plotPulseSequence: if set to True, this script will generate a plot of the pulse sequence ouput by the PulseBlaster
 *savePath: path to folder where data will be saved. By default, data is saved in a folder called Saved_Data in the directory where this script is saved
 *saveFileName: file name under which to save the data. This name will later be augmented by the date and time at which the script was run.

"""
#Imports
from spinapi import ns,us,ms
import os
import numpy as np
from time import localtime, strftime
from connectionConfig import *
import SRScontrol as SRSctl
import DAQcontrol_aSinglePhotonCounter as DAQctl
import PBcontrol as PBctl
import sequenceControl_aSinglePhotonCounter as seqCtl
import random
import matplotlib.pyplot as plt
import numpy as np
import sys

# Define t_min, time resolution of the PulseBlaster, given by 1/(clock frequency):
t_min = 1e3/PBclk #in ns; 1000/500 = 2 ns

#-------------------------  USER INPUT  ---------------------------------------#

# Scan parameters:----------------------------------------------------
# Start pulse duration (in nanoseconds), must be >=5*t_min:
startDelay = 1*us #5*t_min
# End pulse duration (in nanoseconds):
endDelay = 100*us
# Number of delay steps:
N_scanPts = 100
# Microwave power output from SRS(Vpp) - DO NOT EXCEED YOUR AMPLIFIER'S MAXIMUM INPUT POWER:
microwavePower = 0.26 ## with amplifier
# Microwave frequency (Hz):
microwaveFrequency = 2.875e9 #2.91e9 #3.04e9 # 2.871e9 ##2.92e9 ## 2.863e9 ## 
# Pulse sequence parameters:----------------------------------------------------
# Microwave pulse duration (in ns)
t_uW = 20*us
# Number of fluorescence measurement samples to take at each delay point:
Nsamples = 10000
#DAQ timeout, in seconds:
DAQtimeout = 10
# Plotting options--------------------------------------------------------------
# Plot pulse sequence option  - set to true to plot the pulse sequence
plotPulseSequence = True
# Save options------------------------------------------------------------------
# Path to folder where data will be saved:
savePath = os.getcwd()+"\\Saved_Data\\20220706\\"
#savePath = "G:\\My Drive\\Documents\\LBNL\\Magnetic Imaging\\Data\\20200826\\"
# File name for data file
saveFileName = "ORD_fiber_0MW_10mW_0A_cat14_"
#------------------------- END OF USER INPUT ----------------------------------#
try:
    t_readoutDelay = np.linspace(startDelay,endDelay, N_scanPts, endpoint=True) 
    #PB channels
    PBchannels = {'AOM':AOM,'DAQ':DAQ,'uW':uW,'STARTtrig':STARTtrig}
    #Make save file path
    dateTimeStr = strftime("%Y-%m-%d_%Hh%Mm%Ss", localtime())
    dataFileName = savePath + saveFileName+ dateTimeStr +".txt"
    #Make param file path
    paramFileName = savePath + saveFileName+dateTimeStr+'_PARAMS'+".txt"
    #Param file save settings
    formattingSaveString = "%s\t%d\n%s\t%d\n%s\t%f\n%s\t%f\n%s\t%f\n%s\t%r\n%s\t%s\n"
    expParamList = ['N_scanPts:',N_scanPts,'Nsamples:',Nsamples,'startDelay:',startDelay,'endDelay:',endDelay,'t_uW:',t_uW,'plotPulseSequence:',plotPulseSequence,'dataFileName:',dataFileName]


    #Validate user input:
    if startDelay<(5*t_min):
        print('Error: startDelay is too short. Please set startDelay>',5*t_min,'ns.')
        sys.exit()
    if startDelay%(t_min):
        startDelay = t_min*round(startDelay/t_min)
        print('Warning: startDelay is not a multiple of',t_min,'ns. Rounding...\nstartDelay now set to:',startDelay,'ns.')
        t_readoutDelay = np.linspace(startDelay,endDelay, N_scanPts, endpoint=True) 
    stepSize = t_readoutDelay[1]-t_readoutDelay[0]
    if (stepSize%t_min):
                roundedStepSize = t_min*round(stepSize/t_min)
                endDelay  = (N_scanPts-1)*roundedStepSize + startDelay 
                print('Warning: requested time step is ',stepSize,'ns, which is not an integer multiple of ',t_min,'ns. Rounding step size to the nearest multiple of ',t_min,':\nStep size is now',roundedStepSize,'.\nstartDelay=',startDelay,' and \nendDelay=',endDelay)
                t_readoutDelay = np.linspace(startDelay,endDelay, N_scanPts, endpoint=True)

    fluorescence = np.zeros(N_scanPts)
    if plotPulseSequence:
        instructionArray= PBctl.programPB('makeMWDelaySweep', [t_readoutDelay[-1],t_uW])
        [t_us,channelPulses,yTicks]=seqCtl.plotSequence(instructionArray,PBchannels)
        plt.figure(0)
        for channel in channelPulses:
            plt.plot(t_us, list(channel))
        plt.yticks(yTicks)
        plt.xlabel('time (us)')
        plt.ylabel('channel')
        plt.title('Pulse Sequence plot (at first scan point)')
        plt.show()

    #Configure DAQ
    DAQclosed = False
    DAQtask = DAQctl.configureDAQ(Nsamples)
    #DAQtask, dummyTask = DAQctl.configureDAQ(Nsamples)
    SRS = SRSctl.initSRS(GPIBaddr,modelName)
    SRSctl.setSRS_RFAmplitude(SRS,microwavePower)
    SRSctl.setSRS_Freq(SRS, microwaveFrequency)
    SRSctl.enableSRS_RFOutput(SRS)

       
    #Run readout delay scan:
    for i in range (0, N_scanPts):
        #Program PB
        instructionArray= PBctl.programPB('makeMWDelaySweep', [t_readoutDelay[i],t_uW])
        print('Scan point ', i+1, ' of ', N_scanPts)
        #read DAQ
        sig = DAQctl.readDAQ(DAQtask, Nsamples * 2,DAQtimeout)
        #sig = DAQctl.readDAQ(DAQtask,dummyTask, Nsamples * 2,DAQtimeout)
        #sig = np.subtract(signl, [0] + signl[:len(signl)-1])  ## special algorithm for single photon counter. ZH 2020
        #print(sig)
        #Take average of counts
        #sig = np.diff(signl, prepend = signl[0])
        fluorescence[i] = np.mean(sig)

    #Close DAQ task:
    DAQctl.closeDAQTask(DAQtask)
    #DAQctl.closeDAQTask(dummyTask)
    SRSctl.disableSRS_RFOutput(SRS)
    DAQclosed = True
    #Save data:
    #Check if save directory exists, and, if not, creates a "Saved Data" folder in the current directory, where all data will be saved.
    if not (os.path.isdir(savePath)):
         os.makedirs(savePath)
         print('Warning: Save directory did not exist, creating folder named Saved_Data in the working directory. Data will be saved to this directory.')

    data = np.array([t_readoutDelay,fluorescence])
    data = data.T
    dataFile = open(dataFileName, 'w')
    for item in data:
        dataFile.write("%.0f\t%f\n" % tuple(item))
    paramFile = open(paramFileName, 'w')
    paramFile.write(formattingSaveString % tuple(expParamList))
    dataFile.close()
    paramFile.close()

    #Plot results
    plt.figure(1)
    plt.plot(t_readoutDelay, fluorescence)
    plt.xlabel('Delay (ns)')
    plt.ylabel('APD Voltage (V)')
    plt.show()
except KeyboardInterrupt:
        print('User keyboard interrupt. Quitting...')
        sys.exit()
except Exception as e:
    print(e)
finally:
        if 'SRS' in vars(): 
            #Turn off SRS output
            SRSctl.disableSRS_RFOutput(SRS)
        if ('DAQtask' in vars()) and  (not DAQclosed):
            #Close DAQ task:
            DAQctl.closeDAQTask(DAQtask)
#            DAQctl.closeDAQTask(dummyTask)
            DAQclosed=True