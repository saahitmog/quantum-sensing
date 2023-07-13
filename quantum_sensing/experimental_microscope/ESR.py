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

class ESRMeasure(Measurement):
    
    name = 'ESR'
    
    def setup(self):
        
        S = self.settings

        S.New('Npts', dtype=int, initial=100, vmin=0)
        S.New('Navg', dtype=int, initial=10, vmin=1)
        S.New('photon_mode', dtype=bool, initial=False)
        S.New('AWG_mode', dtype=bool, initial=True)
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
        S.New('save', dtype=bool, initial=False)

        self.ui_filename = sibling_path(__file__,"ESR.ui")
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
        S.save.connect_to_widget(self.ui.save_CheckBox)
        S.plotting_type.connect_to_widget(self.ui.plot_ComboBox)

    def setup_figure(self):
        self.plotdata, self.sweep = np.array([]), np.array([])
        self.graph_layout = pg.GraphicsLayoutWidget()
        self.ui.plot_groupBox.layout().addWidget(self.graph_layout)
        self.plot = self.graph_layout.addPlot(title="")
        self.plotline = self.plot.plot()

    def run(self):
        msr, S, LOG = timer(), self.settings, self.LOG
        with msr:
            if S.save.val: self._make_savefiles_()

            LOG(f"Starting {self.name} Measurement in {S.plotting_type.val.capitalize()} Mode")

            self.sweep = np.linspace(S.Start_Frequency.val, S.End_Frequency.val, num=S.Npts.val)
            self.plotdata = np.zeros_like(self.sweep)

            try:
                hws = timer()
                with hws, hide(): self._initialize_()
                if self.inst: 
                    LOG(f'Hardware Startup: {hws.t:.4f} s')
                    if S.sweep.val: self._run_sweep_()
                    else: self._run_()

            except Exception: traceback.print_exc()

            finally:
                if self.inst:
                    hwc = timer()
                    with hwc: self._finalize_()
                    LOG(f'Hardware Close: {hwc.t:.4f} s')
                if S.save.val: self._save_data_()
        LOG(f'Measurement Complete: {msr.t:.4f} s')
        
    def update_display(self):
        if self.settings.plotting_type.val == 'signal': self.plot.setTitle("Signal vs Frequency")
        else: self.plot.setTitle("Contrast vs Frequency")
        self.plotline.setData(self.sweep, self.plotdata)

    def post_run(self): 
        with hide(): self.app.settings_save_ini('.config.ini')

    def _run_sweep_(self) -> None:
        S, LOG = self.settings, self.LOG
        LOG(f'Sweeping Frequencies from {self.sweep[0]:.4f} GHz to {self.sweep[-1]:.4f} GHz at {self.sweep.size} points.')
        self.task = task = DAQ.configureDAQ(S.N_samples.val * S.Npts.val)
        signal = np.zeros(self.sweep.shape, dtype=float)
        background = np.zeros(self.sweep.shape, dtype=float)
        awg = timer()
        with awg: AWGctrl.makeESRSweep(self.inst, S.t_duration.val, self.sweep, S.Vpp.val)
        LOG(f'AWG Write: {awg.t:.4f} s')

        for n in range(S.Navg.val):
            LOG(f'Averaging Run {n+1}')
            if self.interrupt_measurement_called:
                    LOG('Measurement Interrupted')
                    break
            daq = timer()
            with daq: counts = DAQ.readDAQ(task, S.N_samples.val*S.Npts.val*2, S.DAQtimeout.val)
            LOG(f'DAQ Read: {daq.t:.4f} s')

            
            for i in range(self.sweep.size): signal[i], background[i] = np.mean(counts[2*i::2*self.sweep.size]), np.mean(counts[2*i+1::2*self.sweep.size])
            signal, background = np.mean(counts.reshape(self.sweep.size, -1)[:,::2], axis=1), np.mean(counts.reshape(self.sweep.size, -1)[:,1::2], axis=1)


            if S.plotting_type.val == 'contrast': signal = np.divide(signal, background)
            self.plotdata = ((self.plotdata*n) + signal) / (n+1)
            self.set_progress(n/S.Navg.val * 100)

    def _run_(self) -> None:
        S, LOG = self.settings, self.LOG
        self.task = DAQ.configureDAQ(self.settings.N_samples.val)
        interrupted = False
        for n in range(S.Navg.val):
            if interrupted: break
            LOG(f'Starting Averaging Run {n+1}')
            for i, f in enumerate(self.sweep):
                if self.interrupt_measurement_called:
                    interrupted = True
                    LOG('Measurement Interrupted')
                    break
                LOG(f'Frequency: {f:.4f} GHz')
                awg = timer()
                with awg: AWGctrl.makeSingleESRSeqMarker(self.inst, S.t_duration.val, f, S.Vpp.val)
                LOG(f'AWG Write: {awg.t:.4f} s')
                daq = timer()
                with daq: counts = DAQ.readDAQ(self.task, S.N_samples.val*2, S.DAQtimeout.val)
                LOG(f'DAQ Read: {daq.t:.4f} s')
                signal, background = np.mean(counts[0::2]), np.mean(counts[1::2])
                if S.plotting_type.val == 'contrast': signal = np.divide(signal, background)
                self.plotdata[i] = (self.plotdata[i]*n + signal) / (n+1)
                self.set_progress((n*self.sweep.size+i+1)/(S.Navg.val*self.sweep.size) * 100)

    def _interrupt_(self) -> None:
        self.interrupt_measurement_called = True

    def _start_(self) -> None:
        self.activation.update_value(True)

    def _initialize_(self) -> None:
        self.admin, self.inst = AWGctrl.loadDLL(), None
        slotId = AWGctrl.getSlotId(self.admin)
        if slotId:
            self.inst = self.admin.OpenInstrument(slotId)
            if self.inst: self.instId = self.inst.InstrId
        if not slotId or not self.inst: self.LOG('Hardware Connection Failed')
        AWGctrl.instrumentSetup(self.inst)
        
    def _finalize_(self) -> None:
        AWGctrl.SendScpi(self.inst, ":OUTP OFF; :MARK OFF")
        self.admin.CloseInstrument(self.instId)
        self.admin.Close()
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
        h5_io.h5_save_measurement_settings(self, self.M)
        self.h5f.close()

    def LOG(self, msg):
        self.app.logging_widget_handler.emit(makelog(self.name, msg))