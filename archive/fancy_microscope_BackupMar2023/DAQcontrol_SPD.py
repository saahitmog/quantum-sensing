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

DAQ_APDInput = "DEV1/ctr0"   ## the signal from single photon counter.
DAQ_APDTerm = 'PFI0'

def configureDAQ(Nsamples):
    try:
        #Create and configure a DAQ task
        NsampsPerDAQread=2*Nsamples
        readTask = nidaqmx.Task()
        
        #create a counter channel. 
        channel = readTask.ci_channels.add_ci_count_edges_chan(DAQ_APDInput,"", initial_count=0, edge=Edge.FALLING, count_direction=CountDirection.COUNT_UP)  
        channel.ci_count_edges_term = DAQ_APDTerm
        
        #Configure the arm start trigger --- this didn't throw an error, but doesn't work properly with a constant output - zhao 6/14/2022    === IT WORKS, see NV-NMR notes on July 5, 2022. 
        readArmTrig = readTask.triggers.arm_start_trigger
        readArmTrig.dig_edge_src = DAQ_StartTrig
        readArmTrig.trig_type = TriggerType.DIGITAL_EDGE
        #readArmTrig.trig_type = TriggerType.ANALOG_EDGE    ## trigger has to be digital edge or none  --- Possible Values: DAQmx_Val_None, DAQmx_Val_DigEdge
        readArmTrig.dig_edge_edge = Edge.RISING
        #readArmTrig.sync_type = SyncType.SLAVE
        #readArmTrig.dig_edge_dig_sync_enable = True
        
        
        #Configure sample clock
        readTask.timing.cfg_samp_clk_timing(DAQ_MaxSamplingRate,DAQ_SampleClk,Edge.FALLING,AcquisitionType.FINITE, NsampsPerDAQread)
        
        #Configure the counter reset signal   ---- counter resets work this way
        channel.ci_count_edges_count_reset_enable = True
        channel.ci_count_edges_count_reset_term = DAQ_SampleClk
        channel.ci_count_edges_count_reset_active_edge = Edge.RISING
        
        #Configure gate signal   --- however, this doesn't work
        #channel.ci_count_edges_gate_enable = True
        #channel.ci_count_edges_gate_term = DAQ_SampleClk
        
             
        #create a pulse width measurement channel 
        #channel = readTask.ci_channels.add_ci_pulse_width_chan(DAQ_APDInput, "", units = TimeUnits.TICKS)
        #                
        #readTask.PulseWidth.Input.Terminal = DAQ_AOM
        #readTask.PulseWidth.Timebase.Source = DAQ_APDTerm
        
        
    except Exception as excpt:
        print('Error configuring DAQ. Please check your DAQ is connected and powered. Exception details:', type(excpt).__name__,'.',excpt)
        closeDAQTask(readTask)
        #closeDAQTask(dummyTask)
        sys.exit()
    return readTask  #, dummyTask

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