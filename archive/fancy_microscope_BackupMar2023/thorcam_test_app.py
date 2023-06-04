'''
Created on Jan 11, 2017

@author: Edward Barnard
'''

from ScopeFoundry.base_app import BaseMicroscopeApp
#from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
import logging

logging.basicConfig(level=logging.INFO)

# Define your App that inherits from BaseMicroscopeApp
class ThorCamTestApp(BaseMicroscopeApp):
    
    # this is the name of the microscope that ScopeFoundry uses 
    # when displaying your app and saving data related to it    
    name = 'thor_cam_test_app'

    # You must define a setup() function that adds all the 
    # capabilities of the microscope and sets default settings    
    def setup(self):

        #Add App wide settings
        #self.settings.New('test1', dtype=int, initial=0)
        
        #Add Hardware components
        from thorcam_sci import thorcam_sci_hw
        self.add_hardware(thorcam_sci_hw.ThorcamSCIHW(self))


        #Add Measurement components
        import thorcam_capture
        self.add_measurement(thorcam_capture.ThorCamCaptureMeasure(self))
        
        # import thorcam_time_series
        # self.add_measurement(thorcam_time_series.ThorCamTimeSeries(self))
        
        
        # load side panel UI        
        #quickbar_ui_filename = sibling_path(__file__, "quickbar.ui")        
        #self.add_quickbar( load_qt_ui_file(quickbar_ui_filename) )
        
        # Connect quickbar ui elements to settings
        # self.quickbar.foo_pushButton.connect(self.on_foo)
        
        # load default settings from file
        #self.settings_load_ini(sibling_path(__file__, "defaults.ini"))
        
if __name__ == '__main__':
    
    import sys
    app = ThorCamTestApp(sys.argv)
    sys.exit(app.exec_())