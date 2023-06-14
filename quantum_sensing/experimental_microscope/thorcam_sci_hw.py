from ScopeFoundry import HardwareComponent
import os
import sys


def configure_path():
    is_64bits = sys.maxsize > 2**32
    relative_path_to_dlls = '..' + os.sep + 'dlls' + os.sep

    if is_64bits:
        relative_path_to_dlls += '64_lib'
    else:
        relative_path_to_dlls += '32_lib'

    absolute_path_to_file_directory = os.path.dirname(os.path.abspath(__file__))

    absolute_path_to_dlls = os.path.abspath(absolute_path_to_file_directory + os.sep + relative_path_to_dlls)

    os.environ['PATH'] = absolute_path_to_dlls + os.pathsep + os.environ['PATH']

    try:
        # Python 3.8 introduces a new method to specify dll directory
        os.add_dll_directory(absolute_path_to_dlls)
    except AttributeError:
        pass

class ThorcamSCIHW(HardwareComponent):

    name ='thor_cam'

    def setup(self):
        try:
            configure_path()
        except ImportError:
            pass
        #self.settings.New('exp_time', dtype=float, initial=50.0, unit='ms')
        # self.settings.New('gain', dtype=int, initial=100, vmin=0, vmax=100)
        self.settings.New('gain', dtype=int, initial=1, vmin=0, vmax=3) #changed by Nishanth Anand 11/4/22 to fit gain range of CS135MUN camera
        #self.settings.New('pixel_clock', dtype=int, initial=10, unit='MHz')
        self.settings.New('exposure', dtype=float, unit='s', si=True, initial=0.5)

        # self.cam = self.connect()

    def connect(self):
        try:
            configure_path()
        except ImportError:
            pass
        from thorlabs_tsi_sdk.tl_camera import TLCameraSDK, OPERATION_MODE

        self.sdk = TLCameraSDK()
        available_cameras = self.sdk.discover_available_cameras()
        if len(available_cameras) < 1:
            print("no cameras detected")
            raise IOError("no cameras detected")
        self.cam = c = self.sdk.open_camera(available_cameras[0])

        c.exposure_time_us = 500_000  # set exposure to 500 ms
        c.frames_per_trigger_zero_for_unlimited = 0  # start camera in continuous mode
        c.image_poll_timeout_ms = 1000  # 1 second polling timeout

        return c

    def set_exposure(self, t):
        # t is in seconds
        self.cam.exposure_time_us = int(t*1e6)
        self.settings['exposure'] = t

    def set_gain(self, g):
        self.cam.gain = int(g)
        self.settings['gain'] = g

    def disconnect(self):
        if hasattr(self, 'camera'):
            self.cam.disarm()

        if hasattr(self, 'sdk'):
            self.cam.disarm()
            self.cam.dispose()
            self.sdk.dispose()