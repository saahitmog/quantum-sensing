
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

class T1ImageMeasure(Measurement):

    name = "T1Image"
    cutoff = 0

    def setup(self):

        # self.states = ['power', 'target_power']
        # for rate in self.states:
        #     self.settings.New('{}_visible'.format(rate), dtype=bool, initial=True)   
        self.settings.New('photon_mode', dtype=bool, initial=False)
        self.settings.New('AWG_mode', dtype=bool, initial=True)
        self.settings.New('Start_Duration', dtype=float, initial=0.000001, unit='s', si=True)
        self.settings.New('End_Duration', dtype=float, initial=0.01, unit='s', si=True)      
        self.settings.New('Vpp', dtype=float, initial=0.2, spinbox_decimals=3, spinbox_step=0.01, unit='V', si=True)
        self.settings.New('MW_Frequency', dtype=float, initial=3.643, spinbox_decimals=4, unit='GHz', spinbox_step=0.001)
        self.settings.New('t_AOM', dtype=float, initial=0.0005, unit='s', si=True)
        self.settings.New('t_readoutDelay', dtype=float, initial=0.0004, unit='s', si=True)
        self.settings.New('t_pi', dtype=float, initial=0.000000082, unit='s', si=True)
        self.settings.New('N_pts', dtype=int, initial=101)
        self.settings.New('N_samples', dtype=int, initial=1000)
        self.settings.New('DAQtimeout', dtype=int, initial=10, unit='s')
        self.settings.New('magnet_current', dtype=float, initial=0.6)
        # self.settings.New('Navg', dtype=int, initial=10)
        self.settings.New('x_steps', dtype=int, initial=10)
        self.settings.New('y_steps', dtype=int, initial=10)
        self.settings.New('x_step_size', dtype=int, initial=5, unit='um')
        self.settings.New('y_step_size', dtype=int, initial=5, unit='um')
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
        # self.settings.Navg.connect_to_widget(self.ui.Navg_doubleSpinBox)        
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
        self.plot = self.graph_layout.addPlot(title="Signal vs Pulse Duration")

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
        save_dict['Pulse Duration'] = sweep

        #check AWG mode or SRS mode
        mode = 'SRS'
        if(self.settings.AWG_mode.value):
            mode = 'AWG'



        #create arrays to hold the average values across averaging runs
        length = self.settings.N_pts.value
        pixels = self.settings.x_steps.value*self.settings.y_steps.value
        total_pts = length * pixels
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
                my_SRS = SRSctl.initSRS(27, 'SG384')
                SRSctl.setSRS_RFAmplitude(my_SRS, self.settings.Vpp.value, units = "Vpp")
                # #set test frequency and modulation; ESR has no modulation but that's handled in the modulation function
                SRSctl.setSRS_Freq(my_SRS, self.settings.Start_Frequency.value, 'GHz') 
                SRSctl.setupSRSmodulation(my_SRS, 'ESRseq') 
                SRSctl.enableSRS_RFOutput(my_SRS)
                print('SRS Initialized')
                # pass
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

            y_steps = self.settings.y_steps.value
            x_steps = self.settings.x_steps.value
            pixel = np.empty((pixels, 2))
            back = False
            curr_x = 0
            curr_y = 0
            for i in range(y_steps):
                for j in range(x_steps):
                    pixel[i*x_steps+j] = (curr_x, curr_y)
                    if j == x_steps-1:
                        continue
                    if back==False:
                        curr_x += self.settings.x_step_size.value
                    else:
                        curr_x -= self.settings.x_step_size.value
                curr_y += self.settings.y_step_size.value
                back = back==False

            print(pixel)

            self.cutoff = 0
            for i in range(NThrow):
                DAQ.readDAQ(task, self.settings.N_samples.value, self.settings.DAQtimeout.value)
            for j in range(pixels):
                self.ys = np.zeros(sweep.shape, dtype=float)
                #movestages(pixel[j])
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
                        AWGctl.makeT1SeqMarker(inst, f, self.settings.t_AOM.value, self.settings.t_readoutDelay.value, self.settings.t_pi.value, self.settings.MW_Frequency.value, self.settings.Vpp.value)
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
                        # self.ys[step] = np.divide(sig_average, back_average)
                        self.ys[step] = np.divide(sig_average-back_average, sig_average+back_average)
                
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
            self.plot.setTitle("Contrast vs Pulse Duration")
        else:
            self.plot.setTitle("Signal vs Pulse Duration")
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