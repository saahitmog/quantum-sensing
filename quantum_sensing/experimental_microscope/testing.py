import time
from utils import *
import warnings, numpy as np
from multiprocessing import Pool
from matplotlib import pyplot as plt
from cProfile import run
from scipy import signal as sg

def rabi(seg, cyc, mw_delay, mw_duration, amp):
    t = np.arange(seg, step=1)
    omegaSin = 2 * np.pi * cyc
    pre, pulse, post = int((mw_delay-mw_duration)*seg//1e6), int(round(mw_duration*seg/1e6)), int(seg-mw_delay*seg//1e6)
    pre, pulse, post = np.zeros(pre, dtype=int), np.ones(pulse, dtype=int), np.zeros(post, dtype=int)
    print(pre.size, pulse.size, post.size)
    sq = np.concatenate((pre, pulse, post))
    sn = np.sin(omegaSin*t/seg)
    rawSignal = sq * amp * sn
    dacSignal = np.uint8((rawSignal/amp*127)+127)
    del t, sq, sn #, rawSignal
    return rawSignal

'''from AWGcontrol import *
from DAQ_Analog import *

def seqgen(inst, dur, freq, vpp):
    segmentLength = 8998848 #this segment length is optimized for 1kHz trigger signal
    segmentLength = int((2*dur/0.001)*segmentLength)
    cycles = int(freq * segmentLength / 9)

    print(f'--> Frequency: {freq} GHz')
    instrumentCalls(inst, fastsine(segmentLength, cycles, 1), vpp)
    makeESRMarker(inst, segmentLength)

def AWGtest(N=100, dur=0.0005, f=2):
    admin = loadDLL()
    slotId = getSlotId(admin)
    if slotId:
        inst = admin.OpenInstrument(slotId)
        if inst: instId = inst.InstrId
    instrumentSetup(inst)
    task = configureDAQ(10)
    for _ in range(N):
        makeSingleESRSeqMarker(inst, dur, f, 0.1)
        readDAQ(task, 10*2, 10)
    #task = configureDAQ(1000*N)
    #makeESRSweep(inst, dur, np.full(N, f), 0.1)
    #readDAQ(task, 1000*N*2, 1000)

    SendScpi(inst, ":OUTP OFF")
    #SendScpi(inst, ":MARK OFF")
    admin.CloseInstrument(instId)
    admin.Close()
    closeDAQTask(task)'''

from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
from ScopeFoundry import Measurement, BaseMicroscopeApp
import traceback, sys
import numpy as np

import AWGcontrol as AWGctrl
import DAQ_Analog as DAQ
import pyqtgraph as pg

class Test(Measurement):
    
    name = 'Test'
    
    def setup(self):
        self.ui = load_qt_ui_file(sibling_path(__file__,"utils.ui"))
        self.ui.setWindowTitle(self.name)
        self.ui.interruptAOM_pushButton.clicked.connect(self._interrupt_)
        self.ui.startAOM_pushButton.clicked.connect(self._start_)
        self.n, self.N, self.mode = 50, 5, 'contrast'

    def setup_figure(self):
        self.plotdata, self.sweep = np.array([]), np.array([])
        self.graph_layout = pg.GraphicsLayoutWidget()
        self.ui.plot_groupBox.layout().addWidget(self.graph_layout)
        self.plot = self.graph_layout.addPlot(title="")
        self.plotline = self.plot.plot()

    def update_display(self):
        self.plot.setTitle(f"{self.mode.capitalize()} vs Frequency")
        self.plotline.setData(self.sweep, self.plotdata)

    def run(self):
        msr, LOG = timer(), self.LOG
        LOG(f"Testing ESR Sweep")
        with msr:
            try:
                hws = timer()
                with hws, hide(): self._initialize_()
                LOG(f'Hardware Startup: {hws.t:.4f} s')
                self._run_()
            except Exception: traceback.print_exc()
            finally:
                hwc = timer()
                with hwc: self._finalize_()
                LOG(f'Hardware Close: {hwc.t:.4f} s')
        LOG(f'Total Time: {msr.t:.4f} s')
        #LOG(f'I WAITED FOR {msr.t:.4f} SECONDS >.< !!!')

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
        AWGctrl.SendScpi(self.inst, ":OUTP OFF; :MARK OFF")
        self.admin.CloseInstrument(self.instId)
        self.admin.Close()
        DAQ.closeDAQTask(self.task)

    def _run_(self) -> None:
        n, N = self.n, self.N
        LOG, sweep = self.LOG, np.linspace(2.79, 2.95, n)
        signal, background = np.zeros(n, dtype=float), np.zeros(n, dtype=float)
        LOG(f'Sweeping Frequencies from {sweep[0]:.4f} GHz to {sweep[-1]:.4f} GHz at {n} points.')

        self.task = DAQ.configureDAQ(100 * n)

        awg = timer()
        with awg: AWGctrl.makeESRSweep(self.inst, 0.0005, sweep, 0.1)
        LOG(f'AWG Write: {awg.t:.4f} s')
        
        for _n in range(N):
            LOG(f'Starting Averaging Run {_n+1}')
            if self.interrupt_measurement_called:
                    LOG('Measurement Interrupted')
                    break
            daq = timer()
            with daq: counts = DAQ.readDAQ(self.task, 100 * n * 2, 1000)
            LOG(f'DAQ Read: {daq.t:.4f} s')

            for i in range(n): signal[i], background[i] = np.mean(counts[2*i::2*n]), np.mean(counts[2*i+1::2*n])
            if self.mode == 'contrast': signal = np.divide(signal, background)
            self.plotdata = ((self.plotdata*n) + signal) / (n+1)
            self.set_progress(_n/N * 100)
            #LOG('HAI HEWWOO ^w^ !!!')

    def LOG(self, msg):
        record = makelog(self.name, msg)
        self.app.logging_widget_handler.emit(record)


class TestApp(BaseMicroscopeApp):

    name = 'test_app'
    
    def setup(self):
        
        self.add_measurement(Test(self))
        self.ui.show()
        self.ui.activateWindow()

if __name__ == '__main__':
    app = TestApp(sys.argv)
    sys.exit(app.exec_())


