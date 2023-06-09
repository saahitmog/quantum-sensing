
'''
Created on FEBRUARY 11, 2022

@author: Nishanth Anand

Based on code created on JULY 27, 2021 by
@author: Ed Barnard, Benedikt Ursprung
'''
from ScopeFoundry import Measurement, HardwareComponent
import numpy as np
import pyqtgraph as pg
import time
from datetime import datetime
import pandas as pd
import copy
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
from ScopeFoundry import h5_io
import SRScontrol as SRSctl
import AWGcontrol as AWGctl

class RabiMeasure(Measurement):

    name = "RABI"
    cutoff = 0

    def setup(self):

        # self.states = ['power', 'target_power']
        # for rate in self.states:
        #     self.settings.New('{}_visible'.format(rate), dtype=bool, initial=True)   
        self.settings.New('photon_mode', dtype=bool, initial=False)
        self.settings.New('AWG_mode', dtype=bool, initial=True)
        self.settings.New('Start_Duration', dtype=float, initial=1e-8, unit='s', si=True)
        self.settings.New('End_Duration', dtype=float, initial=6e-7, unit='s', si=True)      
        self.settings.New('Vpp', dtype=float, initial=0.2, spinbox_decimals=3, spinbox_step=0.01, unit='V', si=True)
        self.settings.New('MW_Frequency', dtype=float, initial=3.088, spinbox_decimals=4, unit='GHz', spinbox_step=0.001)
        self.settings.New('t_duration', dtype=float, initial=0.0005, unit='s', si=True)
        self.settings.New('MW_delay', dtype=float, initial=0.0005, unit='s', si=True)
        self.settings.New('N_pts', dtype=int, initial=101)
        self.settings.New('N_samples', dtype=int, initial=1000)
        self.settings.New('DAQtimeout', dtype=int, initial=10, unit='s')
        self.settings.New('magnet_current', dtype=float, initial=1.8)
        self.settings.New('Navg', dtype=int, initial=10)
        # self.settings.New('figsize_x', dtype=int, initial=9)
        # self.settings.New('figsize_y', dtype=int, initial=5)
        self.settings.New('plotting_type', dtype=str, initial='contrast')
        # self.settings.New('NThrow', dtype=int, initial=0)
        self.settings.New('fname_format', dtype=str, initial='{timestamp:%y%m%d_%H%M%S}_{measurement.name}_{sample}.{ext}')

        #self.on_new_history_len()
        #self.show_temperature()
        #self.settings.N_pts.add_listener(self.on_new_history_len)
        
        #self.hw = self.app.hardware['laser_quantum']
        
    def setup_figure(self):        
        ui_filename = sibling_path(__file__, "ESR_measurement.ui")
        self.ui = load_qt_ui_file(ui_filename)
        
        self.settings.activation.connect_to_widget(self.ui.run_checkBox)
        self.settings.N_pts.connect_to_widget(self.ui.N_pts_doubleSpinBox)
        self.settings.Navg.connect_to_widget(self.ui.Navg_doubleSpinBox)        
        # self.settings.show_temperature.connect_to_widget(self.ui.temperature_visible_checkBox)
        # self.settings.show_temperature.add_listener(self.show_temperature)

        #HS = self.hw.settings
        #HS.connected.connect_to_widget(self.ui.connected_checkBox)    
        #HS.target_power.connect_to_widget(self.ui.target_power_doubleSpinBox)
        #HS.status.connect_to_widget(self.ui.status_label)      
        #self.ui.on_pushButton.clicked.connect(self.hw.toggle_laser_on)
        #self.ui.off_pushButton.clicked.connect(self.hw.toggle_laser_off)   
        
        self.graph_layout = pg.GraphicsLayoutWidget()
        self.ui.channel_optimizer_GroupBox.layout().addWidget(self.graph_layout)
        self.plot = self.graph_layout.addPlot(title="Signal vs Duration")

        self.current_plotline = self.plot.plot()
        self.average_plotline = self.plot.plot()
        
        
        # self.plotlines = {}
        # self.avglines = {}
        # colors = ['r', 'g', 'r', 'y']
        # for i, rate in enumerate(self.states):
        #      self.plotlines.update({rate:self.plot.plot(pen=colors[i])})
        #      avg_line = pg.InfiniteLine(angle=0, movable=False, pen=colors[i % len(colors)])
        #     self.plot.addItem(avg_line)
        #     self.avglines.update({rate:avg_line})
    
    def run(self):
        #hw = self.hw

        self.set_progress(0)

        if(self.settings.photon_mode.value):
            import DAQcontrol_SPD as DAQ  ## single_photon_stream => replaced with DAQcontrol_SPD by zhao 7/19/2022
        else:
            import DAQ_Analog as DAQ
        
        starttime=time.time()
        # if(self.settings.plotting_type.value == 'signal'):
        #     self.plot = self.graph_layout.addPlot(title="Signal vs Duration")
        # else:
        #     self.plot = self.graph_layout.addPlot(title="Contrast vs Duration")

        # self.current_plotline = self.plot.plot()
        # self.average_plotline = self.plot.plot()

        f = self.settings['fname_format'].format(
             app=self,
             measurement=self,
             timestamp=datetime.fromtimestamp(starttime),
             sample=self.app.settings['sample'],
             ext='h5')
        fn = os.path.join(self.app.settings['save_dir'], f)
        if  not os.path.isdir(self.app.settings['save_dir']):
            os.mkdir(self.app.settings['save_dir'])
        h5_file = h5_io.h5_base_file(self.app, fname=fn, measurement=self)
        M = h5_io.h5_create_measurement_group(self, h5_file)

        start = time.process_time()

        if(self.settings.plotting_type.value != 'signal'):
            print("contrast mode")
        else:
            print("signal mode")

        # style.use("fivethirtyeight")
        #create figure and subplot, figsize can be changed in the global configuration document
        # fig = plt.figure(figsize = (self.settings.figsize_x.value, self.settings.figsize_y.value))
        # ax = fig.add_subplot(111)

        #sweep is a np array of frequency values that we will sweep across, step_size is the size of steps between
        sweep, step_size = np.linspace(self.settings.Start_Duration.value, self.settings.End_Duration.value, num = self.settings.N_pts.value, retstep = True)
        #sweep = np.arange(config['START_FREQUENCY'], config['END_FREQUENCY'] + config['STEP_FREQUENCY'], config['STEP_FREQUENCY'])
        print(sweep)
        #create a dictionary that will save signal and background information and will be exported to pandas df and then to a csv
        save_dict = {}
        save_dict['Duration'] = sweep

        #check AWG mode or SRS mode
        mode = 'SRS'
        if(self.settings.AWG_mode.value):
            mode = 'AWG'



        #create arrays to hold the average values across averaging runs
        length = self.settings.N_pts.value
        total_pts = length * self.settings.Navg.value
        self.average_x = sweep
        self.average_y = np.zeros(sweep.shape, dtype=float)

        #create arrays to hold realtime values during an averaging run, xs and ys will be plotted while signal and background are saved
        signal = np.zeros(sweep.shape, dtype=float)
        background = np.zeros(sweep.shape, dtype=float)
        self.xs = sweep
        self.ys = np.zeros(sweep.shape, dtype=float)

        #the data array holds new samples that come from a DAQ read since we're using stream readers
        data = np.zeros(self.settings.N_samples.value * 4)
        try:
            if(mode == 'AWG'):
                # TURN ON AWG AND INITIALIZE INST
                print('Process Id = {0}'.format(os.getpid()))
                admin = AWGctl.loadDLL()
                slotId = AWGctl.getSlotId(admin)
                if not slotId:
                    print("Invalid choice!")
                else:
                    inst = admin.OpenInstrument(slotId)
                    if not inst:
                        print("Failed to Open instrument with slot-Id {0}".format(slotId))  # @IgnorePep8
                        print("\n")
                    else:
                        instId = inst.InstrId
                AWGctl.instrumentSetup(inst)
                print('AWG Initialized')
            else:
            # #initiate RF generator with channel and model type; set amplitude
                # my_SRS = SRSctl.initSRS(27, 'SG384')
                # SRSctl.setSRS_RFAmplitude(my_SRS, self.settings.Vpp.value, units = "Vpp")
                # # #set test frequency and modulation; ESR has no modulation but that's handled in the modulation function
                # SRSctl.setSRS_Freq(my_SRS, self.settings.Start_Frequency.value, 'GHz') 
                # SRSctl.setupSRSmodulation(my_SRS, 'ESRseq') 
                # SRSctl.enableSRS_RFOutput(my_SRS)
                # print('SRS Initialized')
                pass
            #run the initPB function from the PBinit file 
            # # initPB()
            # # #Get the instruction Array
            # instructionArray = PBctl.programPB(config['sequence_name'], [config['t_AOM'] * ns])
            # print(instructionArray)
            # #Program the PulseBlaster
            # status = pb_start_programming(PULSE_PROGRAM)
            # for i in range(0, len(instructionArray)):
            # 	PBctl.pb_inst_pbonly(instructionArray[i][0],instructionArray[i][1],instructionArray[i][2],instructionArray[i][3])
            # pb_stop_programming()
            #Configure the DAQ
            task = DAQ.configureDAQ(self.settings.N_samples.value)
            #Function to close all running tasks
            def closeExp():
                # #turn off the microwave excitation
                # SRSctl.disableSRS_RFOutput(my_SRS) 

                # #stop the pulse blaster
                # pb_stop()
                # pb_close()
                # pb_reset()
                if(self.settings.AWG_mode.value):
                    AWGctl.SendScpi(inst, ":OUTP OFF")
                    rc = admin.CloseInstrument(instId)
                    AWGctl.Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)
                    rc = admin.Close()
                    AWGctl.Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)
                else:
                    SRSctl.disableSRS_RFOutput(my_SRS) 
                DAQ.closeDAQTask(task)
            
            # AWGctl.makeSingleESRSeq(inst, self.settings.t_AOM.value, self.settings.MW_Frequency.value, self.settings.Vpp.value)
            # AWGctl.makeSingleRabiSeq(inst, self.settings.Start_Duration.value, self.settings.MW_delay.value, self.settings.MW_Frequency.value, self.settings.Vpp.value)
            # time.sleep(1000)

            self.cutoff = 0
            for i in range(NThrow):
                DAQ.readDAQ(task, self.settings.N_samples.value, self.settings.DAQtimeout.value)
            for j in range(self.settings.Navg.value):
                self.ys = np.zeros(sweep.shape, dtype=float)
                for step in range(0, len(sweep)):
                    # time.sleep(0.3)
                    if self.interrupt_measurement_called:
                        print('end partial run')
                        M['run'+str(j)+'_data']=self.ys
                        #Save the signal and background arrays to the dictionary
                        save_dict['Signal Run ' + str(int(j))] = copy.deepcopy(signal)
                        save_dict['Background Run ' + str(int(j))] = copy.deepcopy(background)
                        return
                    #Get new frequency value
                    f = sweep[step]
                    if(mode == 'AWG'):
                        # #init AWG with new frequency
                        # if(f == self.settings.Start_Frequency.value):
                        # #if(True):
                        #     AWGctl.makeSingleESRSeq(inst, self.settings.t_AOM.value, f, self.settings.Vpp.value)
                        # else:
                        #     AWGctl.makeSingleESRSeqFast(inst, self.settings.t_AOM.value, f, self.settings.Vpp.value)
                        AWGctl.makeSingleRabiSeqMarker(inst, f, self.settings.MW_delay.value, self.settings.MW_Frequency.value, self.settings.Vpp.value)
                    else:    
                        #init RF generator with new frequency
                        # SRSctl.setSRS_Freq(my_SRS, f, 'GHz')
                        pass

                
                    #Read from the DAQ
                    counts = DAQ.readDAQ(task, self.settings.N_samples.value * 2, self.settings.DAQtimeout.value)
                    #the signal is the even points and background is the odd points from the data array
                    #counts = data[:self.settings.N_samples.value * 2]
                    #counts = data
                    current_signal = counts[0::2]
                    current_background = counts[1::2]
                
                    if step == 0:
                        print(counts[0:15])
                
                    #normalized_counts = np.diff(counts, prepend = counts[0])

                    #current_signal = normalized_counts[0::2]
                    #current_background = normalized_counts[1::2]
                    # for i in np.arange(0, int(len(counts)/2), 2):
                    #     current_signal[i] = counts[i]
                    #     current_background[i+1] = counts[i+1] - counts[i]

                    #average both arrays
                    sig_average = np.mean(current_signal)
                    back_average = np.mean(current_background)

                    #append signal to signal array and background to background array
                    signal[step] = sig_average
                    background[step] = back_average

                    #Depending on the plotting type, either append the signal or the contrast
                    if self.settings.plotting_type.value == 'signal':
                        self.ys[step] = sig_average
                    else:
                        #self.ys[step] = sig_average / back_average
                        self.ys[step] = np.divide(sig_average, back_average)
                
                    #Average the y correctly 
                    self.average_y[step] = ((self.average_y[step] * j) + self.ys[step]) / (j+1)
                    if(j == 0):
                        self.cutoff += 1
                    # self.cutoff += 1

                    fraction_complete = (j*length + step) / total_pts
                    self.set_progress(fraction_complete * 100)
                print('end averaging run')
                M['run'+str(j)+'_data']=self.ys
                #Save the signal and background arrays to the dictionary
                save_dict['Signal Run ' + str(int(j))] = copy.deepcopy(signal)
                save_dict['Background Run ' + str(int(j))] = copy.deepcopy(background)
        except Exception as err:
            print('EXCEPTED ERROR:'+str(err))
        finally:
            closeExp()
            # if(self.settings.AWG_mode.value):
            #     rc = admin.CloseInstrument(instId)
            #     AWGctl.Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)
            #     rc = admin.Close()
            #     AWGctl.Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)
            # else:
            #     SRSctl.disableSRS_RFOutput(my_SRS) 
            # DAQ.closeDAQTask(task)
            print('reached end')
            end = time.process_time()
            print('time elapsed: ' + str(end - start))
            f = self.settings['fname_format'].format(
            app=self,
            measurement=self,
            timestamp=datetime.fromtimestamp(starttime),
            sample=self.app.settings['sample'],
            ext='csv')
            fn = os.path.join(self.app.settings['save_dir'], f)  
            dataset = pd.DataFrame(save_dict)
            dataset.to_csv(fn)
            M['average_data'] = self.average_y
            M['sweep'] = self.average_x
            h5_file.close()
            # clean up here
            return
        
        #N_AVG = min(self.settings['avg_len'], self.settings['history_len'] - 1)
        N_AVG = self.settings['N_pts']-1
        q = ii - N_AVG
        if q >= 0:
            avg_val = self.optimize_history[q:ii, :].mean(axis=0)
        else:
            avg_val = self.optimize_history[:ii].mean(axis=0) * 1.0 * ii / N_AVG + self.optimize_history[q:].mean(axis=0) * (-q / N_AVG)
        
        # for i, rate in enumerate(self.states):
        #     self.plotlines[rate].setVisible(self.settings['{}_visible'.format(rate)])
        #     self.avglines[rate].setVisible(self.settings['{}_visible'.format(rate)] * self.settings['show_avg_lines'])
        #     if self.settings['{}_visible'.format(rate)]:
        #         title += '<b>\u03BC</b><sub>{}</sub> = {:3.0f} <br />'.format(rate, avg_val[i])
        #         self.plotlines[rate].setData(y=self.optimize_history[:, i])
        #         self.avglines[rate].setPos((0, avg_val[i]))

        self.plot.setTitle(title)
            
    
    def update_display(self):
        #self.current_plotline.setData(self.xs[:index+1], self.ys[:index+1])
        if(self.settings.plotting_type.value != 'signal'):
            self.plot.setTitle("Contrast vs Duration")
        else:
            self.plot.setTitle("Signal vs Duration")
        self.current_plotline.setData(self.average_x[:self.cutoff], self.average_y[:self.cutoff])
        
    # def show_temperature(self):
    #     for t in ['laser_temperature', 'PSU_temperature']:
    #         self.settings['{}_visible'.format(t)] = self.settings['show_temperature']
            
    #     for t in ['power', 'target_power']:
    #         self.settings['{}_visible'.format(t)] = not self.settings['show_temperature']




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
    #self.settings.N_pts = 101

    #runExperiment()

