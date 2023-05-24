'''
Created on Jun 27, 2019

@author: lab
'''

from ScopeFoundry import Measurement
import time
from ir_microscope.measurements.laser_line_writer import LaserLineWriter
from gevent.libev.corecext import self

class ThorCamTimeSeries(Measurement):
    
    name = 'thorcam_time_series'


    def setup(self):
        S = self.settings
        S.New('repetition', int, initial=10)
        S.New('delta_time', float, initial=1, unit='s')


    def run(self):
        S = self.settings
        self.time_series(S['delta_time'], S['repetition'])

    def time_series(self, dt=5, rep=10):
        measure = self.app.measurements['thor_cam_capture']
        hw = self.app.hardware['thor_cam']
        
        MS = measure.settings
        
        hw.settings['connected'] = True
        MS['save_png'] = True
        MS['save_h5'] = True
        MS['continuous'] = True
        MS['activation'] = True        
        time.sleep(1)
        
        for i in range(rep):
            
            if self.interrupt_measurement_called:
                break
            
            self.set_progress((i+1)/rep *100)
            print(self.name, 'saving image', i+1, 'of', rep)
            measure.save_image()

            
            if self.interrupt_measurement_called:
                break
            
            time.sleep(dt)
            
        MS['activation'] = False