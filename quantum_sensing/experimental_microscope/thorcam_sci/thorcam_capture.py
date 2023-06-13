from ScopeFoundry import Measurement
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
from ScopeFoundry import h5_io
import pyqtgraph as pg
#import scipy.misc 
import time
#from imageio import imwrite
#from libtiff import TIFF
#import tifffile as tiff
#import PIL.Image
import numpy as np
#from .tiffile import imsave as tif_imsave
import os

class ThorCamCaptureMeasure(Measurement):
    
    name = 'thor_cam_capture'
    
    def setup(self):
        
        S = self.settings
        #S.New('bg_subtract', dtype=bool, initial=False, ro=False)
        #S.New('acquire_bg',  dtype=bool, initial=False, ro=False)
        S.New('continuous', dtype=bool, initial=True, ro=False)
        S.New('save_png', dtype=bool, initial=False, ro=False)
        S.New('save_tif', dtype=bool, initial=True, ro=False)
        S.New('save_ini', dtype=bool, initial=True, ro=False)
        S.New('save_h5', dtype=bool, initial=False, ro=False)
        
        S.New('r_mod',dtype=float, initial=1.0, ro=False)
        S.New('g_mod',dtype=float, initial=1.0, ro=False)
        S.New('b_mod',dtype=float, initial=1.0, ro=False)
                
        self.ui_filename = sibling_path(__file__,"thorcam_capture.ui")
        self.ui = load_qt_ui_file(self.ui_filename)
        self.ui.setWindowTitle(self.name)
        
        # Event connections
        S.progress.connect_bidir_to_widget(self.ui.progressBar)
        self.ui.start_pushButton.clicked.connect(self.start)
        self.ui.interrupt_pushButton.clicked.connect(self.interrupt)
        self.ui.autowb_pushButton.clicked.connect(self.auto_white_balance)
        self.ui.save_pushButton.clicked.connect(self.save_image)
        S.continuous.connect_to_widget(self.ui.continuous_checkBox)
        S.save_png.connect_to_widget(self.ui.save_png_checkBox)
        S.save_tif.connect_to_widget(self.ui.save_tif_checkBox)
        S.save_ini.connect_to_widget(self.ui.save_ini_checkBox)
        S.save_h5.connect_to_widget( self.ui.save_h5_checkBox )
        
        S.New('img_max', dtype=float, initial=30.0, ro=False)
        S.New('img_min', dtype=float, initial=-20.0, ro=False)
        S.img_max.connect_to_widget(self.ui.max_doubleSpinBox)
        S.img_min.connect_to_widget(self.ui.min_doubleSpinBox)
        
        cam_ui_connections = [
            ('exposure', 'exp_time_doubleSpinBox'),
            ('gain', 'gain_doubleSpinBox')]#,
            #('pixel_clock', 'pixel_clock_doubleSpinBox')]
        
        self.cam_hw = self.app.hardware.thor_cam
        
        for lq_name, widget_name in cam_ui_connections:                          
            self.cam_hw.settings.get_lq(lq_name).connect_to_widget(getattr(self.ui, widget_name))

        self.imview = pg.ImageView(view=pg.PlotItem())
        
        def switch_camera_view():
            self.ui.plot_groupBox.layout().addWidget(self.imview)
            self.imview.showMaximized() 
        self.ui.show_pushButton.clicked.connect(switch_camera_view)
        
    def run(self):
        print(self.name, 'interrupted', self.interrupt_measurement_called)
        
        while not self.interrupt_measurement_called:
            
            bgraimg = self.cam_hw.cam.acquire() # self.img is in BGRA order
#             print("bgra img:", bgraimg.shape, bgraimg.shape[0:2])
            S = self.settings
            
            if len(bgraimg.shape) > 2:                
                b = bgraimg[:,:,0]
                g = bgraimg[:,:,1]
                r = bgraimg[:,:,2]
            else:
                b = g = r = bgraimg
            
            
            Ny, Nx = bgraimg.shape[0:2]
            rgbaimg = np.ones((Ny,Nx,4), dtype=np.uint8)
            # apply WB modifiers, normalized to green 
            rgbaimg[:,:,0] = S.r_mod.val*r  
            rgbaimg[:,:,1] = S.g_mod.val*g
            rgbaimg[:,:,2] = S.b_mod.val*b
            rgbaimg[:,:,3] = 255*rgbaimg[:,:,3] # alpha = 255 is opaque, 0 is transparent. cam_hw returns 0s
            self.img = rgbaimg
            
            if not S['continuous']:
                # save image
                try:
                    self.save_image(self)
                finally:
                    break # end the while loop for non-continuous scans
            else:
                pass
                # restart acq
                #ccd.start_acquisition()
        
    
    def setup_figure(self):
        #self.clear_qt_attr('graph_layout')
        #self.graph_layout=pg.GraphicsLayoutWidget(border=(100,100,100))
        #self.ui.plot_groupBox.layout().addWidget(self.graph_layout)

        
        self.ui.plot_groupBox.layout().addWidget(self.imview)
        
    
    def update_display(self):
        if hasattr(self, "img"):
            #self.imview.setImage(self.img, axes={'y':0, 'x':1, 'c':2}, autoRange=False, levels=(self.settings.img_min.value,self.settings.img_max.value))
            #self.imview.setImage(self.img, axes={'y':0, 'x':1, 'c':2}, levels=(0.0, np.max([r.max(), g.max(), b.max()])))
            saturation = self.img[:,:,:3].max() / 255.0
            self.imview.view.setTitle('{:2.0f}% max saturation'.format(saturation*100.0))
            self.imview.setImage(self.img[:,:,:3], axes={'y':0, 'x':1, 'c':2}, autoLevels=True)
    
    def auto_white_balance(self):
        bgraimg = self.cam_hw.cam.acquire() # self.img is in BGRA order
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