# def OnLoggerEvent(sender, e):
#     del sender
#     print(e.Message.Trim())
#     if (e.Level <= LogLevel.Warning):  # @UndefinedVariable
#         print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
#         print(e.Message.Trim())
#         print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~")


# def Validate(rc, condExpr, funcName="", lineNumber=0):
#     _ = condExpr

#     # cond = (rc == 0)

#     if rc != 0:
#         errMsg = "Assertion \"{0}\" Failed at line {1} of {2}."
#         errMsg = errMsg.format(rc, lineNumber, funcName)
#         raise Exception(errMsg)

# def getSlotId(admin):
#     try:
#         if admin.IsOpen():
#             rc = admin.Close()
#             Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)

#         rc = admin.Open()
#         Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)

#         slotIds = admin.GetSlotIds()
#         n = 0
#         for i in range(0, slotIds.Length, 1):
#             slotId = slotIds[i]
#             slotInfo = admin.GetSlotInfo(slotId)
#             if slotInfo:
#                 if not slotInfo.IsDummySlot:
#                     n = n + 1
#                     print(("{0}. Slot-ID {1} [chassis {2}, slot {3}], "
#                            "IsDummy={4}, IsInUse={5}, IDN=\'{6}\'").
#                           format(i + 1,
#                                  slotId,
#                                  slotInfo.ChassisIndex,
#                                  slotInfo.SlotNumber,
#                                  'Yes' if slotInfo.IsDummySlot != 0 else 'No',
#                                  'Yes' if slotInfo.IsSlotInUse != 0 else 'No',
#                                  slotInfo.GetIdnStr()))
#                 else:
#                     dummy = 1
#                     # print("{0}. Slot-ID {1} - Failed to acquire Slot Info".
#                     # .format(i + 1,slotId))

