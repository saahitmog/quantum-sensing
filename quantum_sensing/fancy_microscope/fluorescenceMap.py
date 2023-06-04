import AWGcontrol as AWGctl
import SRScontrol as SRSctl
import os
import inspect
import time
import numpy as np
import matplotlib.pyplot as plt
import DAQcontrol_SPD as DAQ
def main():
    task = DAQ.configureDAQ(2000)
    

    DAQ.closeDAQTask(task)
    print("closed")
main()