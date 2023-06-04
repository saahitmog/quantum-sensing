import AWGcontrol as AWGctl
import os
import inspect
import time
def main():
    print('Process Id = {0}'.format(os.getpid()))
    admin = AWGctl.loadDLL()
    slotId = AWGctl.getSlotId(admin)
    if not slotId:
        print("Invalid choice!")
    else:
        inst = admin.OpenInstrument(slotId)
        if not inst:
            print("Failed to Open instrument with slot-Id {0}".format(slotId))  # @IgnorePep8
            print("\n")
        else:
            instId = inst.InstrId
    AWGctl.instrumentSetup(inst)
    print('AWG Initialized')

    AWGctl.makeSingleESRSeqMarker(inst, 0.0005, 0.25, 0.2)
    print("generated, sleeping 90 seconds")
    time.sleep(90)

    AWGctl.SendScpi(inst, ":OUTP OFF")
    rc = admin.CloseInstrument(instId)
    AWGctl.Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)
    rc = admin.Close()
    AWGctl.Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)
    print("closed")
main()