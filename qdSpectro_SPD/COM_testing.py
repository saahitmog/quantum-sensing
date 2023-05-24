import serial
import time
COM_port = 'COM4'

def setValue(Flag, Value=''):
	with serial.Serial(COM_port, 9600, timeout=1) as ser:
		command = Flag+str(Value)+'\r'
		ser.write(command.encode())
		return str(ser.readline())

def read_current_and_voltage():
	raw_value = setValue('GETD')
	voltage = str(raw_value[2:4] + '.' + str(raw_value[4:6]))
	current = str(raw_value[6:8] + '.' + str(raw_value[8:10]))
	return [voltage, current]

print(setValue('CURR', '002'))  ##  CURR for current 001 = 0.1 A && VOLT for voltage "010" = 1.00 V, minimum "008" = 0.80 V,  max = 050 
print(read_current_and_voltage())
