import AWGcontrol as AWGctl
import SRScontrol as SRSctl
import os
import inspect
import time
import numpy as np
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
    # my_SRS = SRSctl.initSRS(27, 'SG384')
    # SRSctl.setSRS_RFAmplitude(my_SRS, 0.01, units = "Vpp")
    # # #set test frequency and modulation; ESR has no modulation but that's handled in the modulation function
    # SRSctl.setSRS_Freq(my_SRS, 100, 'MHz') 
    # SRSctl.setupSRSmodulation(my_SRS, 'ESRseq') 
    # SRSctl.enableSRS_RFOutput(my_SRS)
    # print('SRS Initialized')

    #AWGctl.makeSingleESRSeqMarker(inst, 0.0005, 0.025, 0.1)
    # AWGctl.instrumentCalls(inst, AWGctl.scaleWaveform(np.ones(899884800), "P9082M"))
    # AWGctl.makeMarker(inst, 899884800)
    #AWGctl.makeSingleRabiSeqMarker(inst, 0.0001, 0.0005, 0.1, 0.1)
    #AWGctl.makeT1SeqMarker(inst, 0.0005, 0.0005, 0.0004, 0.000001, 0.1, 0.1)
    AWGctl.makeT2Seq(inst, 0.00005, 0.0005, 0.0004, 0.00001, 0.01, 0.1)
    # AWGctl.SendScpi(inst, ":MARK:VOLT:PTOP:MAX?")
    # AWGctl.instrumentCalls(inst, AWGctl.scaleWaveform(AWGctl.squareWave(8998848), "P9082M"), 0.01)
    # SRSctl.setSRS_Freq(my_SRS, 100, 'MHz')
    print("generated, sleeping 90 seconds")
    time.sleep(120)

    AWGctl.SendScpi(inst, ":OUTP OFF")
    rc = admin.CloseInstrument(instId)
    AWGctl.Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)
    rc = admin.Close()
    AWGctl.Validate(rc, __name__, inspect.currentframe().f_back.f_lineno)
    print("closed")
main()