#         if n == 1:
#             sel = slotIds[0]
#         else:
#             sel = input("Please select slot-Id:")
#         slotId = np.uint32(sel)
#     except Exception as e:  # pylint: disable=broad-except
#         print(e)
#     return slotId


# def loadDLL():

#     # Load .NET DLL into memory
#     # The R lets python interpret the string RAW
#     # So you can put in Windows paths easy
#     # clr.AddReference(R'D:\Projects\Alexey\ProteusAwg\PyScpiTest\TEPAdmin.dll')

#     #winpath = os.path.join(os.environ['WINDIR'], 'System32')
  
#     winpath = R'C:\Windows\System32'

#     winpath = os.path.join(winpath, 'TEPAdmin.dll')

#     clr.AddReference(winpath)

#     # pylint: disable=import-error
#     from TaborElec.Proteus.CLI.Admin import CProteusAdmin  # @UnresolvedImport

#     from TaborElec.Proteus.CLI.Admin import IProteusInstrument  # @UnusedImport @UnresolvedImport @IgnorePep8

#     return CProteusAdmin(OnLoggerEvent)


# def SendBinScpi(inst, prefix, path, query_err=False):

#     err_code, resp_str = -1, ''
#     try:
#         print(prefix)
#         inBinDat = bytearray(path, "utf8")
#         inBinDatSz = np.uint64(len(inBinDat))
#         DummyParam = np.uint64(0)
#         res = inst.WriteBinaryData(prefix, inBinDat, inBinDatSz, DummyParam)

