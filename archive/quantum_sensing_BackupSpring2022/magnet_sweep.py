import optimized_ESR
import COM_testing as COM
import numpy as np
import sys
def run(config_dic):
	global config
	config = config_dic
	runExperiment()

def runExperiment():
	try:
		name = input("Enter a filename:")
		config['name'] = name
		for i in np.arange(config['magnet_start'], config['magnet_stop'] + config['magnet_step'], config['magnet_step']):
			i = round(i, 1)
			config['magnet_power'] = i
			print('Current Voltage: ' + COM.read_current_and_voltage()[0])
			print('Setting Voltage to: ' + str(i) + ' ' + COM.setValue(Value = str(i)))
			print('Current Voltage: ' + COM.read_current_and_voltage()[0])
			val = optimized_ESR.run(config)
			if val == 'except':
				sys.exit()
	finally:
		sys.exit()