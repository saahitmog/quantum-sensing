from ScopeFoundry import Measurement, HardwareComponent
import numpy as np
import pyqtgraph as pg
import time
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file

class LaserQuantumOptimizer(Measurement):

    name = "laser_quantum_optimizer" 

    def setup(self):
        
        self.states = ['power', 'target_power', 'laser_temperature', 'PSU_temperature']
        for rate in self.states:
            self.settings.New('{}_visible'.format(rate), dtype=bool, initial=True)   
                
        self.settings.New('history_len', dtype=int, initial=300)        
        self.settings.New('avg_len', dtype=int, initial=40)       
        self.settings.New('show_avg_lines', bool, initial=False)
        self.settings.New('show_temperature', bool, initial=False) 

        self.on_new_history_len()
        self.show_temperature()
        self.settings.history_len.add_listener(self.on_new_history_len)
        
        self.hw = self.app.hardware['laser_quantum']
        
    def setup_figure(self):        
        ui_filename = sibling_path(__file__, "laser_quantum_optimizer.ui")
        self.ui = load_qt_ui_file(ui_filename)
        
        self.settings.activation.connect_to_widget(self.ui.run_checkBox)
        self.settings.history_len.connect_to_widget(self.ui.history_len_doubleSpinBox)
        self.settings.avg_len.connect_to_widget(self.ui.avg_len_doubleSpinBox)        
        self.settings.show_temperature.connect_to_widget(self.ui.temperature_visible_checkBox)
        self.settings.show_temperature.add_listener(self.show_temperature)

        HS = self.hw.settings
        HS.connected.connect_to_widget(self.ui.connected_checkBox)    
        HS.target_power.connect_to_widget(self.ui.target_power_doubleSpinBox)
        HS.status.connect_to_widget(self.ui.status_label)      
        self.ui.on_pushButton.clicked.connect(self.hw.toggle_laser_on)
        self.ui.off_pushButton.clicked.connect(self.hw.toggle_laser_off)   
        
        self.graph_layout = pg.GraphicsLayoutWidget()
        self.ui.channel_optimizer_GroupBox.layout().addWidget(self.graph_layout)
        self.plot = self.graph_layout.addPlot(title="Laser optimizer")
        
        self.plotlines = {}
        self.avglines = {}
        colors = ['r', 'g', 'r', 'y']
        for i, rate in enumerate(self.states):
            self.plotlines.update({rate:self.plot.plot(pen=colors[i])})
            avg_line = pg.InfiniteLine(angle=0, movable=False, pen=colors[i % len(colors)])
            self.plot.addItem(avg_line)
            self.avglines.update({rate:avg_line})       

    def run(self):
        hw = self.hw

        while not self.interrupt_measurement_called:
            self.optimize_ii += 1
            self.optimize_ii %= self.settings['history_len']

            self.optimize_history[self.optimize_ii, :] = [hw.settings[state] for state in self.states]
            time.sleep(0.08) 
            
    def on_new_history_len(self):
        N = self.settings['history_len']
        self.optimize_ii = 0
        self.optimize_history = np.ones((N, len(self.states)), dtype=float)
        for i, state in enumerate(self.states):
            return
            self.optimize_history[:, i] *= self.hw.settings[state]
        self.optimize_history_avg = np.zeros_like(self.optimize_history)
    
    def update_display(self):
        if self.optimize_ii == 0:
            return
        
        ii = self.optimize_ii                    
        title = ''
        
        N_AVG = min(self.settings['avg_len'], self.settings['history_len'] - 1)
        q = ii - N_AVG
        if q >= 0:
            avg_val = self.optimize_history[q:ii, :].mean(axis=0)
        else:
            avg_val = self.optimize_history[:ii].mean(axis=0) * 1.0 * ii / N_AVG + self.optimize_history[q:].mean(axis=0) * (-q / N_AVG)
        
        for i, rate in enumerate(self.states):
            self.plotlines[rate].setVisible(self.settings['{}_visible'.format(rate)])
            self.avglines[rate].setVisible(self.settings['{}_visible'.format(rate)] * self.settings['show_avg_lines'])
            if self.settings['{}_visible'.format(rate)]:
                title += '<b>\u03BC</b><sub>{}</sub> = {:3.0f} <br />'.format(rate, avg_val[i])
                self.plotlines[rate].setData(y=self.optimize_history[:, i])
                self.avglines[rate].setPos((0, avg_val[i]))

        self.plot.setTitle(title)
        
    def show_temperature(self):
        for t in ['laser_temperature', 'PSU_temperature']:
            self.settings['{}_visible'.format(t)] = self.settings['show_temperature']
            
        for t in ['power', 'target_power']:
            self.settings['{}_visible'.format(t)] = not self.settings['show_temperature']


class PMD24HW(HardwareComponent):
    
    name = "laser_quantum"
    
    def setup(self):
        print('setup')
        
        self.settings.New('port', str, initial='COM28')
        self.settings.New('power', float, initial=10, unit='mW',
                          spinbox_decimals=1)
        self.settings.New('target_power', float, initial=10.1, unit='mW',
                          spinbox_decimals=1)
        self.settings.New('status', str, initial='?', ro=True)
        self.settings.New('laser_temperature', float, ro=True, unit='C')
        self.settings.New('PSU_temperature', float, ro=True, unit='C')
        self.add_operation('ON', self.toggle_laser_on)
        self.add_operation('OFF', self.toggle_laser_off)

    def connect(self):
        if self.debug_mode.val: print("connecting to", self.name)
        
        S = self.settings
        self.dev = PMD24(port=S['port'], debug=S['debug_mode'])
        
        S.power.connect_to_hardware(self.dev.read_power)
        S.target_power.connect_to_hardware(None, self.dev.write_power)
        
        S.status.connect_to_hardware(self.dev.read_status)
        S.laser_temperature.connect_to_hardware(self.dev.read_laser_temp)
        S.PSU_temperature.connect_to_hardware(self.dev.read_PSU_temp)
        
        import threading
        self.update_thread_interrupted = False
        self.update_thread = threading.Thread(target=self.update_thread_run)        
        self.update_thread.start()

        # print(self.update_thread)
        self.read_from_hardware()

    def disconnect(self):
        if self.debug_mode.val: print("disconnect " + self.name)
        if hasattr(self, 'update_thread'):
            self.update_thread_interrupted = True
            self.update_thread.join(timeout=0.0)
            del self.update_thread
            
        if hasattr(self, 'dev'):
            self.dev.ser.close()            
            del self.dev
                            
    def toggle_laser_on(self):
        self.dev.write_STPOW(self.settings['target_power'])
        self.settings.status.read_from_hardware()
        self.dev.write_on()
        self.settings.status.read_from_hardware()
        
    def toggle_laser_off(self):
        self.settings.status.read_from_hardware()
        self.dev.write_off()
        self.settings.status.read_from_hardware()

    def update_thread_run(self):
        S = self.settings
        while not self.update_thread_interrupted:
            S.status.read_from_hardware()
            S.power.read_from_hardware()
            S.laser_temperature.read_from_hardware()
            S.PSU_temperature.read_from_hardware()
            # print(self.name, 'update_thread_run', S.status.value,
                  # S.power.value,
                  # S.laser_temperature.value,
                  # S.PSU_temperature.value)
            time.sleep(0.1)
