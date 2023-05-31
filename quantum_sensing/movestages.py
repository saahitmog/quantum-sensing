"""
HOW TO USE: Takes two arguments after file name. 
First argument must be 'X' 'Y' or 'R' to specify X, Y, and Rotational stages respectively. 
Second argument must be the position to move the specified stage to: range is 0 to 18 for both X and Y linear stages and 0 to 360 for rotational stage
Example usages: 'python movestages.py X 9' 'python movestages.py R 30'
"""


from __future__ import print_function
from shutil import move
__signature__ = 0x59b6d589fbcaf327eedc4f70f9f539cc
#!/usr/bin/python
# -*- coding: utf-8 -*-
"""This example helps you to get used to PIPython."""

# (c)2016-2020 Physik Instrumente (PI) GmbH & Co. KG
# Software products that are provided by PI are subject to the
# General Software License Agreement of Physik Instrumente (PI) GmbH & Co. KG
# and may incorporate and/or make use of third-party software components.
# For more information, please read the General Software License Agreement
# and the Third Party Software Note linked below.
# General Software License Agreement:
# http://www.physikinstrumente.com/download/EULA_PhysikInstrumenteGmbH_Co_KG.pdf
# Third Party Software Note:
# http://www.physikinstrumente.com/download/TPSWNote_PhysikInstrumenteGmbH_Co_KG.pdf


import time
from pipython import GCSDevice
from pipython.pidevice.gcs2 import gcs2pitools
import sys

"""Initializes the motion control chip for 'axes'.
   The following actions are done by INI(): Writes the stage parameters which were loaded
   with CST() from the stage database to the controller. Switches the servo on. Sets
    reference mode to True, i.e. REF(), FRF(), MNL(), FNL(), MPL() or FPL() is required to
    reference the axis, usage of POS() is not allowed. Sets reference state to "not
   referenced". If the stage has tripped a limit switch, INI() will move it away from the
    limit switch until the limit condition is no longer given, and the target position is set
    to the current position afterwards. Sets trigger output mode to default configuration.
    @param axes : String convertible or list of them or None.
    """

#CONTROLLERNAME = 'C-867.2U2'  # 'C-884' will also work
#CONTROLLERNAME = 'C-867.1U'
CONTROLLERNAME = {'LINEAR': 'C-867.2U2', 'ROTATIONAL': 'C-867.1U'}
#STAGES = ['U-521.24', 'M-122.2DD', 'NOSTAGE', 'NOSTAGE']
#STAGES = ['U-521.24', 'U-521.24']
#STAGES = ['U-624K010']
STAGES = {'LINEAR': ['U-521.24', 'U-521.24'], 'ROTATIONAL': ['U-624K010']}
#REFMODES = ['FRF', 'FRF']
#REFMODES = 'FNL'
REFMODES = {'LINEAR': ['FRF', 'FRF'], 'ROTATIONAL': 'FNL'}
SERIALNUMBERS = {'LINEAR':'0120033713', 'ROTATIONAL':'0121005792'}
#CONTROLLERNAME = ''

# CONTROLLERNAME = 'E-709'
# STAGES = None  # this controller does not need a 'stages' setting
# REFMODES = None

# CONTROLLERNAME = 'C-887'
# STAGES = None  # this controller does not need a 'stages' setting
# REFMODES = 'FRF'

# CONTROLLERNAME = 'Hydra'
# STAGES = ('6233-9-2203', 'NOSTAGE')
# REFMODES = ('FNL',)

# CONTROLLERNAME = 'C-863.11'
# STAGES = ('M-111.1DG',)  # connect stages to axes
# REFMODES = ('FNL',)  # reference the connected stages


def main():

    """Connect, setup system and move stages and display the positions in a loop."""
    if(len(sys.argv) != 3):
        print('Too few or too many arguments: must be 2 arguments (i.e. python movestages.py X 9)')
        quit()
    if(sys.argv[1] not in ['X', 'x', 'Y', 'y', 'R', 'r']):
        print('Stage must be specified as X, Y, or R')
        quit()
    if(sys.argv[1] in ['X', 'x']):
        if(int(sys.argv[2]) < 0 or int(sys.argv[2]) > 18):
            print('Position out of range: must be between 0 and 18 for X stage')
            quit()
        stageType = 'LINEAR'
        device = initializeController(stageType)
        moveToX(device, int(sys.argv[2]))
        closeDevice(device)
        quit()
    if(sys.argv[1] in ['Y', 'y']):
        if(int(sys.argv[2]) < 0 or int(sys.argv[2]) > 18):
            print('Position out of range: must be between 0 and 18 for Y stage')
            quit()
        stageType = 'LINEAR'
        device = initializeController(stageType)
        moveToY(device, int(sys.argv[2]))
        closeDevice(device)
        quit()
    if(sys.argv[1] in ['R', 'r']):
        # if(int(sys.argv[2]) < 0 or int(sys.argv[2]) > 360):
        #     print('Position out of range: must be between 0 and 360 for Rotational stage')
        #     quit()
        stageType = 'ROTATIONAL'
        device = initializeController(stageType)
        moveToAngle(device, int(sys.argv[2]))
        closeDevice(device)
        quit()

