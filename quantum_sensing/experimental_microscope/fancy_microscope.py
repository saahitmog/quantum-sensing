
from ScopeFoundry import BaseMicroscopeApp
from utils import *
import os, sys 

class FancyMicroscopeApp(BaseMicroscopeApp):

    name = 'fancy_microscope'
    
    def LOG(self, msg): self.logging_widget_handler.emit(makelog('APP', msg))

    def setup(self):
        

        self.LOG("Adding Hardware Components")
        #from thorcam_sci.thorcam_sci_hw import ThorcamSCIHW as camHW
        from stageHW import stageHW
        with hide():
            #self.add_hardware(camHW(self))
            self.add_hardware(stageHW(self))

        self.LOG("Create Measurement objects")
        # from custommeasure import LaserQuantumOptimizer
        # self.add_measurement(LaserQuantumOptimizer(self))

        from ESR import ESRMeasure
        self.add_measurement(ESRMeasure(self))

        from RABI import RabiMeasure
        self.add_measurement(RabiMeasure(self))

        from utils import Utility
        self.add_measurement(Utility(self))

        #from RabiMeasure import RabiMeasure
        #from RabiMappingMeasure import RabiImageMeasure
        #from T1Measure import T1Measure

        #from thorcam_capture import ThorCamCaptureMeasure
        
        #self.add_measurement(RabiImageMeasure(self))
        #self.add_measurement(T1Measure(self))

        #self.add_measurement(ThorCamCaptureMeasure(self))
        # cam not working disconnected?

        #from T1Image import T1ImageMeasure
        #from T1MappingMeasure import T1ImageMeasure
        #self.add_measurement(T1ImageMeasure(self))


        #from ESRMappingMeasure import ESRImageMeasure
        #self.add_measurement(ESRImageMeasure(self))

        '''from T2SweepMeasure import T2SweepMeasure
        self.add_measurement(T2SweepMeasure(self))

        from T2Measure import T2Measure
        self.add_measurement(T2Measure(self))

        from T2MappingMeasure import T2ImageMeasure
        self.add_measurement(T2ImageMeasure(self))'''

        #self.add_measurement(thorcam_sci.thorcam_sci_liveview.ThorcamSCILiveView(self))
 
        self.ui.show()
        self.ui.activateWindow()

        try: self.settings_load_ini('.config.ini')
        except Exception: pass

if __name__ == '__main__':
    app = FancyMicroscopeApp(sys.argv)
    sys.exit(app.exec_())