#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
(c)2018 Physik Instrumente (PI) GmbH & Co. KG
Software products that are provided by PI are subject to the General Software License Agreement of Physik Instrumente (PI) GmbH & Co. KG and may incorporate and/or make use of third-party software components. For more information, please read the General Software License Agreement and the Third Party Software Note linked below.
General Software License Agreement :
http://www.physikinstrumente.com/download/EULA_PhysikInstrumenteGmbH_Co_KG.pdf
Third Party Software Note :
http://www.physikinstrumente.com/download/TPSWNote_PhysikInstrumenteGmbH_Co_KG.pdf
'''

"""This example shows how to move all connected axes of an E-135 open loop."""

from pipython import GCSDevice
from pipython.pitools import waitonwalk


def main():
    """Connect E-135 and move all connected axes open loop.
    Remember you can move only one axis at a time.
    """
    with GCSDevice('E-135') as pidevice:
        pidevice.InterfaceSetupDlg(key='sample')
        print('connected: {}'.format(pidevice.qIDN().strip()))
        for axis in pidevice.axes:
            print('move axis {} forward...'.format(axis))
            pidevice.OSM(axis, 5)
            waitonwalk(pidevice, axis)
            print('move axis {} backward...'.format(axis))
            pidevice.OSM(axis, -5)
            waitonwalk(pidevice, axis)
    print('finished')


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.DEBUG)
    main()
