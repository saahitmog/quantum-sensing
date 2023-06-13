from ScopeFoundry import HardwareComponent
from uc480 import uc480

class ThorCamHW(HardwareComponent):
    
    name = 'thor_cam'
    
    def setup(self):
        
        self.settings.New('exp_time', dtype=float, initial=50.0, unit='ms')
        self.settings.New('gain', dtype=int, initial=100, vmin=0, vmax=100)
        self.settings.New('pixel_clock', dtype=int, initial=10, unit='MHz')
        
    def connect(self):
        
        # create instance and connect to library
        self.cam = uc480()
        
        # connect to first available camera
        self.cam.connect()
        
        self.settings.exp_time.connect_to_hardware(
            read_func = self.cam.get_exposure,
            write_func = self.cam.set_exposure
            )
        
        _min, _max, _inc =self.cam.get_exposure_limits()
        self.settings.exp_time.change_min_max(_min, _max)
        
        self.settings.gain.connect_to_hardware(
            read_func = self.cam.get_gain,
            write_func = self.cam.set_gain,
            )
        
        self.settings.pixel_clock.connect_to_hardware(
            read_func = self.cam.get_pixelclock,
            write_func = self.cam.set_pixelclock
            )
        
        _min, _max, _inc =self.cam.get_pixelclock_range()
        self.settings.pixel_clock.change_min_max(_min, _max)

        self.settings.pixel_clock.add_listener(self.on_pixel_clock_update)

        self.read_from_hardware()
        
    def disconnect(self):
        
        if hasattr(self, 'cam'):
            self.cam.disconnect()
            del self.cam
            
    def on_pixel_clock_update(self):
        _min, _max, _inc = self.cam.get_exposure_limits()
        self.settings.exp_time.change_min_max(_min, _max)