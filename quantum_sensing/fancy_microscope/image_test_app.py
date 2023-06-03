from ScopeFoundry.base_app import BaseMicroscopeApp
from ScopeFoundry import Measurement
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
import pyqtgraph as pg

import sys
sys.path.append('../')
from movestages import *
import numpy as np

class ImageTestApp(BaseMicroscopeApp):

    name = 'image_test_app'
   
    def setup(self):
        self.add_measurement(ImageMeasure(self))

class ImageMeasure(Measurement):
    
    name = 'Image'
    
    def setup(self):
        
        S = self.settings

        S.New('photon_mode', dtype=bool, initial=False)
        S.New('AWG_mode', dtype=bool, initial=True)
        S.New('Start_Frequency', dtype=float, initial=3.088, spinbox_decimals=4, unit='GHz', spinbox_step=0.001)
        S.New('End_Frequency', dtype=float, initial=3.11, spinbox_decimals=4, unit='GHz', spinbox_step=0.001)      
        S.New('Vpp', dtype=float, initial=0.2, spinbox_decimals=3, spinbox_step=0.01, unit='V', si=True)
        S.New('N_pts', dtype=int, initial=100)
        S.New('N_samples', dtype=int, initial=1000)
        S.New('DAQtimeout', dtype=int, initial=10, unit='s')
        S.New('t_duration', dtype=float, initial=0.0005, unit='s', si=True)
        S.New('magnet_current', dtype=float, initial=0.6)
        S.New('Navg', dtype=int, initial=10)

        S.New('x_min', dtype=float, initial=0, vmin=0.0, vmax=18.0)
        S.New('y_min', dtype=float, initial=0, vmin=0.0, vmax=18.0)
        S.New('x_max', dtype=float, initial=18.0, vmin=0.0, vmax=18.0)
        S.New('y_max', dtype=float, initial=18.0, vmin=0.0, vmax=18.0)
        S.New('dx', dtype=float, initial=0.1, vmin=1e-2, vmax=18.0)
        S.New('dy', dtype=float, initial=0.1, vmin=1e-2, vmax=18.0)
        
        self.ui_filename = sibling_path(__file__,"image_test.ui")
        self.ui = load_qt_ui_file(self.ui_filename)
        self.ui.setWindowTitle(self.name)
        
        S.activation.connect_to_widget(self.ui.start_box)
        self.ui.interrupt_pushButton.clicked.connect(self.execute_move)

        S.N_pts.connect_to_widget(self.ui.N_pts_doubleSpinBox)
        S.Navg.connect_to_widget(self.ui.Navg_doubleSpinBox)
    
        S.x_min.connect_to_widget(self.ui.xmin_doubleSpinBox)
        S.y_min.connect_to_widget(self.ui.ymin_doubleSpinBox)
        S.x_max.connect_to_widget(self.ui.xmax_doubleSpinBox)
        S.y_max.connect_to_widget(self.ui.ymax_doubleSpinBox)
        S.dx.connect_to_widget(self.ui.dx_doubleSpinBox)
        S.dy.connect_to_widget(self.ui.dy_doubleSpinBox)
        self.pos_buffer = {'x': None, 'y': None, 'r': None}

        self._execute_move()

        self.graph_layout = pg.GraphicsLayoutWidget()
        self.ui.plot_groupBox.layout().addWidget(self.graph_layout)
        self.plot = self.graph_layout.addPlot(title="Signal vs Frequency")

        self.current_plotline = self.plot.plot()
        self.average_plotline = self.plot.plot()
        
    def run(self):
        S = self.settings
        xmin, ymin, xmax, ymax, dx, dy = S.x_min.val, S.y_min.val, S.x_max.val, S.y_max.val, S.dx.val, S.dy.val

        xy = np.mgrid[xmin:xmax:dx, ymin:ymax:dy].reshape(2,-1).T
        print(xy)
        
        print("App terminated. Goodbye!")

    def _execute_move(self):
        x, y, r = self.settings.x_pos.val, self.settings.y_pos.val, self.settings.r_pos.val

        devices, moved = [], []
        x_diff, y_diff, r_diff = self.pos_buffer['x'] is None or x != self.pos_buffer['x'], \
                                 self.pos_buffer['y'] is None or y != self.pos_buffer['y'], \
                                 self.pos_buffer['r'] is None or r != self.pos_buffer['r']

        if x_diff and y_diff:
            device = initializeController('LINEAR')
            devices.append(device)
            moveToPos(device, x, y)
            self.pos_buffer['x'], self.pos_buffer['y'] = x, y
            moved.append('x')
            moved.append('y')

        elif x_diff:
            device = initializeController('LINEAR')
            devices.append(device)
            moveToX(device, x)
            self.pos_buffer['x'] = x
            moved.append('x')

        elif y_diff:
            device = initializeController('LINEAR')
            devices.append(device)
            moveToY(device, y)
            self.pos_buffer['y'] = y
            moved.append('y')

        if r_diff:
            device = initializeController('ROTATIONAL')
            devices.append(device)
            moveToAngle(device, r)
            self.pos_buffer['r'] = r
            moved.append('r')
        
        for device in devices:
            closeDevice(device)

        if x_diff or y_diff or r_diff:
            print("Stages Moved")
        
if __name__ == '__main__':
    
    app = ImageTestApp(sys.argv)
    sys.exit(app.exec_())