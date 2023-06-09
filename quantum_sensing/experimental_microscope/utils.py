import sys, os, time
import functools
import warnings
from typing import Type
from  logging import LogRecord

class hide:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout

class timer:
    def __init__(self):
        self.t = 0
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.t = time.perf_counter()-self.start_time

def ignore(warning: Type[Warning]):
    def inner(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=warning)
                return func(*args, **kwargs)
        return wrapper
    return inner

def makelog(measurement, msg): return LogRecord(measurement, 20, __file__, 0, ' '+msg, None, None)
def sleeper(id): time.sleep(1)

from ScopeFoundry import Measurement
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
import os, traceback
import numpy as np
import AWGcontrol as AWGctrl

class Utility(Measurement):
    
    name = 'Utility'
    
    def setup(self):
        self.ui = load_qt_ui_file(sibling_path(__file__,"utils.ui"))
        self.ui.setWindowTitle(self.name)
        self.ui.interruptAOM_pushButton.clicked.connect(self._interrupt_)
        self.ui.startAOM_pushButton.clicked.connect(self._start_)

    def run(self):
        LOG = self.LOG
        LOG(f"Toggling AOM")
        mode = 'AOM'
        try:
            with hide(): self._initialize_()
            LOG('AOM ON')
            if mode == 'AOM': self.runAOM()
        except Exception: traceback.print_exc()
        finally: 
            self._finalize_()
            LOG('AOM OFF')

    def _interrupt_(self) -> None:
        self.interrupt_measurement_called = True

    def _start_(self) -> None:
        self.activation.update_value(True)

    def runAOM(self) -> None:
        AWGctrl.SendScpi(self.inst, ":MARK OFF")
        self.inst.WriteBinaryData(':MARK:DATA 0,#', np.full(999872, 4, dtype=np.uint8).tobytes())
        AWGctrl.SendScpi(self.inst, ":MARK:SEL 3; :MARK:VOLT:PTOP 1.2; :MARK ON")
        while not self.interrupt_measurement_called: pass

    def _initialize_(self) -> None:
        self.admin = admin = AWGctrl.loadDLL()
        slotId = AWGctrl.getSlotId(admin)
        if slotId:
            self.inst = inst = admin.OpenInstrument(slotId)
            if inst: self.instId = inst.InstrId
        AWGctrl.instrumentSetup(inst)

    def _finalize_(self) -> None:
        AWGctrl.SendScpi(self.inst, ":OUTP OFF; :MARK OFF")
        self.admin.CloseInstrument(self.instId)
        self.admin.Close()

    def LOG(self, msg):
        record = makelog(self.name, msg)
        self.app.logging_widget_handler.emit(record)
