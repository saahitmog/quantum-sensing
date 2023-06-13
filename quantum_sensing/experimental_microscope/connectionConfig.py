# connectionConfig.py
# Copyright 2018 Diana Prado Lopes Aude Craik

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

#-------------------------  USER INPUT  ---------------------------------------#
#PulseBlaster clock frequency (in MHz):
PBclk = 500

#PulseBlaster Connections ----------------------------------------------
#Enter below the bit numbers of the PulseBlaster channels to which you connect your instruments, according to the definitions below. Example: If you are using the SP18A ESR-PRO Pulseblaster board and chose bit 2 (corresponding to the BNC2 connector on the PulseBlaster board, as shown in figure 10 of the Septermber/2017 version of the PulseBlasterESR-PRO manual) to output the start trigger pulses, you should enter PB_STARTtrig =2.

#  PB_I is the bit number of the PulseBlaster channel connected to the I (or "in phase") input of the SRS microwave signal generator.
#  PB_Q is the bit number of the PulseBlaster channel connected to the Q (or "in quadrature") input of the SRS microwave signal generator.
#  PB_STARTtrig is the bit number of the PulseBlaster channel used to generate the pulses fed to the Data Acquisition Card (DAQ) to trigger the start of data aquisition at each experiment scan point.
#  PB_DAQ is the bit number of the PulseBlaster channel used to generate the pulses fed to the DAQ to gate/act as a sample clock to time the data aquisition.
#  PB_AOM is the bit number of the PulseBlaster channel connected to the TTL input of the switch used to switch on and off the radio-frequency drive to the Acousto Optic Modulator (AOM).
#  PB_Microwaves is the bit number of the PulseBlaster channel connected to the TTL input of the switch used to switch on and off the microwaves generated by the SRS microwave signal generator.

PB_AOM = 0
PB_MW = 1
PB_DAQ = 2
PB_STARTtrig = 3

PB_I = 12
PB_Q = 13
# oscope 2 = pb 13
# oscope 3 = pb 15

# DAQ Connections-------------------------------------------------------
#Enter below the National Instruments DAQ channels used for data acquisition,as follows:
#DAQ_APDInput is the analog input channel of the DAQ to which you have connected your photodector's signal. Here, this is assumed to be a Referenced Single-Ended (RSE) connection. If the user wishes to use a differential connection, the configuration below and in the DAQcontrol.py library should be modified accordingly (e.g. if using the NI USB-6211 DAQ card, refer to chapter 4 the NI USB-621x manual version from April 2009, for analog-input connection options)
#DAQ_SampleClk is the Peripheral Function Interface (PFI) terminal of the DAQ to which you have connected the output of the PB_DAQ PulseBlaster channel (i.e. the PulseBlaster channel which generates the TTL pulses that gate/act as a sample clock to time the data aquisition)
#DAQ_StartTrig is the Peripheral Function Interface (PFI) terminal of the DAQ to which you have connected the output of the PB_STARTtrig PulseBlaster channel (i.e. the PulseBlaster channel which generates the TTL pulses that trigger the start of data aquisition at each experiment scan point)

DAQ_APDInput = "Dev1/ai0"
DAQ_APDTerm = "PFI0"
DAQ_SampleClk = "PFI2"
DAQ_StartTrig = "PFI4"
# DAQ_StartTrig = "PFI3"

#Enter below the maximum sampling rate of your National Instruments DAQ in samples per channel per second:
DAQ_MaxSamplingRate = 250000
#DAQ_MaxSamplingRate = 50000000
#Set minVoltage and maxVoltage (in Volts) below to match an AI (analog input) voltage range which is supported by your DAQ and which accommodates the range of voltages output by your photodetector (e.g. the ‘Analog Input’ section of chapter 4 of the NI USB-621x manual version from April 2009 includes a table listing the supported input voltage ranges for the NI DAQ USB-621x series).
minVoltage= -10
maxVoltage= 10

#SRS Connections-------------------------------------------------------
# Enter below the GPIB address and model name of your SRS.
GPIBaddr = 27
modelName='SG386'

#------------------------- END OF USER INPUT ----------------------------------#

#Convert PulseBlaster bit number to PulseBlaster register address:
I = 2**PB_I
Q = 2**PB_Q
STARTtrig = 2**PB_STARTtrig
DAQ = 2**PB_DAQ
AOM = 2**PB_AOM
uW = 2**PB_MW