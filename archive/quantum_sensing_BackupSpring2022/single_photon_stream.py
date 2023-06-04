import nidaqmx
import nidaqmx.system
from  nidaqmx.constants import *
from connectionConfig import *
import numpy as np
import sys
from nidaqmx.stream_readers import CounterReader

#system = nidaqmx.system.System.local()
DAQ_APDInput = "DEV1/ctr0"   ## the signal from single photon counter.

# def configureDAQ(Nsamples):
# 	try:
# 		NsampsPerDAQread=2*Nsamples
# 		readTask = nidaqmx.Task()
# 		channel = readTask.ci_channels.add_ci_count_edges_chan(DAQ_APDInput,"", initial_count=0, edge=Edge.RISING, count_direction=CountDirection.COUNT_UP)  
# 		#Configure sample clock
# 		readTask.timing.cfg_samp_clk_timing(DAQ_MaxSamplingRate,DAQ_SampleClk,Edge.RISING,AcquisitionType.FINITE, NsampsPerDAQread)
# 		channel.ci_count_edges_term = 'PFI0'
# 		#Configure start trigger
# 		readArmTrig = readTask.triggers.arm_start_trigger
# 		readArmTrig.trig_type = TriggerType.DIGITAL_EDGE
# 		readArmTrig.dig_edge_src = DAQ_StartTrig

# 		channel.ci_count_edges_count_reset_enable = True
# 		channel.ci_count_edges_count_reset_term = DAQ_StartTrig
# 		channel.ci_count_edges_count_reset_active_edge = Edge.RISING

# 		#Create a reader for stream reading
# 		reader = CounterReader(readTask.in_stream)
# 		reader.verify_array_shape = False

# 	except Exception as excpt:
# 		print('Error configuring DAQ. Please check your DAQ is connected and powered. Exception details:', type(excpt).__name__,'.',excpt)
# 		closeDAQTask(task)
# 		sys.exit()
# 	return readTask, reader
def configureDAQ(Nsamples):
    try:
        #Create and configure a DAQ task
        NsampsPerDAQread=2*Nsamples
        readTask = nidaqmx.Task()
        #create a counter channel. 
        channel = readTask.ci_channels.add_ci_count_edges_chan(DAQ_APDInput,"", initial_count=0, edge=Edge.RISING, count_direction=CountDirection.COUNT_UP)  
        channel.ci_count_edges_term = 'PFI0'

        readTask.timing.cfg_samp_clk_timing(DAQ_MaxSamplingRate,DAQ_SampleClk,Edge.RISING,AcquisitionType.FINITE, NsampsPerDAQread)
        #Configure gate signal
        #channel.ci_count_edges_gate_term = DAQ_SampleClk
        #channel.ci_count_edges_gate_enable = True
        
        #Configure the counter reset signal
        channel.ci_count_edges_count_reset_enable = True
        channel.ci_count_edges_count_reset_term = DAQ_StartTrig
        channel.ci_count_edges_count_reset_active_edge = Edge.RISING
        #print(channel.ci_count_edges_gate_enable)
        
        #Configure the arm start trigger
        #readArmTrig = readTask.triggers.arm_start_trigger
        #readArmTrig.dig_edge_src = DAQ_StartTrig
        #readArmTrig.trig_type = TriggerType.DIGITAL_EDGE
        #readArmTrig.dig_edge_edge = Edge.RISING
        #readArmTrig.sync_type = SyncType.SLAVE
        #readArmTrig.dig_edge_dig_sync_enable = True
        #create a dummy analog channel
        #dummyTask = nidaqmx.Task()
        #dummyAI = dummyTask.ai_channels.add_ai_voltage_chan(DAQ_DummyInput,"",TerminalConfiguration.DEFAULT,minVoltage,maxVoltage,VoltageUnits.VOLTS)
        
        #Configure sample clock
        readTask.timing.cfg_samp_clk_timing(DAQ_MaxSamplingRate,DAQ_SampleClk,Edge.RISING,AcquisitionType.FINITE, NsampsPerDAQread)
        
        #dummyTask.timing.cfg_samp_clk_timing(DAQ_MaxSamplingRate,DAQ_SampleClk,Edge.RISING,AcquisitionType.FINITE, NsampsPerDAQread)
        #Configure start trigger on dummy task
        #dummyStartTrig = dummyTask.triggers.start_trigger
        #dummyStartTrig.cfg_anlg_edge_start_trig("Dev1/ai0")
        #dummyStartTrig.cfg_dig_edge_start_trig(DAQ_StartTrig,Edge.RISING)
        #print(dummyStartTrig.sync_type)
        #dummyStartTrig.retriggerable = True
        #dummyStartTrig.sync_type = SyncType.MASTER
        #readStartTrig = readTask.triggers.start_trigger
        #readStartTrig.sync_type = SyncType.MASTER
        
        
    except Exception as excpt:
        print('Error configuring DAQ. Please check your DAQ is connected and powered. Exception details:', type(excpt).__name__,'.',excpt)
        closeDAQTask(readTask)
        #closeDAQTask(dummyTask)
        sys.exit()
    return readTask  #, dummyTask

# def readDAQ(reader, N, timeout, array):
# 	try:
# 		test = reader.read_many_sample_double(array, number_of_samples_per_channel= N * 2, timeout = timeout)
# 	except Exception as excpt:
# 		print('Error: could not read DAQ. Please check your DAQ\'s connections. Exception details:', type(excpt).__name__,'.',excpt)
# 		sys.exit()
# 	return test
def readDAQ(task, N, timeout):
    try:
        #dummy.start()  ## the dummy task to enable trigger.
        counts = task.read(N,timeout)
        #dummy.stop()
    except Exception as excpt:
        print('Error: could not read DAQ. Please check your DAQ\'s connections. Exception details:', type(excpt).__name__,'.',excpt)
        sys.exit()
    return counts
	
def closeDAQTask(task):
	task.close()
