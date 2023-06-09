from ScopeFoundry.base_app import BaseMicroscopeApp
from ScopeFoundry import Measurement, h5_io
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
import pyqtgraph as pg

import sys, os, inspect
from datetime import datetime
import numpy as np
import pandas as pd

#import AWGcontrol as AWGctrl, DAQ_Analog as DAQ

class TestApp(BaseMicroscopeApp):

    name = 'ui_test_app'
   
    def setup(self):
        self.add_measurement(TestMeasure(self))

class TestMeasure(Measurement):
    
    name = 'ESR'
    
    def setup(self):
        
        S = self.settings

        S.New('Npts', dtype=int, initial=100, vmin=0)
        S.New('Navg', dtype=int, initial=10, vmin=1)
        #S.New('photon_mode', dtype=bool, initial=False)
        #S.New('AWG_mode', dtype=bool, initial=True)
        S.New('Start_Frequency', dtype=float, initial=2.5, spinbox_decimals=4, unit='GHz', spinbox_step=0.001)
        S.New('End_Frequency', dtype=float, initial=3.0, spinbox_decimals=4, unit='GHz', spinbox_step=0.001)      
        S.New('Vpp', dtype=float, initial=0.08, spinbox_decimals=3, spinbox_step=0.01, unit='V', si=True, vmin=0)
        S.New('N_samples', dtype=int, initial=1000, vmin=1)
        S.New('DAQtimeout', dtype=int, initial=1000, unit='s', vmin=0)
        S.New('t_duration', dtype=float, initial=0.0005, unit='s', si=True, vmin=0)
        S.New('magnet_current', dtype=float, initial=1.8, unit='A', si=True, vmin=0)
        S.New('plotting_type', dtype=str, initial='signal', choices=('signal', 'contrast'))
        S.New('fname_format', dtype=str, initial='{timestamp:%y%m%d_%H%M%S}_{measurement.name}_{sample}.{ext}')
        S.New('sweep', dtype=bool, initial=False)

        self.ui_filename = sibling_path(__file__,"test_app.ui")
        self.ui = load_qt_ui_file(self.ui_filename)
        self.ui.setWindowTitle(self.name)

        self.ui.interrupt_pushButton.clicked.connect(self._interrupt_)
        self.ui.start_pushButton.clicked.connect(self._start_)

        S.Npts.connect_to_widget(self.ui.Npts_doubleSpinBox)
        S.Navg.connect_to_widget(self.ui.Navg_doubleSpinBox)
        S.Start_Frequency.connect_to_widget(self.ui.freqmin_doubleSpinBox)
        S.End_Frequency.connect_to_widget(self.ui.freqmax_doubleSpinBox)
        S.Vpp.connect_to_widget(self.ui.Vpp_doubleSpinBox)
        S.magnet_current.connect_to_widget(self.ui.magcurr_doubleSpinBox)
        S.sweep.connect_to_widget(self.ui.sweep_CheckBox)
        S.plotting_type.connect_to_widget(self.ui.plot_ComboBox)

    def setup_figure(self):

        self.plotdata, self.sweep = np.array([]), np.array([])

        self.graph_layout = pg.GraphicsLayoutWidget()
        self.ui.plot_groupBox.layout().addWidget(self.graph_layout)
        self.plot = self.graph_layout.addPlot(title="")

        self.plotline = self.plot.plot()

    def run(self):
        self.set_progress(0)
        S = self.settings
        # self._make_savefiles_()

        # print(f"{S.plotting_type.val} mode")

        self.sweep = np.linspace(S.Start_Frequency.val, S.End_Frequency.val, num=S.Npts.val)

        try:
            # self.__initialize()
            # if S.sweep.val: self._run_sweep_()
            # else: self._run_()
            print(self.sweep)
            pass

        except Exception as e:
            print(e)

        finally:
            # self.__finalize()
            # self._save_data_()
            pass
        return
        
    def update_display(self):
        if(self.settings.plotting_type.val == 'signal'):
            self.plot.setTitle("Signal vs Frequency")
        else:
            self.plot.setTitle("Contrast vs Frequency")
        self.plotline.setData(self.sweep, self.plotdata)

    def _run_(self):
        S = self.settings
        self.task = task = DAQ.configureDAQ(S.N_samples.val * self.sweep.size)
        signal = np.zeros(self.sweep.shape, dtype=float)
        background = np.zeros(self.sweep.shape, dtype=float)

        for n in range(S.Navg.val):
            #time.sleep(0.1)

            counts = DAQ.readDAQ(task, S.N_samples.val*2*self.sweep.size, S.DAQtimeout.val)
            
            for i in range(self.sweep.size):
                signal[i] = np.mean(counts[2*i::2*n])
                background[i] = np.mean(counts[2*i+1::2*n])

            if S.plotting_type.val == 'contrast': signal = np.divide(signal, background)
            self.plotdata = ((self.plotdata*n) + signal) / (n+1)
            self.set_progress(n/S.Navg.val * 100)

    def _run_sweep_(self):
        #Configure the DAQ
        S = self.settings
        self.task = task = DAQ.configureDAQ(S.N_samples.val * self.sweep.size)
        AWGctrl.makeESRSweep(self.inst, S.t_duration.val, self.sweep, S.Vpp.val)

        for n in range(S.Navg.val):
            #time.sleep(0.1)

            for i, f in enumerate(self.sweep):
                AWGctrl.makeSingleESRSeqMarker(self.inst, S.t_duration.val, f, S.Vpp.val)
                counts = DAQ.readDAQ(task, S.N_samples.val*2, S.DAQtimeout.val)
                signal = np.mean(counts[0::2])
                background = np.mean(counts[1::2])
                if S.plotting_type.val == 'contrast': signal = np.divide(signal, background)
                self.plotdata[i] = (self.plotdata[i]*n + signal) / (n+1)
                self.set_progress((n*self.sweep.size+i+1)/(S.Navg.val*self.sweep.size) * 100)

    def _interrupt_(self):
        self.interrupt_measurement_called = True

    def _start_(self):
        self.activation.update_value(not self.activation.val)

    def _initialize_(self):
        self.admin = admin = AWGctrl.loadDLL()
        slotId = AWGctrl.getSlotId(admin)
        if not slotId:
            print("Invalid choice!")
        else:
            self.inst = inst = admin.OpenInstrument(slotId)
            if not inst:
                print("Failed to Open instrument with slot-Id {0}".format(slotId))  # @IgnorePep8
                print("\n")
            else:
                self.instId = inst.InstrId
        AWGctrl.instrumentSetup(inst)

    def _finalize_(self):
        AWGctrl.SendScpi(self.inst, ":OUTP OFF")
        rc = self.admin.CloseInstrument(self.instId)
        AWGctrl.Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)
        rc = self.admin.Close()
        AWGctrl.Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)
        DAQ.closeDAQTask(self.task)

    def _make_savefiles_(self):
        S = self.settings
        t = datetime.now()
        if  not os.path.isdir(self.app.settings['save_dir']):
            os.mkdir(self.app.settings['save_dir'])

        fn = S['fname_format'].format(
             app=self,
             measurement=self,
             timestamp=t,
             sample=self.app.settings['sample'],
             ext='h5')
        fn = os.path.join(self.app.settings['save_dir'], fn)
        self.h5f = h5_file = h5_io.h5_base_file(self.app, fname=fn, measurement=self)
        self.M = h5_io.h5_create_measurement_group(self, h5_file)

        fn = S['fname_format'].format(
             app=self,
             measurement=self,
             timestamp=t,
             sample=self.app.settings['sample'],
             ext='csv')
        self.csvfn = os.path.join(self.app.settings['save_dir'], fn)
        self.save_dict = {}

    def _save_data_(self):
        S = self.settings

        self.save_dict['sweep'] = self.sweep
        self.save_dict[f'average {S.plotting_type.val}'] = self.plotdata
        dataset = pd.DataFrame(self.save_dict)
        dataset.to_csv(self.csvfn)

        self.M['sweep'] = self.sweep
        self.M[f'average {S.plotting_type.val}'] = self.plotdata
        self.h5f.close()
        
if __name__ == '__main__':
    app = TestApp(sys.argv)
    sys.exit(app.exec_())