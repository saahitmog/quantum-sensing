from ScopeFoundry.base_app import BaseMicroscopeApp
from ScopeFoundry import Measurement, h5_io
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
import pyqtgraph as pg

import time, os, inspect, copy
from datetime import datetime
import numpy as np
import pandas as pd
import AWGcontrol as AWGctl

import movestages as PIctrl
import numpy as np
from traceback import print_exc as eprint

class T1ImageMeasure(Measurement):
    
    name = 'T1Image'
    
    def setup(self):
        
        S = self.settings

        S.New('N_pts', dtype=int, initial=100)
        S.New('Navg', dtype=int, initial=5)

        S.New('x_min', dtype=float, initial=0, vmin=0.0, vmax=18.0)
        S.New('y_min', dtype=float, initial=0, vmin=0.0, vmax=18.0)
        S.New('x_max', dtype=float, initial=18.0, vmin=0.0, vmax=18.0)
        S.New('y_max', dtype=float, initial=18.0, vmin=0.0, vmax=18.0)
        S.New('dx', dtype=float, initial=0.1, vmin=1e-2, vmax=18.0)
        S.New('dy', dtype=float, initial=0.1, vmin=1e-2, vmax=18.0)

        S.New('photon_mode', dtype=bool, initial=False)
        S.New('AWG_mode', dtype=bool, initial=True)
        S.New('Start_Tau', dtype=float, initial=536e-9, spinbox_decimals=3, unit='s', si=True)
        S.New('End_Tau', dtype=float, initial=2e-4, spinbox_decimals=3, unit='s', si=True)      
        S.New('Vpp', dtype=float, initial=0.08, spinbox_decimals=3, spinbox_step=0.01, unit='V', si=True)
        S.New('MW_Frequency', dtype=float, initial=3.643, spinbox_decimals=4, unit='GHz', spinbox_step=0.001)
        S.New('t_AOM', dtype=float, initial=0.0005, unit='s', si=True)
        S.New('t_readoutDelay', dtype=float, initial=0.0004, unit='s', si=True)
        S.New('t_pi', dtype=float, initial=50e-9, unit='s', si=True)
        S.New('N_samples', dtype=int, initial=1000)
        S.New('DAQtimeout', dtype=int, initial=1000, unit='s')
        S.New('magnet_current', dtype=float, initial=1.8)

        S.New('plotting_type', dtype=str, initial='contrast')
        S.New('fname_format', dtype=str, initial='{timestamp:%y%m%d_%H%M%S}_{measurement.name}_{sample}.{ext}')
        
        self.ui_filename = sibling_path(__file__,"image_test.ui")
        self.ui = load_qt_ui_file(self.ui_filename)
        self.ui.setWindowTitle(self.name)
        
        S.activation.connect_to_widget(self.ui.start_box)
        self.ui.interrupt_pushButton.clicked.connect(self._interrupt)

        S.N_pts.connect_to_widget(self.ui.N_pts_doubleSpinBox)
        S.Navg.connect_to_widget(self.ui.Navg_doubleSpinBox)
    
        S.x_min.connect_to_widget(self.ui.xmin_doubleSpinBox)
        S.y_min.connect_to_widget(self.ui.ymin_doubleSpinBox)
        S.x_max.connect_to_widget(self.ui.xmax_doubleSpinBox)
        S.y_max.connect_to_widget(self.ui.ymax_doubleSpinBox)
        S.dx.connect_to_widget(self.ui.dx_doubleSpinBox)
        S.dy.connect_to_widget(self.ui.dy_doubleSpinBox)
        self.pos_buffer = {'x': None, 'y': None, 'r': None}

        self.sweep, self.cutoff = [], 0
        self.res, self.num_pts, self.dims = '', 1, (1,1)

    def setup_figure(self):

        self.graph_layout = pg.GraphicsLayoutWidget()
        self.ui.plot_groupBox.layout().addWidget(self.graph_layout)
        self.plot = self.graph_layout.addPlot(title="Signal vs Tau")
        self.plotdata = []

        self.current_plotline = self.plot.plot()
        self.average_plotline = self.plot.plot()
        
    def run(self):
        S = self.settings
        starttime = time.time()
        xmin, ymin, xmax, ymax, dx, dy = S.x_min.val, S.y_min.val, S.x_max.val, S.y_max.val, S.dx.val, S.dy.val

        self.dims = (np.arange(xmin, xmax+dx, dx).size, np.arange(ymin, ymax+dy, dy).size)
        self.xy = xy = np.mgrid[xmin:xmax+dx:dx, ymin:ymax+dy:dy].reshape(2,-1).T
        self.num_pts = xy.size / 2

        if(S.photon_mode.val):
            import DAQcontrol_SPD as DAQ  ## single_photon_stream => replaced with DAQcontrol_SPD by zhao 7/19/2022
        else:
            import DAQ_Analog as DAQ

        f = S['fname_format'].format(
             app=self,
             measurement=self,
             timestamp=datetime.fromtimestamp(starttime),
             sample=self.app.settings['sample'],
             ext='h5')
        
        fn = os.path.join(self.app.settings['save_dir'], f)
        if not os.path.isdir(self.app.settings['save_dir']):
            os.mkdir(self.app.settings['save_dir'])
        h5_file = h5_io.h5_base_file(self.app, fname=fn, measurement=self)
        M = h5_io.h5_create_measurement_group(self, h5_file)

        if S.plotting_type.val == 'signal':
            print("signal mode")
        else:
            print("contrast mode")

        sweep, step = np.linspace(S.Start_Tau.value, S.End_Tau.value, num = S.N_pts.value, retstep = True)
        # print(sweep)
        #create a dictionary that will save signal and background information and will be exported to pandas df and then to a csv
        save_dict = {}
        save_dict['Tau'] = self.sweep = sweep

        #create arrays to hold the average values across averaging runs
        length = S.N_pts.val
        pixels = xy.size / 2
        total_pts = length * pixels
        self.average_x = sweep
        self.plotdata = np.zeros(sweep.shape, dtype=float)

        #create arrays to hold realtime values during an averaging run, xs and ys will be plotted while signal and background are saved
        signal = np.zeros(sweep.shape, dtype=float)
        background = np.zeros(sweep.shape, dtype=float)
        self.data = np.zeros(sweep.shape, dtype=float)

        try:
            # ---- SETUP EXPERIMENT ----
            
            # SETUP AWG AND DAQ
            self._initialize_AWG()
            self.stage = self._initialize_stages()
            task = DAQ.configureDAQ(S.N_samples.val * sweep.size)

            interrupted = False

            for idx, pix in enumerate(xy):
                if interrupted: break
                x, y = pix
                self._execute_move(x, y)
                print(f'Current Pixel: {pix}')
                
                '''for n in range(S.Navg.val):

                    if self.interrupt_measurement_called:
                        print('Interrupted')
                        break

                    print(f'Averaging Run {n+1}: Reading From DAQ ...')
                    counts = DAQ.readDAQ(task, S.N_samples.val * 2 * sweep.size, S.DAQtimeout.val)
                    print(f'DAQ Read complete.')

                    for i in range(sweep.size):
                        signal[i] = np.mean(counts[2*i::2*sweep.size])
                        background[i] = np.mean(counts[2*i+1::2*sweep.size])

                        #Depending on the plotting type, either append the signal or the contrast
                        if S.plotting_type.val == 'signal':
                            self.data[i] = signal[i]
                        else:
                            self.data[i] = np.divide(signal[i], background[i])

                        self.plotdata[i] = ((self.plotdata[i] * n) + self.data[i]) / (n+1)

                        
                    self.set_progress((idx * S.Navg.val + n + 1) / (pixels * S.Navg.val) * 100)'''

                for n in range(S.Navg.value):
                    if interrupted: break
                    self.data = np.zeros(sweep.shape, dtype=float)
                    for i, d in enumerate(sweep):
                        # time.sleep(0.3)
                        if self.interrupt_measurement_called:
                            print('end partial run')
                            interrupted = True
                            M['run'+str(n)+'_data']=self.data
                            #Save the signal and background arrays to the dictionary
                            save_dict['Signal Run ' + str(int(n))] = copy.deepcopy(signal)
                            save_dict['Background Run ' + str(int(n))] = copy.deepcopy(background)
                            break

                        AWGctl.makeT1SeqMarker(self.inst, d, S.t_AOM.value, S.t_readoutDelay.value, S.t_pi.value, S.MW_Frequency.value, S.Vpp.value)

                        #Read from the DAQ
                        counts = DAQ.readDAQ(task, S.N_samples.value * 2, S.DAQtimeout.value)
                        current_signal = counts[0::2]
                        current_background = counts[1::2]

                        #average both arrays
                        sig_average = np.mean(current_signal)
                        back_average = np.mean(current_background)

                        #append signal to signal array and background to background array
                        signal[i] = sig_average
                        background[i] = back_average

                        #Depending on the plotting type, either append the signal or the contrast
                        if S.plotting_type.value == 'signal':
                            self.data[i] = sig_average
                        else:
                            self.data[i] = np.divide(sig_average-back_average, sig_average+back_average)
                    
                        #Average the y correctly 
                        self.plotdata[i] = ((self.plotdata[i] * n) + self.data[i]) / (n+1)

                        #fraction_complete = (n*length + i + 2) / total_pts
                        #self.set_progress(fraction_complete * 100)

                    #M['run_'+str(pix)+'_'+str(n)+'_data'] = self.data
                    # Save the signal and background arrays to the dictionary
                    #save_dict['Signal Run '+str(pix)+'_'+str(n)] = copy.deepcopy(signal)
                    #save_dict['Background Run '+str(pix)+'_'+str(n)] = copy.deepcopy(background)

        except Exception:
            print('EXCEPTED ERROR:', end=' ')
            eprint()
        finally:
            self._execute_move(9, 9)
            PIctrl.closeDevice(self.stage)
            DAQ.closeDAQTask(task)
            self._close_AWG()

            f = S['fname_format'].format(app=self,
                                         measurement=self,
                                         timestamp=datetime.fromtimestamp(starttime),
                                         sample=self.app.settings['sample'],
                                         ext='csv')
            fn = os.path.join(self.app.settings['save_dir'], f)  
            df = pd.DataFrame(save_dict)
            df.to_csv(fn)
            M['sweep'] = sweep
            M['pixels'] = xy
            h5_file.close()

            print('Measurement Complete')
            return
        
        # print("Measurement Complete!")

    def update_display(self):
        S = self.settings
        self.ui.num_pts.setText(str(int(self.xy.size/2)))
        self.ui.res.setText(f'{self.dims[0]} X {self.dims[1]}')
        if(S.plotting_type.value == 'signal'):
            self.plot.setTitle("Signal vs Tau")
        else:
            self.plot.setTitle("Constrast vs Tau")
        #self.current_plotline.setData(self.sweep[:self.cutoff], self.plotdata[:self.cutoff])
        self.current_plotline.setData(self.sweep, self.plotdata)

    def _initialize_stages(self):
        return PIctrl.initializeController('LINEAR')

    def _execute_move(self, x, y):

        x_diff, y_diff= self.pos_buffer['x'] is None or x != self.pos_buffer['x'], \
                                 self.pos_buffer['y'] is None or y != self.pos_buffer['y']

        if x_diff and y_diff:
            PIctrl.moveToPos(self.stage, x, y)
            self.pos_buffer['x'], self.pos_buffer['y'] = x, y

        elif x_diff:
            PIctrl.moveToX(self.stage, x)
            self.pos_buffer['x'] = x

        elif y_diff:
            PIctrl.moveToY(self.stage, y)
            self.pos_buffer['y'] = y

        #if x_diff or y_diff:
        #    print("Stages Updated")

    def _interrupt(self):
        self.interrupt_measurement_called = True

    def _initialize_AWG(self):
            self.admin = admin = AWGctl.loadDLL()
            slotId = AWGctl.getSlotId(admin)
            if not slotId:
                print("Invalid choice!")
            else:
                self.inst = inst = admin.OpenInstrument(slotId)
                if not inst:
                    print("Failed to Open instrument with slot-Id {0}".format(slotId))  # @IgnorePep8
                    print("\n")
                else:
                    self.instId = inst.InstrId
            AWGctl.instrumentSetup(inst)
            print('AWG Initialized')

    def _close_AWG(self):
        AWGctl.SendScpi(self.inst, ":OUTP OFF")
        rc = self.admin.CloseInstrument(self.instId)
        AWGctl.Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)
        rc = self.admin.Close()
        AWGctl.Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)