from ScopeFoundry import Measurement
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
from ScopeFoundry import h5_io
import pyqtgraph as pg

import scipy.ndimage as sp_image
import time
#from imageio import imwrite
#from libtiff import TIFF
#import tifffile as tiff
#import PIL.Image
import numpy as np
import os
import sys
sys.path.append('../')
from movestages import *

from thorlabs_tsi_sdk.tl_camera import TLCamera, Frame
from thorlabs_tsi_sdk.tl_camera_enums import SENSOR_TYPE
from thorlabs_tsi_sdk.tl_mono_to_color_processor import MonoToColorProcessorSDK

try:
    #  For python 2.7 tkinter is named Tkinter
    import Tkinter as tk
except ImportError:
    import tkinter as tk
from PIL import Image, ImageTk
#import typing
import threading
try:
    #  For Python 2.7 queue is named Queue
    import Queue as queue
except ImportError:
    import queue

""" LiveViewCanvas

This is a Tkinter Canvas object that can be reused in custom programs. The Canvas expects a parent Tkinter object and 
an image queue. The image queue is a queue.Queue that it will pull images from, and is expected to hold PIL Image 
objects that will be displayed to the canvas. It automatically adjusts its size based on the incoming image dimensions.

"""


class LiveViewCanvas(tk.Canvas):

    def __init__(self, parent, image_queue):
        # type: (typing.Any, queue.Queue) -> LiveViewCanvas
        self.image_queue = image_queue
        self._image_width = 0
        self._image_height = 0
        tk.Canvas.__init__(self, parent)
        self.pack()
        self._get_image()

    def _get_image(self):
        try:
            image = self.image_queue.get_nowait()
            self._image = ImageTk.PhotoImage(master=self, image=image)
            if (self._image.width() != self._image_width) or (self._image.height() != self._image_height):
                # resize the canvas to match the new image size
                self._image_width = self._image.width()
                self._image_height = self._image.height()
                self.config(width=self._image_width, height=self._image_height)
            self.create_image(0, 0, image=self._image, anchor='nw')
        except queue.Empty:
            pass
        self.after(10, self._get_image)


""" ImageAcquisitionThread

This class derives from threading.Thread and is given a TLCamera instance during initialization. When started, the 
thread continuously acquires frames from the camera and converts them to PIL Image objects. These are placed in a 
queue.Queue object that can be retrieved using get_output_queue(). The thread doesn't do any arming or triggering, 
so users will still need to setup and control the camera from a different thread. Be sure to call stop() when it is 
time for the thread to stop.

"""


class ImageAcquisitionThread(threading.Thread):

    def __init__(self, camera):
        # type: (TLCamera) -> ImageAcquisitionThread
        super(ImageAcquisitionThread, self).__init__()
        self._camera = camera
        self._previous_timestamp = 0

        # setup color processing if necessary
        if self._camera.camera_sensor_type != SENSOR_TYPE.BAYER:
            # Sensor type is not compatible with the color processing library
            self._is_color = False
        else:
            self._mono_to_color_sdk = MonoToColorProcessorSDK()
            self._image_width = self._camera.image_width_pixels
            self._image_height = self._camera.image_height_pixels
            self._mono_to_color_processor = self._mono_to_color_sdk.create_mono_to_color_processor(
                SENSOR_TYPE.BAYER,
                self._camera.color_filter_array_phase,
                self._camera.get_color_correction_matrix(),
                self._camera.get_default_white_balance_matrix(),
                self._camera.bit_depth
            )
            self._is_color = True

        self._bit_depth = camera.bit_depth
        self._camera.image_poll_timeout_ms = 0  # Do not want to block for long periods of time
        self._image_queue = queue.Queue(maxsize=2)
        self._stop_event = threading.Event()

    def get_output_queue(self):
        # type: (type(None)) -> queue.Queue
        return self._image_queue

    def stop(self):
        self._stop_event.set()

    def _get_color_image(self, frame):
        # type: (Frame) -> Image
        # verify the image size
        width = frame.image_buffer.shape[1]
        height = frame.image_buffer.shape[0]
        if (width != self._image_width) or (height != self._image_height):
            self._image_width = width
            self._image_height = height
            print("Image dimension change detected, image acquisition thread was updated")
        # color the image. transform_to_24 will scale to 8 bits per channel
        color_image_data = self._mono_to_color_processor.transform_to_24(frame.image_buffer,
                                                                         self._image_width,
                                                                         self._image_height)
        color_image_data = color_image_data.reshape(self._image_height, self._image_width, 3)
        # return PIL Image object
        return Image.fromarray(color_image_data, mode='RGB')

    def _get_image(self, frame):
        # type: (Frame) -> Image
        # no coloring, just scale down image to 8 bpp and place into PIL Image object
        scaled_image = frame.image_buffer >> (self._bit_depth - 8)
        return Image.fromarray(scaled_image)

    def run(self):
        while not self._stop_event.is_set():
            try:
                frame = self._camera.get_pending_frame_or_null()
                if frame is not None:
                    if self._is_color:
                        pil_image = self._get_color_image(frame).rotate(90)
                    else:
                        pil_image = self._get_image(frame).rotate(90)
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
            pass


