from ScopeFoundry import HardwareComponent
import movestages as PIctrl

class stageHW(HardwareComponent):

    name ='PI_stage'

    def setup(self):

        self.settings.New('x', dtype=float, unit='mm', si=True, vmin=-9, vmax=9, initial=0)
        self.settings.New('y', dtype=float, unit='mm', si=True, vmin=-9, vmax=9, initial=0)
        self.settings.New('r', dtype=float, unit='deg', initial=-30)
        self.add_operation('Move', self.move)

    def connect(self):
        self.linstage = PIctrl.initializeController('LINEAR')
        self.rotstage = PIctrl.initializeController('ROTATIONAL')

    def disconnect(self):
        if hasattr(self, 'linstage'):
            PIctrl.closeDevice(self.linstage)
        if hasattr(self, 'rotstage'):
            PIctrl.closeDevice(self.rotstage)

    def move(self, x=None, y=None, r=None):
        S = self.settings
        if x is None:
            x = S.x.val
        if y is None:
            y = S.y.val
        if r is None:
            r = S.r.val

        PIctrl.moveToPos(self.linstage, x, y)
        PIctrl.moveToAngle(self.rotstage, r)

        S.x.update_value(x)
        S.y.update_value(y)
        S.r.update_value(r)
