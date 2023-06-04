import uc480
import pylab as pl
import pylablib as pll
from PIL import Image
pll.par["devices/dlls/thorlabs_tlcam"] = "path/to/dlls"
from pylablib.devices import Thorlabs
cam = Thorlabs.ThorlabsTLCamera()
Thorlabs.list_cameras_tlcam()
cam.set_exposure(1e-3)
image = cam.grab(1)
print(cam.get_data_dimensions())
image.show()

# create instance and connect to library
cam = uc480.uc480()

# connect to first available camera
cam.connect()
cam.get_hw_master_gain_factor()

# take a single image
img = cam.acquire()

# clean up
cam.disconnect()

pl.imshow(img, cmap='gray')
pl.colorbar()
pl.show()