#         err_code = int(res.ErrCode)
#         resp_str = str(res.RespStr).strip()

#         if 0 != err_code:
#             print("Error {0} ({1})".format(err_code, resp_str))
#         elif len(resp_str) > 0:
#             print("{0}".format(resp_str))
#         if query_err:
#             err = inst.SendScpi(':SYST:ERR?')
#             if not err.RespStr.startswith('0'):
#                 print(err.RespStr)
#                 err = inst.SendScpi('*CLS')

#     except Exception as e:  # pylint: disable=broad-except
#         print(e)

#     return err_code, resp_str


# def SendScpi(inst, line, query_err=False, print_line=True):

#     err_code, resp_str = -1, ''
#     try:
#         if print_line:
#             print(line)
#         line = line + "\n"
#         res = inst.SendScpi(str(line))
#         err_code = int(res.ErrCode)
#         resp_str = str(res.RespStr).strip()

#         if 0 != err_code:
#             if not print_line:
#                 print(line.strip())
#             print("Error {0} - ({1})".format(err_code, resp_str))
#         elif len(resp_str) > 0 and print_line:
#             print("{0}".format(resp_str))
#         if query_err:
#             err = inst.SendScpi(':SYST:ERR?')
#             if not err.RespStr.startswith('0'):
#                 print(err.RespStr)
#                 err = inst.SendScpi('*CLS')
#     except Exception as e:  # pylint: disable=broad-except
#         print(e)

#     return err_code, resp_str
    
# def scaleWaveform(rawSignal, model):

#     if model == "P9082M":  # 9GS/s
#         bits = 8
#         wpt_type = np.uint8
#     else:  # 2GS/s or 1.25GS/s models
#         bits = 16
#         wpt_type = np.uint16

#     maxSig = max(rawSignal)
#     verticalScale = ((pow(2, bits))/2)-1
#     vertScaled = (rawSignal/maxSig) * verticalScale
#     dacSignal = (vertScaled + verticalScale)
#     dacSignal = dacSignal.astype(wpt_type)
    
#     if max(dacSignal) > 256:
#         dacSignal16 = []
#         for i in range(0,len(dacSignal)*2):
#             dacSignal16.append(0)
            
#         j=0
#         for i in range(0,len(dacSignal)):
#             dacSignal16[j] = dacSignal[i] & 0x0f
#             dacSignal16[j+1] = dacSignal[i] >> 8
#             j=j+2
#         dacSignal = dacSignal16
    
