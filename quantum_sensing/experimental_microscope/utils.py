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
    def __enter__(self, msg: str = ''):
        self.start_time = time.perf_counter()
        self.msg = msg

    def __exit__(self, exc_type, exc_val, exc_tb):
        t = time.perf_counter()-self.start_time
        print(self.msg, f'{t:.4f} seconds', sep='')

def ignore(warning: Type[Warning]):
    def inner(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=warning)
                return func(*args, **kwargs)
        return wrapper
    return inner

