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

'''import AWGcontrol as AWGctrl
import DAQ_Analog as DAQ'''

class Test(Measurement):
    
    name = 'Test'
    
    def setup(self):
        self.ui = load_qt_ui_file(sibling_path(__file__,"utils.ui"))
        self.ui.setWindowTitle(self.name)
        self.ui.interruptAOM_pushButton.clicked.connect(self._interrupt_)
        self.ui.startAOM_pushButton.clicked.connect(self._start_)

    def run(self):
        msr, LOG = timer(), self.LOG
        LOG(f"Testing")
        with msr:
            try:
                self._run_()
            except Exception: traceback.print_exc()
            finally: ...
        LOG(f'Total Time: {msr.t:.4f} s')
        #LOG(f'I WAITED FOR {msr.t:.4f} SECONDS >.< !!!')

    def _interrupt_(self) -> None:
        self.interrupt_measurement_called = True

    def _start_(self) -> None:
        self.activation.update_value(True)

    '''def _initialize_(self) -> None:
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
        DAQ.closeDAQTask(self.task)'''

    def _run_(self) -> None:
        '''while not self.interrupt_measurement_called:
            time.sleep(2)
            '''
        with Pool() as pool: pool.map(worker, range(100))
        self.LOG('HAI HEWWOO ^w^ !!!')

    def LOG(self, msg):
        self.app.logging_widget_handler.emit(makelog(self.name, msg))

def worker(id):
    time.sleep(1)


class TestApp(BaseMicroscopeApp):

    name = 'test_app'
    
    def setup(self):
        
        self.add_measurement(Test(self))
        self.ui.show()
        self.ui.activateWindow()

if __name__ == '__main__':
    app = TestApp(sys.argv)
    sys.exit(app.exec_())
    print(os.cpu_count())


