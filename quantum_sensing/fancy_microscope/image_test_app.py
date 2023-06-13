from ScopeFoundry.base_app import BaseMicroscopeApp
from ScopeFoundry import Measurement, h5_io
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
import pyqtgraph as pg

import sys, time, os, inspect, copy
from datetime import datetime
import numpy as np
import pandas as pd
# import AWGcontrol as AWGctl

import movestages as PIctrl
import numpy as np
sys.path.append('../')
#import movestages as PIctrl

class ImageTestApp(BaseMicroscopeApp):

    name = 'image_test_app'
   
    def setup(self):
        self.add_measurement(ImageMeasure(self))

class ImageMeasure(Measurement):
    
    name = 'Image'
    
    def setup(self):
        
        S = self.settings

        S.New('N_pts', dtype=int, initial=100)
        S.New('Navg', dtype=int, initial=10)

        S.New('x_min', dtype=float, initial=0, vmin=0.0, vmax=18.0)
        S.New('y_min', dtype=float, initial=0, vmin=0.0, vmax=18.0)
        S.New('x_max', dtype=float, initial=18.0, vmin=0.0, vmax=18.0)
        S.New('y_max', dtype=float, initial=18.0, vmin=0.0, vmax=18.0)
        S.New('dx', dtype=float, initial=0.1, vmin=1e-2, vmax=18.0)
        S.New('dy', dtype=float, initial=0.1, vmin=1e-2, vmax=18.0)
        S.New('res', dtype=str, initial='', ro=True)
        S.New('num_pts', dtype=int, initial=1, ro=True)
        
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
        S.res.connect_to_widget(self.ui.res)
        S.num_pts.connect_to_widget(self.ui.num_pts)
        self.pos_buffer = {'x': None, 'y': None, 'r': None}
        self.stage = self._initialize_stages()
        self.plotdata = []

    def setup_figure(self):
        self.graph_layout = pg.GraphicsLayoutWidget()
        self.ui.plot_groupBox.layout().addWidget(self.graph_layout)
        self.plot = self.graph_layout.addPlot(title="X Position vs Y Position")

        self.scatter = pg.ScatterPlotItem(size=10, brush=pg.mkBrush(255, 255, 0, 255))
        self.plot.addItem(self.scatter)

    def run(self):
        S = self.settings
        
        self.plotdata = []
        xmin, ymin, xmax, ymax, dx, dy = S.x_min.val, S.y_min.val, S.x_max.val, S.y_max.val, S.dx.val, S.dy.val
        xy = np.mgrid[xmin:xmax+dx:dx, ymin:ymax+dy:dy].reshape(2,-1).T
        print(xy)
        N = S.Navg.val

        self.xs, self.ys = np.arange(xmin, xmax+dx, dx), np.arange(ymin, ymax+dy, dy)

        print("Starting Measurement")

        try:
            starttime = time.time()
            # ---- SETUP EXPERIMENT ----
            print('Setting up ...')
            self.stage = self._initialize_stages()
            endtime = time.time()
            print(f'Setup Complete! [Elapsed time: {endtime-starttime} s]')    

            starttime = time.time()
            # ---- DO EXPERIMENT ----
            interrupted, delay = False, 0
            print('Running Measurement ...')

            for i, x in enumerate(self.xs):
                if interrupted: break
                for j, y in enumerate(self.ys):
                    if interrupted: break
                    self._execute_move(x, y)
                    print(f'Current Pixel: {(x, y)}')
            
            '''for idx, pix in enumerate(xy):
                
                x, y = pix
                self._execute_move(x, y)
                # ---- DO MEASUREMENT ----
                self.plotdata.append(pix.tolist())
                self.set_progress((idx + 1) / xy.size * 100)
                time.sleep(1)
                for n in range(N):
                    # ---- DO MEASUREMENT ----
                    if self.interrupt_measurement_called:
                        print('Measurement Interrupted', end=' ')
                        interrupted = True
                        break
                    prog = (N * idx + n + 1) / (xy.size / 2 * N)  * 100
                    self.set_progress(prog)
                    time.sleep(delay)

                if interrupted:
                    break
                self.plotdata.append(pix.tolist())

            endtime = time.time()
            if not interrupted:
                print("Measurement Complete!", end=' ')
            print(f'[Elapsed time: {endtime-starttime} s]')'''

        except Exception as e:
            print(f'EXCEPTED ERROR: {e}')

        finally:
            # ---- CLOSE EQUIPMENT ----
            print('Finalizing Measurement ...')
            starttime = time.time()
            self._execute_move(9, 9)
            PIctrl.closeDevice(self.stage)
            endtime = time.time()
            print(f'Finalization Complete! [Elapsed time: {endtime-starttime} s]')

    def update_display(self):
        self.scatter.clear()
        self.scatter.addPoints(pos=self.plotdata)

    def _initialize_stages(self):
        return
        #return PIctrl.initializeController('LINEAR')

    def _execute_move(self, x, y):
        x_diff, y_diff = self.pos_buffer['x'] is None or x != self.pos_buffer['x'], \
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

    def _interrupt(self):
        self.interrupt_measurement_called = True

