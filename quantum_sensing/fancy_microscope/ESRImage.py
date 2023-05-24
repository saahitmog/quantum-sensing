
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
from movemcm import Controller

class ESRImageMeasure(Measurement):

    name = "ESRImage"
    cutoff = 0

    def setup(self):

        # self.states = ['power', 'target_power']
        # for rate in self.states:
        #     self.settings.New('{}_visible'.format(rate), dtype=bool, initial=True)   
        self.settings.New('photon_mode', dtype=bool, initial=False)
        self.settings.New('AWG_mode', dtype=bool, initial=True)
        self.settings.New('Start_Frequency', dtype=float, initial=3.04, spinbox_decimals=4, unit='GHz', spinbox_step=0.001)
        self.settings.New('End_Frequency', dtype=float, initial=3.15, spinbox_decimals=4, unit='GHz', spinbox_step=0.001)
        self.settings.New('Vpp', dtype=float, initial=0.08, spinbox_decimals=3, spinbox_step=0.01, unit='V', si=True)  
        self.settings.New('N_pts', dtype=int, initial=101)
        self.settings.New('N_samples', dtype=int, initial=1000)
        self.settings.New('DAQtimeout', dtype=int, initial=1000, unit='s')
        self.settings.New('t_duration', dtype=float, initial=0.0005, unit='s', si=True)
        self.settings.New('magnet_current', dtype=float, initial=0.6)
        # self.settings.New('Navg', dtype=int, initial=10)
        self.settings.New('x_start', dtype=int, initial=0, unit='um')
        self.settings.New('y_start', dtype=int, initial=0, unit='um')
        self.settings.New('x_steps', dtype=int, initial=10)
        self.settings.New('y_steps', dtype=int, initial=10)
        self.settings.New('x_step_size', dtype=int, initial=1, unit='um')
        self.settings.New('y_step_size', dtype=int, initial=1, unit='um')
        # self.settings.New('figsize_x', dtype=int, initial=9)
        # self.settings.New('figsize_y', dtype=int, initial=5)
        self.settings.New('plotting_type', dtype=str, initial='contrast')
        self.settings.New('integration_min', dtype=float, initial=3.07, unit='GHz', spinbox_decimals=3, spinbox_step=0.01)
        self.settings.New('integration_max', dtype=float, initial=3.085, unit='GHz', spinbox_decimals=3, spinbox_step=0.01)
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
        self.plot = self.graph_layout.addPlot(title="Signal vs Frequency")

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
        starttime=time.time()
        self.set_progress(0)

        if(self.settings.photon_mode.value):
            import DAQcontrol_SPD as DAQ  ## single_photon_stream => replaced with DAQcontrol_SPD by zhao 7/19/2022
        else:
            import DAQ_Analog as DAQ
        
        # starttime=time.time()
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

        # start = time.process_time()
        start = starttime

        if(self.settings.plotting_type.value != 'signal'):
            print("contrast mode")
        else:
            print("signal mode")

        # style.use("fivethirtyeight")
        #create figure and subplot, figsize can be changed in the global configuration document
        # fig = plt.figure(figsize = (self.settings.figsize_x.value, self.settings.figsize_y.value))
        # ax = fig.add_subplot(111)

        #sweep is a np array of frequency values that we will sweep across, step_size is the size of steps between
        sweep, step_size = np.linspace(self.settings.Start_Frequency.value, self.settings.End_Frequency.value, num = self.settings.N_pts.value, retstep = True)
        #sweep = np.arange(config['START_FREQUENCY'], config['END_FREQUENCY'] + config['STEP_FREQUENCY'], config['STEP_FREQUENCY'])
        print(sweep)
        #create a dictionary that will save signal and background information and will be exported to pandas df and then to a csv
        save_dict = {}
        save_dict['Frequency'] = sweep

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
                # my_SRS = SRSctl.initSRS(27, 'SG384')
                # SRSctl.setSRS_RFAmplitude(my_SRS, self.settings.Vpp.value, units = "Vpp")
                # # #set test frequency and modulation; ESR has no modulation but that's handled in the modulation function
                # SRSctl.setSRS_Freq(my_SRS, self.settings.Start_Frequency.value, 'GHz') 
                # SRSctl.setupSRSmodulation(my_SRS, 'ESRseq') 
                # SRSctl.enableSRS_RFOutput(my_SRS)
                # print('SRS Initialized')
                print("SRS not supported")
                return
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
            task = DAQ.configureDAQ(self.settings.N_samples.value * len(sweep))
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
                    # SRSctl.disableSRS_RFOutput(my_SRS)
                    print("SRS not supported")
                    return
                DAQ.closeDAQTask(task)

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

            controller = Controller(which_port='COM5',
                        stages=('ZFM2030', 'ZFM2030', 'ZFM2030'),
                        reverse=(False, False, False),
                        verbose=True,
                        very_verbose=False)
            
            #channel 0 is Y, channel 1 is Z, channel 2 is X
            print('\n# Home:')
            controller.move_um(0, 0, relative=False, block=True)
            # controller.move_um(1, 0, relative=False, block=True)
            controller.move_um(2, 0, relative=False, block=True)

            startpos = (self.settings.x_start.value, self.settings.y_start.value)

            def movestages(coord, offset):
                controller.move_um(2, offset[0] + coord[0], relative=False, block=True)
                controller.move_um(0, offset[1] + coord[1], relative=False, block=True)

            currtime=time.time()
            print('One-time setup: ', currtime-starttime, ' seconds')

            AWGctl.makeESRSweep(inst, self.settings.t_duration.value, sweep, self.settings.Vpp.value)

            lasttime=currtime
            currtime=time.time()
            print('--------> Generate sequence total:', currtime-lasttime, ' seconds')

            n = len(sweep)
            for j in range(pixels):
                self.ys = np.zeros(sweep.shape, dtype=float)
                movestages(pixel[j], startpos)
                # time.sleep(0.3)
                # if self.interrupt_measurement_called:
                #     print('end partial run')
                #     M['run'+str(j)+'_data']=self.ys
                #     #Save the signal and background arrays to the dictionary
                #     save_dict['Signal Run ' + str(int(j))] = copy.deepcopy(signal)
                #     save_dict['Background Run ' + str(int(j))] = copy.deepcopy(background)
                #     return

                #Read from the DAQ
                counts = DAQ.readDAQ(task, self.settings.N_samples.value * 2 * n, self.settings.DAQtimeout.value)
                lasttime=currtime
                currtime=time.time()
                print('--------> Read DAQ:', currtime-lasttime, ' seconds')
                #the signal is the even points and background is the odd points from the data array
                #counts = data[:self.settings.N_samples.value * 2]
                #counts = data
                for i in range(n):
                    signal[i] = np.mean(counts[2*i::2*n]) #Averages signal count for frequency i by splicing every (2*N_pts)th sample, for example for N_pts = 101 every 202nd sample starting with sample 2*i
                    background[i] = np.mean(counts[2*i+1::2*n])

                    # current_signal = counts[0::2]
                    # current_background = counts[1::2]
            
                    # #average both arrays
                    # sig_average = np.mean(current_signal)
                    # back_average = np.mean(current_background)

                    # #append signal to signal array and background to background array
                    # signal[step] = sig_average
                    # background[step] = back_average

                    #Depending on the plotting type, either append the signal or the contrast
                    if self.settings.plotting_type.value == 'signal':
                        self.ys[i] = signal[i]
                    else:
                        #self.ys[step] = sig_average / back_average
                        self.ys[i] = np.divide(signal[i], background[i])
                
                    #Average the y correctly 
                    # self.average_y[i] = ((self.average_y[i] * j) + self.ys[i]) / (j+1)

                    if(j == 0):
                        self.cutoff += 1
                    # self.cutoff += 1

                    fraction_complete = (j*length + i) / total_pts
                    self.set_progress(fraction_complete * 100)
                
                lasttime=currtime
                currtime=time.time()
                print('--------> Averaging and plotting:', currtime-lasttime, ' seconds')
                print('End sweep on pixel {0}'.format(pixel[j]))
                M['run_'+str(pixel[j])+'_data']=self.ys
                #Save the signal and background arrays to the dictionary
                save_dict['Signal Run ' + str(pixel[j])] = copy.deepcopy(signal)
                save_dict['Background Run ' + str(pixel[j])] = copy.deepcopy(background)
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
            print('Ending experiment...')
            # end = time.process_time()
            end = time.time()
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
            # M['average_data'] = self.average_y
            M['sweep'] = sweep
            M['pixels'] = pixel
            h5_file.close()
            # clean up here
            return
            
    
    def update_display(self):
        #self.current_plotline.setData(self.xs[:index+1], self.ys[:index+1])
        if(self.settings.plotting_type.value != 'signal'):
            self.plot.setTitle("Contrast vs Frequency")
        else:
            self.plot.setTitle("Signal vs Frequency")
        self.current_plotline.setData(self.average_x[:self.cutoff], self.ys[:self.cutoff])


from ctypes import *
import numpy as np
import sys
import time
import copy
import pandas as pd

import os
import inspect
from System import Array, Char, Int16
import time

datapath = os.path.dirname(sys.argv[0])
maxScpiResponse = 65535

if (datapath):
    datapath = datapath + "\\"
print(datapath)


#Define number of measurements to throw away before starting experiment 
NThrow = 0