#     return(dacSignal);
    
# def pulseWave(segmentLength, cycles, onTime):
    
#     segmentLengthOn = int(onTime * segmentLength)
#     segmentLengthOff = int((1-onTime) * segmentLength)
#     time = np.linspace(0, segmentLengthOn-1, segmentLengthOn)
#     omega = 2 * np.pi * cycles
#     rawSignalOn = np.sin(omega*time/segmentLength)
#     rawSignalOff = np.array(np.zeros(segmentLengthOff)) 
#     rawSignal = np.concatenate([rawSignalOn,rawSignalOff])
    
#     return(rawSignal);

# def instrumentSetup(inst, sampleRateDAC = 9E9):
    
#     query_syst_err = True      
    
#     res = SendScpi(inst, ":SYST:INF:MODel?")
    
#     model = res[1]

#     # Module 1
#     SendScpi(inst, ":INST:ACTive 1", query_syst_err)

#     # get hw option
#     SendScpi(inst, "*IDN?")
#     SendScpi(inst, "*OPT?")
#     # reset - must!
#     SendScpi(inst, "*CLS", query_syst_err)
#     # reset - must!
#     SendScpi(inst, "*RST", query_syst_err)

#     # set sampling DAC freq.
#     SendScpi(inst, ":FREQ:RAST {0}".format(sampleRateDAC), query_syst_err)  
    
#     #^^^^ set once
# def instrumentCalls(inst, waveform, vpp=0.001, offset=0):
#     query_syst_err = True  
    
#     dacSignal = waveform
    
#     # ---------------------------------------------------------------------
#     # DAC functions CH 1 
#     # ---------------------------------------------------------------------

#     # select channel
#     SendScpi(inst, ":INST:CHAN 1", query_syst_err)

#     # load I waveform into instrument
#     segNum = 1
#     SendScpi(inst, ":TRACe:DEF {0},{1}".format(segNum, len(dacSignal)), query_syst_err)
#     SendScpi(inst, ":TRACe:SEL {0}".format(segNum), query_syst_err)

#     prefix = ':TRAC:DATA 0,#'
#     print(prefix, end=' .. ')

#     res = inst.WriteBinaryData(prefix, dacSignal.tobytes())
#     Validate(res.ErrCode, __name__, inspect.currentframe().f_back.f_lineno)

#     res = SendScpi(inst, ":SYST:ERR?", False, False)
#     print(res[1])

#     # Vpp for output
#     SendScpi(inst, ":SOUR:VOLT {0}".format(vpp))

#     # sel segment 1 - play I
#     SendScpi(inst, ":SOUR:FUNC:MODE:SEGM {0}".format(segNum), query_syst_err) 
    
#     trig_lev = 128
#     enableTrigger(inst, trig_lev, 1)

#     # connect ouput
#     SendScpi(inst, ":OUTP ON", query_syst_err)

#     #MARKER CODE >>>>
#     SendScpi(inst, ":MARK OFF")
      
#     # enble marker 1 CH 1
#     offTime = offset
#     onTime = int(len(dacSignal)/8)-offset
#     markerWave = []
#     for i in range(0,offTime):
#         markerWave.append(0)
#     for i in range(0,onTime):
#         markerWave.append(1)  
#     markerWave = np.uint8(markerWave)
       
#     prefix = ':MARK:DATA 0,#'
#     print(prefix, end=' .. ')
#     res = inst.WriteBinaryData(prefix, markerWave.tobytes())
#     Validate(res.ErrCode, __name__, inspect.currentframe().f_back.f_lineno)

#     SendScpi(inst, ":MARK:VOLT:PTOP 1")
#     SendScpi(inst, ":MARK:SEL 1")
#     SendScpi(inst, ":MARK ON")

# def enableTrigger(inst, trig_lev, trig_channel):
#     SendScpi(inst, ":TRIG:SOUR:ENAB TRG{0}".format(trig_channel)) # Set tigger enable signal to TRIG1 (CH specific)
#     SendScpi(inst, ":TRIG:SEL TRG1") # Select trigger for programming (CH specific)
#     SendScpi(inst, ":TRIG:LEV 0.1") # Set trigger level
#     SendScpi(inst, ":TRIG:COUN 1") # Set number of waveform cycles (1) to generate (CH specific)
#     SendScpi(inst, ":TRIG:IDLE DC") # Set output idle level to DC (CH specific)
#     SendScpi(inst, ":TRIG:IDLE:LEV {0}".format(trig_lev)) # Set DC level in DAC value (CH specific)
#     SendScpi(inst, ":TRIG:STAT ON") # Enable trigger state (CH specific)
#     SendScpi(inst, ":INIT:CONT OFF") # Enable trigger mode (CH specific)
#     SendScpi(inst, ":TRIG:GATE:STAT OFF") #Disable trigger gated mode

#     # SendScpi(inst, ":TRIG:SOUR:ENAB TRG{0}".format(trig_channel)) # Set tigger enable signal to TRIG1 (CH specific)
#     # SendScpi(inst, ":TRIG:SEL TRG1") # Select trigger for programming (CH specific)
#     # #SendScpi(inst, ":TRIG:LEV 0.5") # Set trigger level
#     # SendScpi(inst, ":TRIG:COUN 0") # Set number of waveform cycles (1) to generate (CH specific)
#     # SendScpi(inst, ":TRIG:IDLE DC") # Set output idle level to DC (CH specific)
#     # SendScpi(inst, ":TRIG:IDLE:LEV {0}".format(trig_lev)) # Set DC level in DAC value (CH specific)
#     # SendScpi(inst, ":TRIG:STAT ON") # Enable trigger state (CH specific)
#     # SendScpi(inst, ":INIT:CONT OFF") # Enable trigger mode (CH specific)
#     # SendScpi(inst, ":TRIG:GATE:STAT OFF") #Disable trigger gated mode