'''class ESRImageMeasure(Measurement):
    
    name = 'ESRImageTest'
    
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
        S.New('Start_Frequency', dtype=float, initial=3.6, spinbox_decimals=4, unit='GHz', spinbox_step=0.001)
        S.New('End_Frequency', dtype=float, initial=3.66, spinbox_decimals=4, unit='GHz', spinbox_step=0.001)      
        S.New('Vpp', dtype=float, initial=0.08, spinbox_decimals=3, spinbox_step=0.01, unit='V', si=True)
        S.New('N_samples', dtype=int, initial=1000)
        S.New('DAQtimeout', dtype=int, initial=1000, unit='s')
        S.New('t_duration', dtype=float, initial=0.0005, unit='s', si=True)
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
        self.stage = self._initialize_stages()

        self.freqs, self.cutoff = []

    def setup_figure(self):

        self.graph_layout = pg.GraphicsLayoutWidget()
        self.ui.plot_groupBox.layout().addWidget(self.graph_layout)
        self.plot = self.graph_layout.addPlot(title="Signal vs Frequency")

        self.current_plotline = self.plot.plot()
        self.average_plotline = self.plot.plot()
        
    def run(self):
        S = self.settings
        starttime = time.time()
        xmin, ymin, xmax, ymax, dx, dy = S.x_min.val, S.y_min.val, S.x_max.val, S.y_max.val, S.dx.val, S.dy.val

        xy = np.mgrid[xmin:xmax+dx:dx, ymin:ymax:dy].reshape(2,-1).T

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

        freqs, df = np.linspace(S.Start_Frequency.val, S.End_Frequency.val, num = S.N_pts.val, retstep = True)
        # print(freqs)
        #create a dictionary that will save signal and background information and will be exported to pandas df and then to a csv
        save_dict = {}
        save_dict['Frequency'] = freqs

        #create arrays to hold the average values across averaging runs
        length = S.N_pts.val
        pixels = xy.size
        total_pts = length * pixels
        self.average_x = freqs
        self.average_y = np.zeros(freqs.shape, dtype=float)

        #create arrays to hold realtime values during an averaging run, xs and ys will be plotted while signal and background are saved
        signal = np.zeros(freqs.shape, dtype=float)
        background = np.zeros(freqs.shape, dtype=float)
        self.data = np.zeros(freqs.shape, dtype=float)

        try:
            # ---- SETUP EXPERIMENT ----
            
            # SETUP AWG AND DAQ
            self._initialize_AWG()
            task = DAQ.configureDAQ(S.N_samples.val * freqs.size)
            AWGctl.makeESRSweep(self.inst, S.t_duration.val, freqs, S.Vpp.val)

            for idx, pix in enumerate(xy):
                if self.interrupt_measurement_called:
                    print('Interrupted')
                    break
                x, y = pix
                self._execute_move(x, y)

                for n in range(S.Navg.val):

                    counts = DAQ.readDAQ(self.task, S.N_samples.val * 2 * freqs.size, S.DAQtimeout.val)

                    for i in range(freqs.size):
                        signal[i] = np.mean(counts[2*i::2*freqs.size])
                        background[i] = np.mean(counts[2*i+1::2*freqs.size])

                        #Depending on the plotting type, either append the signal or the contrast
                        if S.plotting_type.val == 'signal':
                            self.data[i] = signal[i]
                        else:
                            self.data[i] = np.divide(signal[i], background[i])

                        if(idx == 0):
                            self.cutoff += 1
                        
                    self.set_progress((idx * S.Navg.val + n) / (pixels * S.Navg.val) * 100)
                    M['run_'+str(pix)+'_data'] = self.data
                    #Save the signal and background arrays to the dictionary
                    save_dict['Signal Run ' + str(pix)] = copy.deepcopy(signal)
                    save_dict['Background Run ' + str(pix)] = copy.deepcopy(background)

        except Exception as e:
            print('EXCEPTED ERROR:' + str(e))
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
            M['sweep'] = freqs
            M['pixels'] = xy
            h5_file.close()
            return
        
        # print("Measurement Complete!")

    def update_display(self):
        S = self.settings
        if(S.plotting_type.value == 'signal'):
            self.plot.setTitle("Signal vs Frequency")
        else:
            self.plot.setTitle("Constrast vs Frequency")
        self.current_plotline.setData(self.freqs[:self.cutoff], self.average_y[:self.cutoff])

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
        AWGctl.Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)'''
        
if __name__ == '__main__':
    
    app = ImageTestApp(sys.argv)
    sys.exit(app.exec_())