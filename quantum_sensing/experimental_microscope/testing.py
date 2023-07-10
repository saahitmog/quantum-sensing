import time
from utils import *
import warnings
from multiprocessing import Pool

def printer(): print('fsusibvsibvub')

def method(*args, **kwargs) -> bool:
    #time.sleep(1)
    return args

if __name__ == '__main__':
    with Pool() as pool:
        results = pool.map(method, range(100))

    #print(results)

