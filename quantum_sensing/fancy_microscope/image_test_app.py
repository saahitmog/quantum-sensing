from ScopeFoundry.base_app import BaseMicroscopeApp
from ScopeFoundry import Measurement
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
import pyqtgraph as pg

import sys, time
sys.path.append('../')
import movestages as pi_ctrl
import numpy as np

class ImageTestApp(BaseMicroscopeApp):

    name = 'image_test_app'
   
    def setup(self):
        self.add_measurement(ImageMeasure(self))

class ImageMeasure(Measurement):
    
    name = 'Image'
    
    def setup(self):
        
        S = self.settings

        S.New('N_pts', dtype=int, initial=100)
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
        self.ui.interrupt_pushButton.clicked.connect(self._interrupt)

        S.N_pts.connect_to_widget(self.ui.N_pts_doubleSpinBox)
        S.Navg.connect_to_widget(self.ui.Navg_doubleSpinBox)
    
        S.x_min.connect_to_widget(self.ui.xmin_doubleSpinBox)
        S.y_min.connect_to_widget(self.ui.ymin_doubleSpinBox)
        S.x_max.connect_to_widget(self.ui.xmax_doubleSpinBox)
        S.y_max.connect_to_widget(self.ui.ymax_doubleSpinBox)
        S.dx.connect_to_widget(self.ui.dx_doubleSpinBox)
        S.dy.connect_to_widget(self.ui.dy_doubleSpinBox)
        self.pos_buffer = {'x': None, 'y': None, 'r': None}

        self.stage = self._initialize_stages()

        self.graph_layout = pg.GraphicsLayoutWidget()
        self.ui.plot_groupBox.layout().addWidget(self.graph_layout)
        self.plot = self.graph_layout.addPlot(title="Signal vs Frequency")

        self.current_plotline = self.plot.plot()
        self.average_plotline = self.plot.plot()
        
    def run(self):
        S = self.settings
        xmin, ymin, xmax, ymax, dx, dy = S.x_min.val, S.y_min.val, S.x_max.val, S.y_max.val, S.dx.val, S.dy.val

        xy = np.mgrid[xmin:xmax:dx, ymin:ymax:dy].reshape(2,-1).T

        for x, y in xy:
            if self.interrupt_measurement_called:
                print('Interrupted')
                break
            self._execute_move(x, y)
            time.sleep(0.5)
            # DO MEASUREMENT

        self._execute_move(9, 9)
        pi_ctrl.closeDevice(self.stage)
        # print("Measurement Complete!")

    def _initialize_stages(self):
        return pi_ctrl.initializeController('LINEAR')

    def _execute_move(self, x, y):

        x_diff, y_diff= self.pos_buffer['x'] is None or x != self.pos_buffer['x'], \
                                 self.pos_buffer['y'] is None or y != self.pos_buffer['y']

        if x_diff and y_diff:
            pi_ctrl.moveToPos(self.stage, x, y)
            self.pos_buffer['x'], self.pos_buffer['y'] = x, y

        elif x_diff:
            pi_ctrl.moveToX(self.stage, x)
            self.pos_buffer['x'] = x

        elif y_diff:
            pi_ctrl.moveToY(self.stage, y)
            self.pos_buffer['y'] = y

        #if x_diff or y_diff:
        #    print("Stages Updated")

    def _interrupt(self):
        self.interrupt_measurement_called = True
        
if __name__ == '__main__':
    
    app = ImageTestApp(sys.argv)
    sys.exit(app.exec_())