class ThorCamCaptureMeasure(Measurement):
    
    name = 'Camera'
    
    def setup(self):
        
        S = self.settings
        #S.New('bg_subtract', dtype=bool, initial=False, ro=False)
        #S.New('acquire_bg',  dtype=bool, initial=False, ro=False)
        S.New('continuous', dtype=bool, initial=True, ro=False)
        S.New('save_png', dtype=bool, initial=False, ro=False)
        S.New('save_tif', dtype=bool, initial=True, ro=False)
        S.New('save_ini', dtype=bool, initial=True, ro=False)
        S.New('save_h5', dtype=bool, initial=False, ro=False)
        S.New('camera_select', dtype=int, initial=0, ro=False)
        S.New('gain', dtype=int, initial=1, vmin=0, vmax=3)
        S.New('exposure', dtype=float, unit='s', si=True, initial=0.2)
        
        S.New('r_mod',dtype=float, initial=1.0, ro=False)
        S.New('g_mod',dtype=float, initial=1.0, ro=False)
        S.New('b_mod',dtype=float, initial=1.0, ro=False)

        S.New('x_pos', dtype=float, initial=9.0, vmin=0.0, vmax=18.0)
        S.New('y_pos', dtype=float, initial=9.0, vmin=0.0, vmax=18.0)
        S.New('r_pos', dtype=float, initial=0)
        
        self.ui_filename = sibling_path(__file__,"thorcam_capture.ui")
        self.ui = load_qt_ui_file(self.ui_filename)
        self.ui.setWindowTitle(self.name)
        
        # Event connections
        #S.progress.connect_bidir_to_widget(self.ui.progressBar)
        self.ui.start_pushButton.clicked.connect(self.start)
        self.ui.interrupt_pushButton.clicked.connect(self.interrupt)
        self.ui.autowb_pushButton.clicked.connect(self.auto_white_balance)
        self.ui.save_pushButton.clicked.connect(self.save_image)
        self.ui.move_pushButton.clicked.connect(self.execute_move)
        S.continuous.connect_to_widget(self.ui.continuous_checkBox)
        S.save_png.connect_to_widget(self.ui.save_png_checkBox)
        S.save_tif.connect_to_widget(self.ui.save_tif_checkBox)
        S.save_ini.connect_to_widget(self.ui.save_ini_checkBox)
        S.save_h5.connect_to_widget( self.ui.save_h5_checkBox )
        S.exposure.connect_to_widget(self.ui.exp_time_doubleSpinBox)
        S.gain.connect_to_widget(self.ui.gain_doubleSpinBox)
        
        S.New('img_max', dtype=float, initial=100.0, ro=False)
        S.New('img_min', dtype=float, initial=0, ro=False)
        S.img_max.connect_to_widget(self.ui.max_doubleSpinBox)
        S.img_min.connect_to_widget(self.ui.min_doubleSpinBox)

        S.x_pos.connect_to_widget(self.ui.movex_doubleSpinBox)
        S.y_pos.connect_to_widget(self.ui.movey_doubleSpinBox)
        S.r_pos.connect_to_widget(self.ui.mover_doubleSpinBox)
        self.pos_buffer = {'x': None, 'y': None, 'r': None}
        self.execute_move()
        
        cam_ui_connections = [
            ('exposure', 'exp_time_doubleSpinBox'),
            ('gain', 'gain_doubleSpinBox')]#,
            #('pixel_clock', 'pixel_clock_doubleSpinBox')]
        
        self.cam_hw = self.app.hardware['thor_cam']

        # setup color processing if necessary
        self._camera = self.cam_hw.cam
        # print(self.cam_hw)

        # if self._camera.camera_sensor_type != SENSOR_TYPE.BAYER:
        #     # Sensor type is not compatible with the color processing library
        #     self._is_color = False
        # else:
        #     self._mono_to_color_sdk = MonoToColorProcessorSDK()
        #     self._image_width = self._camera.image_width_pixels
        #     self._image_height = self._camera.image_height_pixels
        #     self._mono_to_color_processor = self._mono_to_color_sdk.create_mono_to_color_processor(
        #         SENSOR_TYPE.BAYER,
        #         self._camera.color_filter_array_phase,
        #         self._camera.get_color_correction_matrix(),
        #         self._camera.get_default_white_balance_matrix(),
        #         self._camera.bit_depth
        #     )
        #     self._is_color = True
        self._is_color = False   
     
        for lq_name, widget_name in cam_ui_connections:                          
            self.cam_hw.settings.get_lq(lq_name).connect_to_widget(getattr(self.ui, widget_name))

        self.imview = pg.ImageView(view=pg.PlotItem())

        def switch_camera_view():
            self.ui.plot_groupBox.layout().addWidget(self.imview)
            self.imview.showMaximized()

        self.ui.show_pushButton.clicked.connect(switch_camera_view)

        
    def run(self):
        S = self.settings
        camera = self.cam_hw.cam

        # print(camera.gain_range)

        # create generic Tk App with just a LiveViewCanvas widget
        print("Generating app...")
        #root = tk.Tk()
        #root.title(camera.name)
        image_acquisition_thread = ImageAcquisitionThread(camera)
        # camera_widget = LiveViewCanvas(parent=root, image_queue=image_acquisition_thread.get_output_queue())

        print("Setting camera parameters...")
        camera.frames_per_trigger_zero_for_unlimited = 0
        camera.arm(2)
        camera.issue_software_trigger()

        self.cam_hw.set_exposure(S['exposure'])
        self.cam_hw.set_gain(S['gain'])

        print("Starting image acquisition thread...")
        image_acquisition_thread.start()

        # print("App starting")
        # root.mainloop()


        # print(self.name, 'interrupted', self.interrupt_measurement_called)
        # print(self._camera)
        # self._camera.frames_per_trigger_zero_for_unlimited = 0
        # self._camera.arm(2)
        # self._camera.issue_software_trigger()

        while not self.interrupt_measurement_called:
            try:
                self.cam_hw.set_exposure(S['exposure'])
                # camera.exposure_time_us = int(1e6*S['exposure'])
                self.cam_hw.set_gain(S['gain'])
                # camera.gain = S['gain']
                self.img = image_acquisition_thread.get_output_queue().get_nowait()
                print(self.img.size)
            except queue.Empty:
                pass
            else:
                pass
                print("Updated Image")

        # while not self.interrupt_measurement_called:
        #     #bgraimg = self.cam_hw.cam.acquire() # self.img is in BGRA order
        #     try:
        #         frame = camera.get_pending_frame_or_null()
        #         if frame is not None:
        #             if self._is_color:
        #                 pil_image = self._get_color_image(frame)
        #             else:
        #                pil_image = self._get_image(frame)
        #             self._image_queue.put_nowait(pil_image)
        #             bgraimg = frame.image_buffer >> (self._bit_depth - 8)
        #             print("bgra img:", bgraimg.shape, bgraimg.shape[0:2])
            
        #             if len(bgraimg.shape) > 2:                
        #                 b = bgraimg[:,:,0]
        #                 g = bgraimg[:,:,1]
        #                 r = bgraimg[:,:,2]
        #             else:
        #                 b = g = r = bgraimg
        #             Ny, Nx = bgraimg.shape[0:2]
        #             rgbaimg = np.ones((Ny,Nx,4), dtype=np.uint8)
        #             # apply WB modifiers, normalized to green 
        #             rgbaimg[:,:,0] = S.r_mod.val*r  
        #             rgbaimg[:,:,1] = S.g_mod.val*g
        #             rgbaimg[:,:,2] = S.b_mod.val*b
        #             rgbaimg[:,:,3] = 255*rgbaimg[:,:,3] # alpha = 255 is opaque, 0 is transparent. cam_hw returns 0s
        #             self.img = rgbaimg
        #             if not S['continuous']:
        #             # save image
        #                 try:
        #                     self.save_image(self)
        #                 finally:
        #                     break # end the while loop for non-continuous scans
        #             else:
        #                 pass
        #                 # restart acq
        #                 #ccd.start_acquisition()
        #     except Exception:
        #         # No point in keeping this image around when the queue is full, let's skip to the next one
        #         continue
        
        print("Waiting for image acquisition thread to finish...")
        image_acquisition_thread.stop()
        image_acquisition_thread.join()

        print("Closing resources...")
        camera.disarm()
        print("App terminated. Goodbye!")
        
    
    def setup_figure(self):
        #self.clear_qt_attr('graph_layout')
        #self.graph_layout=pg.GraphicsLayoutWidget(border=(100,100,100))
        #self.ui.plot_groupBox.layout().addWidget(self.graph_layout)        
        self.ui.plot_groupBox.layout().addWidget(self.imview)
        
    
    def update_display(self):
        if hasattr(self, "img"):
            #self.imview.setImage(self.img, axes={'y':0, 'x':1, 'c':2}, autoRange=False, levels=(self.settings.img_min.value,self.settings.img_max.value))
            #self.imview.setImage(self.img, axes={'y':0, 'x':1, 'c':2}, levels=(0.0, np.max([r.max(), g.max(), b.max()])))
            #self.img.resize()
            #image = np.asarray(self.img)
            image = np.array(self.img.getdata()).reshape(self.img.height, self.img.width)
            #sp_image.zoom(image, 3)
            #self.imview.setImage(image, axes={'y':0, 'x':1, 'c':2}, autoLevels=True)
            #######self.imview.setImage(image, axes={'y':0, 'x':1}, autoLevels=True)
            #saturation = image[:,:,:3].max() / 255.0
            #self.imview.view.setTitle('{:2.0f}% max saturation'.format(saturation*100.0))
            #self.imview.setImage(image[:,:,:3], axes={'y':0, 'x':1, 'c':2}, autoLevels=True)
            self.imview.setImage(image, autoRange=False, levels=(self.settings.img_min.value,self.settings.img_max.value))
    
    def auto_white_balance(self):
        #bgraimg = self.cam_hw.cam.acquire() # self.img is in BGRA order
        bgraimg = self.img
        S = self.settings
        print('thor_cam_capture auto_white_balance')
        
        b = bgraimg[:,:,0]
        g = bgraimg[:,:,1]
        r = bgraimg[:,:,2]
        b_mean = b.mean()
        g_mean = g.mean()
        r_mean = r.mean()
        print("avg values: r = {:0.1f}, g = {:0.1f}, b = {:0.1f}".format(r_mean, g_mean, b_mean) )
        
        g_mod = (b_mean+g_mean+r_mean)/g_mean
        r_mod = (b_mean+g_mean+r_mean)/r_mean
        b_mod = (b_mean+g_mean+r_mean)/b_mean
        
        min_mod = np.min([r_mod, g_mod, b_mod])
        
        r_mod = r_mod/min_mod
        g_mod = g_mod/min_mod
        b_mod = b_mod/min_mod
        
        print("mods: r = {:0.2f}, g = {:0.2f}, b = {:0.2f}".format(r_mod, g_mod, b_mod) )
       
        S.g_mod.update_value(new_val=g_mod)
        S.r_mod.update_value(new_val=r_mod)
        S.b_mod.update_value(new_val=b_mod)
        
    def save_image(self):
        print('thor_cam_capture save_image')
        S = self.settings
        t0 = time.time()
        fname = os.path.join(self.app.settings['save_dir'], "%i_%s" % (t0, self.name))
        
        if S['save_ini']:
            self.app.settings_save_ini(fname + ".ini")
        if S['save_png']:
            self.imview.export(fname + ".png")
        if S['save_tif']:
            self.imview.export(fname + ".tif")
        if S['save_h5']:
            with h5_io.h5_base_file(app=self.app, measurement=self) as H:
                M = h5_io.h5_create_measurement_group(measurement=self, h5group=H)
                M.create_dataset('img', data=self.img, compression='gzip')

    def _get_color_image(self, frame):
        # type: (Frame) -> Image
        # verify the image size
        # width = frame.image_buffer.shape[1]
        # height = frame.image_buffer.shape[0]
        # if (width != self._image_width) or (height != self._image_height):
        #     self._image_width = width
        #     self._image_height = height
        #     print("Image dimension change detected, image acquisition thread was updated")
        # color the image. transform_to_24 will scale to 8 bits per channel
        color_image_data = self._mono_to_color_processor.transform_to_24(frame.image_buffer,
                                                                         self._image_width,
                                                                         self._image_height)
        color_image_data = color_image_data.reshape(self._image_height, self._image_width, 3)
        # return PIL Image object
        return Image.fromarray(color_image_data, mode='RGB')

    def _get_image(self, frame):
        # type: (Frame) -> Image
        # no coloring, just scale down image to 8 bpp and place into PIL Image object
        scaled_image = frame.image_buffer >> (self._bit_depth - 8)
        return Image.fromarray(scaled_image)
    
    def execute_move(self):
        x, y, r = self.settings.x_pos.val, self.settings.y_pos.val, self.settings.r_pos.val

        devices, moved = [], []
        x_diff, y_diff, r_diff = self.pos_buffer['x'] is not None and x != self.pos_buffer['x'], \
                                 self.pos_buffer['y'] is not None and y != self.pos_buffer['y'], \
                                 self.pos_buffer['r'] is not None and r != self.pos_buffer['r']

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
            self.pos_buffer['R'] = r
            moved.append('r')
        
        for device in devices:
            closeDevice(device)

        print("Stages Moved")
        print(f"Axes moved: {moved}")