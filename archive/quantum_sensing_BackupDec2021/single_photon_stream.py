import nidaqmx
import nidaqmx.system
from  nidaqmx.constants import *
from connectionConfig import *
import numpy as np
import sys
from nidaqmx.stream_readers import CounterReader

#system = nidaqmx.system.System.local()
DAQ_APDInput = "DEV1/ctr0"   ## the signal from single photon counter.

def configureDAQ(Nsamples):
	try:
		NsampsPerDAQread=2*Nsamples
		readTask = nidaqmx.Task()
		channel = readTask.ci_channels.add_ci_count_edges_chan(DAQ_APDInput,"", initial_count=0, edge=Edge.RISING, count_direction=CountDirection.COUNT_UP)  
		#Configure sample clock
		readTask.timing.cfg_samp_clk_timing(DAQ_MaxSamplingRate,DAQ_SampleClk,Edge.RISING,AcquisitionType.FINITE, NsampsPerDAQread)
		channel.ci_count_edges_term = 'PFI0'
		#Configure start trigger
		readArmTrig = readTask.triggers.arm_start_trigger
		readArmTrig.trig_type = TriggerType.DIGITAL_EDGE
		readArmTrig.dig_edge_src = DAQ_StartTrig

		channel.ci_count_edges_count_reset_enable = True
		channel.ci_count_edges_count_reset_term = DAQ_StartTrig
		channel.ci_count_edges_count_reset_active_edge = Edge.RISING

		#Create a reader for stream reading
		reader = CounterReader(readTask.in_stream)
		reader.verify_array_shape = False

	except Exception as excpt:
		print('Error configuring DAQ. Please check your DAQ is connected and powered. Exception details:', type(excpt).__name__,'.',excpt)
		closeDAQTask(task)
		sys.exit()
	return readTask, reader
def readDAQ(reader, N, timeout, array):
	try:
		test = reader.read_many_sample_double(array, number_of_samples_per_channel= N * 2, timeout = timeout)
	except Exception as excpt:
		print('Error: could not read DAQ. Please check your DAQ\'s connections. Exception details:', type(excpt).__name__,'.',excpt)
		sys.exit()
	return test
	
def closeDAQTask(task):
	task.close()
