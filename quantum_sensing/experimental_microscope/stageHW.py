from ScopeFoundry import HardwareComponent
import os, sys
import movestages as PIctrl

class stageHW(HardwareComponent):

    name ='PI_stage'

    def setup(self):

        self.settings.New('x', dtype=float, unit='mm', si=True, initial=9, vmin=0, vmax=18)
        self.settings.New('y', dtype=float, unit='mm', si=True, initial=9, vmin=0, vmax=18)
        self.settings.New('r', dtype=float, unit='deg', initial=-30)
        self.cam = self.connect()

    def connect(self):

        self.linstage = PIctrl.initializeController('LINEAR')
        self.rotstage = PIctrl.initializeController('ROTATIONAL')
        self.move()

    def disconnect(self):
        PIctrl.closeDevice(self.linstage)
        PIctrl.closeDevice(self.rotstage)

    def move(self, x=None, y=None, r=None):
        if x is None:
            x = self.settings.x.val
        if y is None:
            y = self.settings.y.val
        if r is None:
            r = self.settings.r.val

        PIctrl.moveToPos(self.linstage, x, y)
        PIctrl.moveToAngle(self.rotstage, r)

        self.settings.x.update_value(x)
        self.settings.y.update_value(y)
        self.settings.r.update_value(r)
