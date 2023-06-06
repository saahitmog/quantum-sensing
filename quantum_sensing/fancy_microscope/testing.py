import sys
import numpy as np
 
import pyqtgraph as pg
from PyQt5.QtGui import *
 
 
class Window(QMainWindow):
 
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 600, 500)
        icon = QIcon("skin.png")
        self.setWindowIcon(icon)

        self.xs = np.arange(0, 18.1, 6)
        self.ys = np.arange(0, 18.1, 9)
        self.data = np.array([])

        self.ui()
        self.show()
 
    def ui(self):

        xd, yd = np.arange(10), np.arange(10)

        widget = pg.GraphicsLayoutWidget()
        
        for i, x in enumerate(self.xs):
            for j, y in enumerate(self.ys):
                plot = widget.addPlot(row=y, col=x)
                plot.setTitle(f'{x}, {y}')
                plotline = plot.plot()
                plotline.setData(xd*i, yd*j)

        self.setCentralWidget(widget)
 
App = QApplication(sys.argv)
window = Window()
sys.exit(App.exec())