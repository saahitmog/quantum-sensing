import time
from utils import *
import warnings


def printer(): print('fsusibvsibvub')

@ignore(Warning)
def my_method_decorator(*args, **kwargs) -> bool:
    warnings.warn("WARNING", UserWarning)
    time.sleep(1)
    print('doin stuffs')

if __name__ == '__main__':
    with timer('Timer test: '): my_method_decorator()

