import serial
import time
COM_port = 'COM4'

def setValue(Flag = 'VOLT', Value=''):
	with serial.Serial(COM_port, 9600, timeout=1) as ser:
		if Flag == 'VOLT':
			val = float(Value)*10
			command = Flag + "%03d\r"%val  
		else:
			command = Flag+str(Value)+'\r'
		ser.write(command.encode())
		return str(ser.readline())

def read_current_and_voltage():
	raw_value = setValue('GETD')
	voltage = str(raw_value[2:4] + '.' + str(raw_value[4:6]))
	current = str(raw_value[6:8] + '.' + str(raw_value[8:10]))
	return [voltage, current]

#print(setValue('VOLT', '0.8')) # change to proper number 
#print(read_current_and_voltage())