def moveToAngle(pidevice, pos):
    testMove(pidevice, [pos])

def moveToPos(pidevice, xpos, ypos):
    moveX(pidevice, [xpos])
    moveY(pidevice, [ypos])

def moveToX(pidevice, xpos):
    moveX(pidevice, [xpos])

def moveToY(pidevice, ypos):
    moveY(pidevice, [ypos])

def moveX(pidevice, posList):
    for axis in ['1']:
        for target in posList:
            #print('move axis {} to {:.2f}'.format(axis, target))
            pidevice.MOV(axis, target)

                # To check the "on target state" of an axis there is the GCS command
                # qONT(). But it is more convenient to just call "waitontarget".

            gcs2pitools.waitontarget(pidevice, axes=axis)

                # GCS commands usually can be called with single arguments, with
                # lists as arguments or with a dictionary.
                # If a query command is called with an argument the keys in the
                # returned dictionary resemble the arguments. If it is called
                # without an argument the keys are always strings.

            position = pidevice.qPOS(axis)[axis]  # query single axis
                # position = pidevice.qPOS()[str(axis)] # query all axes
            #print('current position of axis {} is {:.2f}'.format(axis, position))
    #print('done') 
   
def moveY(pidevice, posList):
    for axis in ['2']:
        for target in posList:
            #print('move axis {} to {:.2f}'.format(axis, target))
            pidevice.MOV(axis, target)

                # To check the "on target state" of an axis there is the GCS command
                # qONT(). But it is more convenient to just call "waitontarget".

            gcs2pitools.waitontarget(pidevice, axes=axis)

                # GCS commands usually can be called with single arguments, with
                # lists as arguments or with a dictionary.
                # If a query command is called with an argument the keys in the
                # returned dictionary resemble the arguments. If it is called
                # without an argument the keys are always strings.

            position = pidevice.qPOS(axis)[axis]  # query single axis
                # position = pidevice.qPOS()[str(axis)] # query all axes
            #print('current position of axis {} is {:.2f}'.format(axis, position))
    #print('done')  

def initializeController(stageType):
    if stageType not in ['LINEAR', 'ROTATIONAL']:
        print('Error: Stage Type must be LINEAR or ROTATIONAL')
        return
    else:
        pidevice = GCSDevice(CONTROLLERNAME[stageType])
        # Choose the interface according to your cabling.

        # pidevice.ConnectTCPIP(ipaddress='192.168.90.207')
        pidevice.ConnectUSB(serialnum=SERIALNUMBERS[stageType])
        # pidevice.ConnectRS232(comport=1, baudrate=115200)

        # Controllers like C-843 and E-761 are connected via PCI.
        # pidevice.ConnectPciBoard(board=1)

        # Each PI controller supports the qIDN() command which returns an
        # identification string with a trailing line feed character which
        # we "strip" away.

        #print('connected: {}'.format(pidevice.qIDN().strip()))

        # Show the version info which is helpful for PI support when there
        # are any issues.

        if pidevice.HasqVER():
            #print('version info:\n{}'.format(pidevice.qVER().strip()))
            pass

        # In the module pipython.pitools there are some helper
        # functions to make using a PI device more convenient. The "startup"
        # function will initialize your system. There are controllers that
        # cannot discover the connected stages hence we set them with the
        # "stages" argument. The desired referencing method (see controller
        # user manual) is passed as "refmode" argument. All connected axes
        # will be stopped if they are moving and their servo will be enabled.
        #print('initialize connected stages...')
        gcs2pitools.startup(pidevice, stages=STAGES[stageType], refmodes=REFMODES[stageType])
        return pidevice

def testMove(pidevice, posList):
    for axis in pidevice.axes:
        for target in posList:
            #print('move axis {} to {:.2f}'.format(axis, target))
            pidevice.MOV(axis, target)

                # To check the "on target state" of an axis there is the GCS command
                # qONT(). But it is more convenient to just call "waitontarget".

            gcs2pitools.waitontarget(pidevice, axes=axis)

                # GCS commands usually can be called with single arguments, with
                # lists as arguments or with a dictionary.
                # If a query command is called with an argument the keys in the
                # returned dictionary resemble the arguments. If it is called
                # without an argument the keys are always strings.

            position = pidevice.qPOS(axis)[axis]  # query single axis
                # position = pidevice.qPOS()[str(axis)] # query all axes
            #print('current position of axis {} is {:.2f}'.format(axis, position))
    #print('done')
    
def closeDevice(device):
    device.close()

if __name__ == '__main__':
    # To see what is going on in the background you can remove the following
    # two hashtags. Then debug messages are shown. This can be helpful if
    # there are any issues.

    # import logging
    # logging.basicConfig(level=logging.DEBUG)
    main()
