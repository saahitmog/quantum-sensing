#DAQ control
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

import nidaqmx
from  nidaqmx.constants import *
from connectionConfig import *
import sys
import time
DAQ_APDInput = "Dev1/ai0"

system = nidaqmx.system.System.local()
def configureDAQ(Nsamples):
	# try:
	# 	#Create and configure an analog input voltage task
	# 	NsampsPerDAQread=2*Nsamples
	# 	readTask = nidaqmx.Task()
	# 	channel = readTask.ai_channels.add_ai_voltage_chan(DAQ_APDInput)

	try:
		#Create and configure an analog input voltage task
		NsampsPerDAQread=2*Nsamples
		readTask = nidaqmx.Task()
		#channel = readTask.ai_channels.add_ai_voltage_chan(DAQ_APDInput)
		channel = readTask.ai_channels.add_ai_voltage_chan(DAQ_APDInput,"",TerminalConfiguration.DIFFERENTIAL,minVoltage,maxVoltage,VoltageUnits.VOLTS)

		#Configure sample clock
		readTask.timing.cfg_samp_clk_timing(DAQ_MaxSamplingRate,DAQ_SampleClk,Edge.RISING,AcquisitionType.FINITE, NsampsPerDAQread)

		# #Configure convert clock
		#readTask.timing.ai_conv_src = DAQ_SampleClk
		#readTask.timing.ai_conv_active_edge = Edge.RISING
		# readTask.timing.cfg_samp_clk_timing(DAQ_MaxSamplingRate, DAQ_SampleClk)
		# print("configured clock")

		#Configure start trigger
		readStartTrig = readTask.triggers.start_trigger
		readStartTrig.cfg_dig_edge_start_trig(DAQ_StartTrig,Edge.RISING)

		# #Create a reader from stream reading
		# reader = AnalogSingleChannelReader(readTask.in_stream)
		# reader.verify_array_shape = False	

	except Exception as excpt:
		print('Error configuring DAQ. Please check your DAQ is connected and powered. Exception details:', type(excpt).__name__,'.',excpt)
		closeDAQTask(readTask)
		sys.exit()

	return readTask

def readDAQ(task,N,timeout):
	try:
		counts = task.read(N,timeout)
	except Exception as excpt:
		print('Error: could not read DAQ. Please check your DAQ\'s connections. Exception details:', type(excpt).__name__,'.',excpt)
		sys.exit()
	return counts
	
def closeDAQTask(task):
	task.close()

def DAQTest():
	task = configureDAQ(1)
	try:
		for i in range(10):
			print(readDAQ(task, 1, 10))
			time.sleep(1)
		closeDAQTask(task)
	except:
		sys.exit()