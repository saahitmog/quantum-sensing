import sys
import numpy as np
 
import pyqtgraph as pg
from PyQt5.QtGui import *
 
 
class Window(QMainWindow):
 
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 600, 500)
        #icon = QIcon("skin.png")
        #self.setWindowIcon(icon)

        self.xs = np.arange(0, 18.1, 6)
        self.ys = np.arange(0, 18.1, 9)
        self.sweep = np.linspace(0, 100)
        self.data = np.empty((self.xs.size, self.ys.size, self.sweep.size))
        self._fill()

        self.ui()
        self.show()
 
    def ui(self):

        widget = pg.GraphicsLayoutWidget()
        
        for i, x in enumerate(self.xs):
            for j, y in enumerate(self.ys):
                plot = widget.addPlot(row=y, col=x)
                plot.setTitle(f'{x}, {y}')
                plotline = plot.plot()
                plotline.setData(self.sweep, self.data[i, j])

        self.setCentralWidget(widget)

    def _fill(self):
        rng = np.random.default_rng()
        for i in self.data:
            for j in i:
                rand = rng.random(size=self.sweep.size)
                np.copyto(j, rand)
 
App = QApplication(sys.argv)
window = Window()
sys.exit(App.exec())