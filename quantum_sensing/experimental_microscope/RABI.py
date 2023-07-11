from ScopeFoundry import Measurement, h5_io
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
import pyqtgraph as pg

import os, inspect, traceback
from datetime import datetime
import numpy as np
import pandas as pd

import AWGcontrol as AWGctrl
import DAQ_Analog as DAQ
from utils import *

class RabiMeasure(Measurement):
    
    name = 'RABI'
    
    def setup(self):
        
        S = self.settings

        S.New('Npts', dtype=int, initial=100, vmin=0)
        S.New('Navg', dtype=int, initial=10, vmin=1)
        S.New('photon_mode', dtype=bool, initial=False)
        S.New('AWG_mode', dtype=bool, initial=True)
        S.New('Start_Duration', dtype=float, initial=1e-8, spinbox_decimals=9, unit='s', si=True)
        S.New('End_Duration', dtype=float, initial=6e-7, spinbox_decimals=9, unit='s', si=True)
        S.New('Vpp', dtype=float, initial=0.08, spinbox_decimals=3, spinbox_step=0.01, unit='V', si=True, vmin=0)
        S.New('MW_Frequency', dtype=float, initial=3.0000, spinbox_decimals=4, unit='GHz', spinbox_step=0.001)
        S.New('MW_delay', dtype=float, initial=0.0005, spinbox_decimals=5, unit='s', si=True)
        S.New('N_samples', dtype=int, initial=1000, vmin=1)
        S.New('DAQtimeout', dtype=int, initial=1000, unit='s', vmin=0)
        S.New('t_duration', dtype=float, initial=0.0005, unit='s', si=True, vmin=0)
        S.New('magnet_current', dtype=float, initial=1.8, unit='A', si=True, vmin=0)
        S.New('plotting_type', dtype=str, initial='signal', choices=('signal', 'contrast'))
        S.New('fname_format', dtype=str, initial='{timestamp:%y%m%d_%H%M%S}_{measurement.name}_{sample}.{ext}')
        S.New('sweep', dtype=bool, initial=False)
        S.New('save', dtype=bool, initial=False)

        self.ui_filename = sibling_path(__file__,"RABI.ui")
        self.ui = load_qt_ui_file(self.ui_filename)
        self.ui.setWindowTitle(self.name)

        self.ui.interrupt_pushButton.clicked.connect(self._interrupt_)
        self.ui.start_pushButton.clicked.connect(self._start_)

        S.Npts.connect_to_widget(self.ui.Npts_doubleSpinBox)
        S.Navg.connect_to_widget(self.ui.Navg_doubleSpinBox)
        S.Start_Duration.connect_to_widget(self.ui.durmin_doubleSpinBox)
        S.End_Duration.connect_to_widget(self.ui.durmax_doubleSpinBox)
        S.Vpp.connect_to_widget(self.ui.Vpp_doubleSpinBox)
        S.MW_Frequency.connect_to_widget(self.ui.mwfreq_doubleSpinBox)
        S.MW_delay.connect_to_widget(self.ui.mwdelay_doubleSpinBox)
        S.sweep.connect_to_widget(self.ui.sweep_CheckBox)
        S.save.connect_to_widget(self.ui.save_CheckBox)
        S.plotting_type.connect_to_widget(self.ui.plot_ComboBox)

    def setup_figure(self):
        self.plotdata, self.sweep = np.array([]), np.array([])
        self.graph_layout = pg.GraphicsLayoutWidget()
        self.ui.plot_groupBox.layout().addWidget(self.graph_layout)
        self.plot = self.graph_layout.addPlot(title="")
        self.plotline = self.plot.plot()

    def run(self):
        with timer('Measurement Complete: '):
            self.set_progress(0)
            S = self.settings
            if S.save.val: self._make_savefiles_()

            print(f"Starting Rabi Measurement in {S.plotting_type.val.capitalize()} Mode")

            self.sweep = np.linspace(S.Start_Duration.val, S.End_Duration.val, num=S.Npts.val)
            self.plotdata = np.zeros_like(self.sweep)

            try:
                with timer('--> Hardware Startup: '), hide(): self._initialize_()
                if S.sweep.val: 
                    print('Rabi Sweep Measurement not yet implemented. Aborting measurement.')
                    self._run_sweep_()
                else: self._run_()
            except Exception: traceback.print_exc()
            finally:
                with timer('--> Hardware Close: '): self._finalize_()
                if S.save.val: self._save_data_()
                # print('')
        
    def update_display(self):
        if self.settings.plotting_type.val == 'signal': self.plot.setTitle("Signal vs Duration")
        else: self.plot.setTitle("Contrast vs Duration")
        self.plotline.setData(self.sweep, self.plotdata)

    def post_run(self): 
        with hide(): self.app.settings_save_ini('.config.ini')

    def _run_sweep_(self) -> None:
        S = self.settings
        self.task = task = DAQ.configureDAQ(S.N_samples.val * S.Npts.val)
        signal = np.zeros(self.sweep.shape, dtype=float)
        background = np.zeros(self.sweep.shape, dtype=float)
        AWGctrl.makeRabiSweep(self.inst, self.sweep, S.MW_delay.val, S.MW_Frequency.val, S.Vpp.val)

        for n in range(S.Navg.val):
            if self.interrupt_measurement_called:
                    print('Measurement Interrupted')
                    break
            with timer('--> Read DAQ: '): counts = DAQ.readDAQ(task, S.N_samples.val*S.Npts.val*2, S.DAQtimeout.val)
            for i in range(self.sweep.size):
                signal[i], background[i] = np.mean(counts[2*i::2*self.sweep.size]), np.mean(counts[2*i+1::2*self.sweep.size])

            if S.plotting_type.val == 'contrast': signal = np.divide(signal, background)
            self.plotdata = ((self.plotdata*n) + signal) / (n+1)
            self.set_progress(n/S.Navg.val * 100)

    def _run_(self) -> None:
        #Configure the DAQ
        S = self.settings
        self.task = task = DAQ.configureDAQ(S.N_samples.val)
        interrupted = False
        for n in range(S.Navg.val):
            if interrupted: break
            for i, d in enumerate(self.sweep):
                if self.interrupt_measurement_called:
                    interrupted = True
                    print('Measurement Interrupted')
                    break
                AWGctrl.makeSingleRabiSeqMarker(self.inst, d, S.MW_delay.val, S.MW_Frequency.val, S.Vpp.val)
                counts = DAQ.readDAQ(task, S.N_samples.val*2, S.DAQtimeout.val)
                signal = np.mean(counts[0::2])
                background = np.mean(counts[1::2])
                if S.plotting_type.val == 'contrast': signal = np.divide(signal, background)
                self.plotdata[i] = (self.plotdata[i]*n + signal) / (n+1)
                self.set_progress((n*self.sweep.size+i+1)/(S.Navg.val*self.sweep.size) * 100)

    def _interrupt_(self) -> None:
        self.interrupt_measurement_called = True

    def _start_(self) -> None:
        self.activation.update_value(True)

    def _initialize_(self) -> None:
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

    def _finalize_(self) -> None:
        AWGctrl.SendScpi(self.inst, ":OUTP OFF")
        rc = self.admin.CloseInstrument(self.instId)
        AWGctrl.Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)
        rc = self.admin.Close()
        AWGctrl.Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)
        DAQ.closeDAQTask(self.task)

    def _make_savefiles_(self) -> None:
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

    def _save_data_(self) -> None:
        S = self.settings

        self.save_dict['sweep'] = self.sweep
        self.save_dict[f'average {S.plotting_type.val}'] = self.plotdata
        dataset = pd.DataFrame(self.save_dict)
        dataset.to_csv(self.csvfn)

        self.M['sweep'] = self.sweep
        self.M[f'average {S.plotting_type.val}'] = self.plotdata
        self.h5f.close()