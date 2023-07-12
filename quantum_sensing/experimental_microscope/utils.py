import sys, os, time
import functools
import warnings
from typing import Type

class hide:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout

class timer:
    def __init__(self, msg: str = '', quiet: bool = False):
        self.msg, self.quiet = msg, quiet

    def __enter__(self):
        self.start_time = time.perf_counter()

    def __exit__(self, exc_type, exc_val, exc_tb):
        t = time.perf_counter()-self.start_time
        if not self.quiet: print(self.msg, f'{t:.4f} seconds', sep='')

def ignore(warning: Type[Warning]):
    def inner(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=warning)
                return func(*args, **kwargs)
        return wrapper
    return inner

from ScopeFoundry import Measurement
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
import os, inspect, traceback
import numpy as np
import AWGcontrol as AWGctrl

class AOMToggle(Measurement):
    
    name = 'Utility'
    
    def setup(self):
        self.ui_filename = sibling_path(__file__,"utils.ui")
        self.ui = load_qt_ui_file(self.ui_filename)
        self.ui.setWindowTitle(self.name)
        self.ui.interrupt_pushButton.clicked.connect(self._interrupt_)
        self.ui.start_pushButton.clicked.connect(self._start_)

    def run(self):
        print(f"Toggling AOM")
        try:
            with hide(): self._initialize_()
            print('----- AOM ON -----')
            self._run_()
        except Exception: traceback.print_exc()
        finally: 
            self._finalize_()
            print('----- AOM OFF -----')

    def _interrupt_(self) -> None:
        self.interrupt_measurement_called = True

    def _start_(self) -> None:
        self.activation.update_value(True)

    def _run_(self) -> None:
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