# def sinePulse(segmentLength, bits, squareCycles, sinCycles, duty, amp):
    
#     time = np.linspace(0, segmentLength-1, segmentLength)
#     omegaSquare = 2 * np.pi * squareCycles
#     omegaSin = 2 * np.pi * sinCycles
#     rawSignal = ((sg.square(omegaSquare*time/segmentLength, duty)+1)/2) *amp*np.sin(omegaSin*time/segmentLength)

#     dacSignal = scaleWaveform(rawSignal, "P9082M")

#     return(dacSignal);

# def squareWave(segmentLength):
#     time = np.linspace(0, segmentLength-1, segmentLength)
#     print(sg.square(time))
#     return scaleWaveform(sg.square(time),"P9082M")


# def sinePulseOffset(segmentLength, bits, squareCycles, sinCycles, duty, amp, offset):
#     time = np.linspace(0, segmentLength-1, segmentLength)
#     omegaSquare = 2 * np.pi * squareCycles
#     omegaSin = 2 * np.pi * sinCycles
#     squareSignal = np.roll((sg.square(omegaSquare*time/segmentLength, duty)+1)/2, offset)
#     squareSignal[:offset] = [0] * offset
#     rawSignal = (squareSignal*amp*np.sin(omegaSin*time/segmentLength))
    
#     dacSignal = scaleWaveform(rawSignal, "P9082M")

#     return(dacSignal);

# def makeESRseq(inst, t_duration, mw_duration, startFreq, endFreq, vpp = 0.001, freqStep=1):
#     #t_duration is total duration
#     #mw_duration is microwave duration
#     #Frequency (GHz) 10-1000 Integer val
#     # freq = startFreq
#     # while freq < endFreq:
#     #     segmentLength = 2499968
#     #     cycles = int(freq * segmentLength * 1e6 / 9e9)
#     #     squares = int((1/(t_duration / 1e6)) * segmentLength / 9e9)
#     #     duty = mw_duration / t_duration
#     #     instrumentCalls(inst, sinePulse(segmentLength, 8, squares, cycles, duty, 1))
#     #     freq += freqStep
#     freq = startFreq
#     instrumentSetup(inst)
#     while freq <= endFreq:
#         segmentLength = 4999936
#         cycles = int(freq * segmentLength * 1e9 / 9e9)
#         squares = int((1/(t_duration / 1e6)) * segmentLength / 9e9)
#         duty = mw_duration / t_duration
#         print('Frequency: {0} GHz'.format(freq))
#         instrumentCalls(inst, sinePulse(segmentLength, 8, squares, cycles, duty, 1), vpp)
#         freq += freqStep

# def makeSingleESRSeq(inst, duration, freq, vpp = 0.001):
#     segmentLength = 4999936
#     segmentLength = 8998848 #this segment length is optimized for 1kHz trigger signal
#     cycles = int(freq * segmentLength * 1e9 / 9e9)
#     squares = int((1/(duration / 1e6)) * segmentLength / 9e9)
#     duty = 0.5
#     print('Frequency: {0} GHz'.format(freq))
#     instrumentCalls(inst, sinePulse(segmentLength, 8, squares, cycles, duty, 1), vpp)

# def makeReadoutDelaySweep(inst, t_duration, mw_duration, freq, delayStart, delayStop, vpp = 0.001, delayStep=0.1):
#     #delay in microseconds
#     instrumentSetup(inst)
#     t_readoutDelay = delayStart
#     while t_readoutDelay <= delayStop:
#         tot_duration = t_duration + t_readoutDelay
#         segmentLength = 4999936
#         cycles = int(freq * segmentLength * 1e9 / 9e9)
#         squares = int((1/(tot_duration / 1e6)) * segmentLength / 9e9)
#         duty = mw_duration / tot_duration
#         offset = int(2*np.pi*t_readoutDelay/tot_duration)
#         print('Delay: {0} us'.format(t_readoutDelay))
#         instrumentCalls(inst, sinePulseOffset(segmentLength, 8, squares, cycles, duty, 1, offset), vpp)
#         t_readoutDelay += delayStep
#         time.sleep(5)

# def makeRabiSeq(inst, t_duration, freq, mwStart, mwStop, vpp = 0.001, mwStep=0.1):
#     #delay in microseconds
#     instrumentSetup(inst)
#     mw_duration = mwStart
#     while mw_duration <= mwStop:
#         segmentLength = 4999936
#         segmentLength = 8998848 #this segment length is optimized for 1kHz trigger signal
#         cycles = int(freq * segmentLength * 1e9 / 9e9)
#         squares = int((1/(t_duration / 1e6)) * segmentLength / 9e9)
#         duty = mw_duration / t_duration
#         # offset = int(2*np.pi*t_readoutDelay/t_duration)
#         offset = 0
#         print('MW duration: {0} us'.format(mw_duration))
#         instrumentCalls(inst, sinePulseOffset(segmentLength, 8, squares, cycles, duty, 1, offset), vpp)
#         mw_duration += mwStep
#         time.sleep(5)

