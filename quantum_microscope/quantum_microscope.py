
from ScopeFoundry import BaseMicroscopeApp

class QuantumMicroscopeApp(BaseMicroscopeApp):

    # this is the name of the microscope that ScopeFoundry uses 
    # when storing data
    name = 'quantum_microscope'
    
    # You must define a setup function that adds all the 
    #capablities of the microscope and sets default settings
    def setup(self):
        
        #Add App wide settings
        
        #Add hardware components
        print("Adding Hardware Components")
        #from ScopeFoundryHW.virtual_function_gen import VirtualFunctionGenHW
        # from custommeasure import PMD24HW
        import thorcam_sci.thorcam_sci_hw
        # self.add_hardware(PMD24HW(self))
        #self.add_hardware(VirtualFunctionGenHW(self))
        self.add_hardware(thorcam_sci.thorcam_sci_hw.ThorcamSCIHW(self))
        #Add measurement components
        print("Create Measurement objects")
        # from custommeasure import LaserQuantumOptimizer
        # self.add_measurement(LaserQuantumOptimizer(self))
        from ESRMeasure import ESRMeasure
        from RabiMeasure import RabiMeasure
        #import thorcam_sci.thorcam_sci_liveview
        from thorcam_capture import ThorCamCaptureMeasure
        self.add_measurement(ESRMeasure(self))
        self.add_measurement(RabiMeasure(self))
        self.add_measurement(ThorCamCaptureMeasure(self))
        #self.add_measurement(thorcam_sci.thorcam_sci_liveview.ThorcamSCILiveView(self))
        # Connect to custom gui
        
        # load side panel UI
        
        # show ui
        self.ui.show()
        self.ui.activateWindow()


if __name__ == '__main__':
    import sys
    
    app = QuantumMicroscopeApp(sys.argv)
    sys.exit(app.exec_())