from ScopeFoundry import Measurement, HardwareComponent
import numpy as np
import pyqtgraph as pg
import time
from datetime import datetime
import pandas as pd
import copy
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
from ScopeFoundry import h5_io
import queue


try:
    # if on Windows, use the provided setup script to add the DLLs folder to the PATH
    from windows_setup import configure_path
    configure_path()
except ImportError:
    configure_path = None

class ThorcamSCILiveView(Measurement):
    name = 'thorcam_sci_live'

    def setup(self):
        self.ui_filename = sibling_path(__file__,"thorcam_capture.ui")
        self.ui = load_qt_ui_file(self.ui_filename)
        self.ui.setWindowTitle(self.name)
        self.add_operation('Snap', self.snap)
        pass

    def setup_figure(self):
        # create a GraphLayoutWidget -- contains PlotItems, Plotitems contain ImageItems, or PlotLines 
        # pyqtgraph PlotItem with an ImageItem
        #self.ui = #some qt object
        pass

    def run(self):
        self._image_queue = queue.Queue(maxsize=2)

        self._camera = self.app.hardware['thor_cam'].camera

        self._camera.frames_per_trigger_zero_for_unlimited = 0
        self._camera.arm(2)
        self._camera.issue_software_trigger()
        while not self.interrupt_measurement_called:
            try:
                frame = self._camera.get_pending_frame_or_null()
                if frame is not None:
                    if self._is_color:
                        pil_image = self._get_color_image(frame)
                    else:
                        pil_image = self._get_image(frame)
                    self._image_queue.put_nowait(pil_image)
            except queue.Full:
                # No point in keeping this image around when the queue is full, let's skip to the next one
                pass
            except Exception as error:
                print("Encountered error: {error}, image acquisition will stop.".format(error=error))
                break
        print("Image acquisition has stopped")
        if self._is_color:
            self._mono_to_color_processor.dispose()
            self._mono_to_color_sdk.dispose()


    def update_display(self):
        try:
            image = self.image_queue.get_nowait()

            # self.image_item.setImage(newImage)

            self._image = ImageTk.PhotoImage(master=self, image=image)
            if (self._image.width() != self._image_width) or (self._image.height() != self._image_height):
                # resize the canvas to match the new image size
                self._image_width = self._image.width()
                self._image_height = self._image.height()
                self.config(width=self._image_width, height=self._image_height)
            self.create_image(0, 0, image=self._image, anchor='nw')
        except queue.Empty:
            pass

    def snap(self):
        pass