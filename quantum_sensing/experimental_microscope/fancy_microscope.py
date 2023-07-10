
from ScopeFoundry import BaseMicroscopeApp
import os, sys

class FancyMicroscopeApp(BaseMicroscopeApp):

    # this is the name of the microscope that ScopeFoundry uses 
    # when storing data
    name = 'fancy_microscope'
    
    # You must define a setup function that adds all the 
    # capablities of the microscope and sets default settings
    def setup(self):
        
        #Add App wide settings
        
        #Add hardware components
        print("Adding Hardware Components")
        
        from thorcam_sci.thorcam_sci_hw import ThorcamSCIHW as camHW
        from stageHW import stageHW
        with hide():
            #self.add_hardware(camHW(self))
            self.add_hardware(stageHW(self))

        #Add measurement components
        print("Create Measurement objects")
        # from custommeasure import LaserQuantumOptimizer
        # self.add_measurement(LaserQuantumOptimizer(self))

        from ESR import ESRMeasure
        self.add_measurement(ESRMeasure(self))

        #from RabiMeasure import RabiMeasure
        #from RabiMappingMeasure import RabiImageMeasure
        #from T1Measure import T1Measure

        from thorcam_capture import ThorCamCaptureMeasure
        
        #self.add_measurement(RabiMeasure(self))
        #self.add_measurement(RabiImageMeasure(self))
        #self.add_measurement(T1Measure(self))

        #self.add_measurement(ThorCamCaptureMeasure(self))
        # cam not working disconnected?

        #from ESRSweepMeasure import ESRSweepMeasure
        #self.add_measurement(ESRSweepMeasure(self))

        #from T1Image import T1ImageMeasure
        #from T1MappingMeasure import T1ImageMeasure
        #self.add_measurement(T1ImageMeasure(self))

        #from ESRImage import ESRImageMeasure

        from ESRMappingMeasure import ESRImageMeasure
        self.add_measurement(ESRImageMeasure(self))

        '''from T2SweepMeasure import T2SweepMeasure
        self.add_measurement(T2SweepMeasure(self))

        from T2Measure import T2Measure
        self.add_measurement(T2Measure(self))

        from T2MappingMeasure import T2ImageMeasure
        self.add_measurement(T2ImageMeasure(self))'''

        #self.add_measurement(thorcam_sci.thorcam_sci_liveview.ThorcamSCILiveView(self))
        # Connect to custom gui
        
        # load side panel UI
        
        # show ui
        self.ui.show()
        self.ui.activateWindow()

class hide:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout


if __name__ == '__main__':
    import sys
    
    app = FancyMicroscopeApp(sys.argv)
    sys.exit(app.exec_())