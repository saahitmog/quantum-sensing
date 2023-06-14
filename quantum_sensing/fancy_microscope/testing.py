#import AWGcontrol as AWGctrl
import numpy as np, multiprocessing as mp
import matplotlib.pyplot as plt
from cProfile import run
from memory_profiler import profile
import time
import AWGcontrol as AWGctl

if __name__ == '__main__':
    #run('orig(100)', sort='cumtime')
    #run('fast(100)', sort='cumtime')
    #fast(500)
    #orig(100)
    admin = AWGctl.loadDLL()
    slotId = AWGctl.getSlotId(admin)
    if not slotId:
        print("Invalid choice!")
    else:
        inst = admin.OpenInstrument(slotId)
        if not inst:
            print("Failed to Open instrument with slot-Id {0}".format(slotId))
            print("\n")
        else:
            instId = inst.InstrId
    AWGctl.instrumentSetup(inst)
    AWGctl.testWrite(inst)
