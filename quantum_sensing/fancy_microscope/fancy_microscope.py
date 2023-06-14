
from ScopeFoundry import BaseMicroscopeApp

class FancyMicroscopeApp(BaseMicroscopeApp):

    # this is the name of the microscope that ScopeFoundry uses 
    # when storing data
    name = 'fancy_microscope'
    
    # You must define a setup function that adds all the 
    #capablities of the microscope and sets default settings
    def setup(self):
        
        #Add App wide settings
        
        #Add hardware components
        #print("Adding Hardware Components")
        #from ScopeFoundryHW.virtual_function_gen import VirtualFunctionGenHW
        # from custommeasure import PMD24HW
        #import thorcam_sci.thorcam_sci_hw
        # self.add_hardware(PMD24HW(self))
        #self.add_hardware(VirtualFunctionGenHW(self))

        #self.add_hardware(thorcam_sci.thorcam_sci_hw.ThorcamSCIHW(self))
        # cam not working disconnected?

        #Add measurement components
        print("Create Measurement objects")
        # from custommeasure import LaserQuantumOptimizer
        # self.add_measurement(LaserQuantumOptimizer(self))
        from ESRMeasure import ESRMeasure
        from RabiMeasure import RabiMeasure
        from RabiMappingMeasure import RabiImageMeasure
        from T1Measure import T1Measure

        #import thorcam_sci.thorcam_sci_liveview
        #from thorcam_capture import ThorCamCaptureMeasure
        self.add_measurement(ESRMeasure(self))
        self.add_measurement(RabiMeasure(self))
        self.add_measurement(RabiImageMeasure(self))
        self.add_measurement(T1Measure(self))

        #self.add_measurement(ThorCamCaptureMeasure(self))
        # cam not working disconnected?

        from ESRSweepMeasure import ESRSweepMeasure
        self.add_measurement(ESRSweepMeasure(self))

        #from T1Image import T1ImageMeasure
        from T1MappingMeasure import T1ImageMeasure
        self.add_measurement(T1ImageMeasure(self))

        #from ESRImage import ESRImageMeasure

        from ESRMappingMeasure import ESRImageMeasure
        self.add_measurement(ESRImageMeasure(self))

        from T2SweepMeasure import T2SweepMeasure
        self.add_measurement(T2SweepMeasure(self))

        from T2Measure import T2Measure
        self.add_measurement(T2Measure(self))

        from T2MappingMeasure import T2ImageMeasure
        self.add_measurement(T2ImageMeasure(self))

        #self.add_measurement(thorcam_sci.thorcam_sci_liveview.ThorcamSCILiveView(self))
        # Connect to custom gui
        
        # load side panel UI
        
        # show ui
        self.ui.show()
        self.ui.activateWindow()


if __name__ == '__main__':
    import sys
    
    app = FancyMicroscopeApp(sys.argv)
    sys.exit(app.exec_())