# def makeT1Seq(t_delay,t_AOM,t_readoutDelay,t_pi):
#     return
# def makeT2Seq(t_delay,t_AOM,t_readoutDelay,t_pi,IQpadding, numberOfPiPulses):
#     return
# def makeXY8seq(t_delay,t_AOM,t_readoutDelay,t_pi,IQpadding, numberOfRepeats):
#     return
# def makecorrelationSpectSeq(t_delay_betweenXY8seqs,t_delay, t_AOM,t_readoutDelay,t_pi,IQpadding,numberOfRepeats):
#     return
# def makeCPMGpulses(start_delay,numberOfPiPulses,t_delay,t_pi, t_piby2,IQpadding):
#     return
# def makeXY8pulses(start_delay,numberOfRepeats,t_delay,t_pi, t_piby2,IQpadding):
#     return	
# import AWGcontrol as AWGctl
# # def run(config_dic):
# #     global config
# #     config = config_dic
# #     runExperiment()

# def runExperiment():
#     try:
#         start = time.process_time()

#         self.settings.N_pts.update_value(new_val=int(self.settings.N_pts.value))
#         self.settings.N_samples.update_value(new_val=int(self.settings.N_samples.value))
#         #Setup plotting style
#         style.use("fivethirtyeight")
#         #create figure and subplot, figsize can be changed in the global configuration document
#         fig = plt.figure(figsize = (self.settings.figsize_x.value, self.settings.figsize_y.value))
#         ax = fig.add_subplot(111)

#         #sweep is a np array of frequency values that we will sweep across, step_size is the size of steps between
#         sweep, step_size = np.linspace(self.settings.Start_Frequency.value, self.settings.End_Frequency.value, num = self.settings.N_pts.value, retstep = True)
#         #sweep = np.arange(config['START_FREQUENCY'], config['END_FREQUENCY'] + config['STEP_FREQUENCY'], config['STEP_FREQUENCY'])
#         print(sweep)
#         #create a dictionary that will save signal and background information and will be exported to pandas df and then to a csv
#         save_dict = {}
#         save_dict['Frequency'] = sweep


#         #create arrays to hold the average values across averaging runs
#         length = self.settings.N_pts.value
#         total_pts = length * self.settings.Navg.value
#         average_x = sweep
#         average_y = np.zeros(length)

#         #create arrays to hold realtime values during an averaging run, xs and ys will be plotted while signal and background are saved
#         signal = np.zeros(length)
#         background = np.zeros(length)
#         xs = sweep
#         ys = np.zeros(length)

#         #the data array holds new samples that come from a DAQ read since we're using stream readers
#         data = np.zeros(self.settings.N_samples.value * 4)

#         #plot the data for the first time and get the line variable (which isn't really used)
#         line, = ax.plot(xs, ys, 'b-')
        
#         # #initiate RF generator with channel and model type; set amplitude
#         # my_SRS = SRSctl.initSRS(27, 'SG386') 

#         # SRSctl.setSRS_RFAmplitude(my_SRS, config['V_pp'], units = "Vpp") 

#         # #set test frequency and modulation; ESR has no modulation but that's handled in the modulation function
#         # SRSctl.setSRS_Freq(my_SRS, config['START_FREQUENCY'], 'GHz') 
#         # SRSctl.setupSRSmodulation(my_SRS, config['sequence_name']) 

#         # #run the initPB function from the PBinit file 
#         # initPB()

#         # #Get the instruction Array
#         # instructionArray = PBctl.programPB(config['sequence_name'], [config['t_AOM'] * ns])
#         # print(instructionArray)

#         # #Program the PulseBlaster
#         # status = pb_start_programming(PULSE_PROGRAM)
#         # for i in range(0, len(instructionArray)):
#         # 	PBctl.pb_inst_pbonly(instructionArray[i][0],instructionArray[i][1],instructionArray[i][2],instructionArray[i][3])
#         # pb_stop_programming()

#         #Configure the DAQ
#         task = DAQ.configureDAQ(self.settings.N_samples.value)

#         #TURN ON AWG AND INITIALIZE INST
#         print('Process Id = {0}'.format(os.getpid()))
#         admin = AWGctl.loadDLL()
#         slotId = AWGctl.getSlotId(admin)
#         if not slotId:
#             print("Invalid choice!")
#         else:
#             inst = admin.OpenInstrument(slotId)
#             if not inst:
#                 print("Failed to Open instrument with slot-Id {0}".format(slotId))  # @IgnorePep8
#                 print("\n")
#             else:
#                 instId = inst.InstrId
#         AWGctl.instrumentSetup(inst)
#         # #turn on the microwave excitation 
#         # SRSctl.enableSRS_RFOutput(my_SRS)

#         #Function to close all running tasks
#         def closeExp():
#             # #turn off the microwave excitation
#             # SRSctl.disableSRS_RFOutput(my_SRS) 

#             # #stop the pulse blaster
#             # pb_stop()
#             # pb_close()
#             # pb_reset()
#             AWGctl.SendScpi(inst, ":OUTP OFF")
#             rc = admin.CloseInstrument(instId)
#             AWGctl.Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)
#             rc = admin.Close()
#             AWGctl.Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)
#             #Close the DAQ once we are done
#             #DAQ.closeDAQTask(task)
#             return

#         # #Function to save data 
#         # def save():
#         #     #check if user wants to save the plot
#         #     #saved = input("Save plot? y/n")
#         #     saved = 'y'
#         #     if saved == 'y':
#         #         #name = input("Enter a filename:")
#         #         name = config['folder'] + '/' + config['name'] + '_' + str(config['magnet_power'])
#         #         #save the figure
#         #         plt.savefig(name + '.png')

#         #         #save the pandas dataframe with background, signal, and frequency
#         #         dataset = pd.DataFrame(save_dict)
#         #         dataset.to_csv(name + '.csv')

