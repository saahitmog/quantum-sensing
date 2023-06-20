#import AWGcontrol as AWGctrl
import numpy as np
import matplotlib.pyplot as plt
import time
import AWGcontrol as AWGctl

if __name__ == '__main__':
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

    freq, vpp = 4.5e9, 1.2
    AWGctl.SendScpi(inst, ":INST:CHAN 1")
    AWGctl.SendScpi(inst, ":MODE NCO")
    AWGctl.SendScpi(inst, f":NCO:CFR1 {freq}")
    AWGctl.SendScpi(inst, f":SOUR:VOLT {vpp}")

    AWGctl.SendScpi(inst, ":OUTP ON")

    #freqs = np.array([0.1]) np.arange(0.1, 1.1, 0.1)
    #AWGctl.makeESRSweep(inst, 0.0005, freqs, 0.2)

    time.sleep(120)

    AWGctl.SendScpi(inst, ":OUTP OFF")
    #AWGctl.SendScpi(inst, ":MARK OFF")