#         #         #closeExp()
#         #         #sys.exit()

#         #     #elif saved == 'n':
#         #         #closeExp()
#         #         #sys.exit()
#         #         #x=0
#         #     #else:
#         #     #	print('Error, try again')
#         #     #	save()

#         #start the pulse blaster with the sequence that was programmed
#         # pb_start()
#         AWGctl.makeSingleESRSeq(inst, self.settings.t_AOM.value, self.settings.Start_Frequency.value, self.settings.Vpp.value)
#         #Throw away the first NThrow samples to get the photon counter warmed up (not really necessary)
#         for i in range(NThrow):
#             DAQ.readDAQ(task, self.settings.N_samples.value, self.settings.DAQtimeout.value)

#         #Init function used by FuncAnimation to setup the initial plot; only used if blit = True
#         def init():
#             line.set_data([], [])
#             return line, 

#         #Initialize f to be the start frequency, avg_run to be 0, and step to be 0
#         f = sweep[0]
#         avg_run = 0
#         step = 0
#         begin = time.time()
#         close = True
#         #This is the function that runs the experiment and does the plotting
#         #This is the function that runs the experiment and does the plotting
#         def animate(k):
#             #Defines f,avg_run,step as global variables so we can update between function calls
#             nonlocal f
#             nonlocal avg_run
#             nonlocal step
#             nonlocal close

#             #If f goes past end frequency, we are done
#             if step >= length:
#                 #Save the signal and background arrays to the dictionary
#                 save_dict['Signal Run ' + str(int(avg_run))] = copy.deepcopy(signal)
#                 save_dict['Background Run ' + str(int(avg_run))] = copy.deepcopy(background)

#                 #if we haven't finished all averaging runs yet, reset all temp variables and continue
#                 if avg_run < config['Navg'] - 1:
#                     f = sweep[0]
#                     step = 0
#                     avg_run += 1
#                     return 

#                 #get the end of the progress time and calculate time elapsed
#                 end = time.process_time()
#                 print('time elapsed: ' + str(end - start))
#                 closeExp()
#                 # save()
#                 plt.close(fig)
#                 close = False
#                 return None

#             #Otherwise, increment the frequency and continue
#             else:
#                 #Get new frequency value
#                 f = sweep[step]

#                 #init RF generator with new frequency
#                 # SRSctl.setSRS_Freq(my_SRS, f, 'GHz')
#                 #init AWG with new frequency
#                 AWGctl.makeSingleESRSeq(inst, self.settings.t_AOM.value, f, self.settings.Vpp.value)
                
#                 #Read from the DAQ
#                 data = DAQ.readDAQ(task, self.settings.N_samples * 2, config['DAQtimeout'])
#                 #the signal is the even points and background is the odd points from the data array
#                 counts = data[:self.settings.N_samples * 2]
#                 current_signal = counts[0::2]
#                 current_background = counts[1::2]
                
#                 if step == 0:
#                     print(counts[0:15])
                
#                 #normalized_counts = np.diff(counts, prepend = counts[0])

#                 #current_signal = normalized_counts[0::2]
#                 #current_background = normalized_counts[1::2]
#                 for i in np.arange(0, int(len(counts)/2), 2):
#                     current_signal[i] = counts[i]
#                     current_background[i+1] = counts[i+1] - counts[i]

#                 #average both arrays
#                 sig_average = np.mean(current_signal)
#                 back_average = np.mean(current_background)

#                 #append signal to signal array and background to background array
#                 signal[step] = sig_average
#                 background[step] = back_average

#                 #Depending on the plotting type, either append the signal or the contrast
#                 if self.settings.plotting_type == 'signal':
#                     ys[step] = sig_average
#                 else:
#                     ys[step] = sig_average / back_average
                
#                 #Average the y correctly 
#                 average_y[step] = ((average_y[step] * avg_run) + ys[step]) / (avg_run+1)

#                 #plot the new data, we plot the entire average arrays, but we only plot the realtime data up to what we have so far
#                 ax.clear()
#                 ax.plot(xs[:step + 1], ys[:step + 1], 'o')
#                 if avg_run == 0:
#                     ax.plot(average_x[:step + 1], average_y[:step + 1], 'r-')
#                 else:
#                     ax.plot(average_x, average_y, 'r-')

#                 #Make the plot look good
#                 plt.xticks(rotation=45, ha='right')
#                 plt.subplots_adjust(bottom=0.30)
#                 plt.title('Photo Counter Readout vs Frequency')
#                 plt.ylabel('Photon Counts')
#                 plt.xlabel('Frequency (GHz)')

#                 #If we are starting a new averaging run, print it
#                 if step == 0:
#                     print('Starting Averaging Round: ' + str(avg_run))
#                 step += 1

#                 #Test code to calculate the % complete and time left for the experiment
#                 pts_complete = (avg_run * length) + step
#                 fraction_complete = (pts_complete / total_pts) 
#                 intermediate_time = time.time()
#                 time_spent = intermediate_time - begin
#                 time_left = (time_spent / fraction_complete) - time_spent
#                 if step % 10 == 0:
#                     print('Percent Complete: ' + str(int((fraction_complete * 100))))
#                     print('Approx. Time Left (s): ' + str(int(time_left)))
#         #Begin the animation - All of the experiment work is done in the animate function
#         ani = animation.FuncAnimation(fig, animate, init_func = init, interval = 1, blit = False, frames = int(total_pts) + 2, repeat = False) 
#         plt.show()
#         return None
#     finally:
#         return None
