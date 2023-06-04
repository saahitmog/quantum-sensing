import PBcontrol as PBctl
import sequenceControl as seqCtl
import T1config as T1
from spinapi import *
from ctypes import *
import numpy as np
import sys
import single_photon_stream as DAQ #NOTE THIS CHANGE FROM PHOTODIODE CODE
import SRScontrol as SRSctl
from PBinit import initPB
import time
import copy
import pandas as pd

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style

#Define number of measurements to throw away before starting experiment 
NThrow = 0

def main():
	'''For running experiment normally'''
	global config
	config = {}
	#Constants for PulseBlaster
	config['t_AOM'] = 50000 * ns
	config['sequence_name'] = "ESRseq"

	#Defines the frequency that the SRS will sweep (in GHz)
	config['START_FREQUENCY'] = 2.5
	config['END_FREQUENCY'] = 3.5
	config['N_pts'] = 101

	runExperiment()

def run(config_dic):
	global config
	config = config_dic
	runExperiment()

def runExperiment():
	try:
	 	#start the start time to measure length of program execution
		start = time.process_time()

		config['N_pts'] = int(config['N_pts'])
		config['N_samples'] = int(config['N_samples'])
		#Setup plotting style
		style.use("fivethirtyeight")

		#create figure and subplot, figsize can be changed in the global configuration document
		fig = plt.figure(figsize = (config['figsize_x'], config['figsize_y']))
		ax = fig.add_subplot(111)

		#sweep is a np array of length values that we will sweep across, step_size is the size of steps between
		sweep, step_size = np.linspace(config['start_t'], config['end_t'], num = config['N_pts'], retstep = True)

		#create a dictionary that will save signal and background information and will be exported to pandas df and then to a csv
		save_dict = {}
		save_dict['Length'] = sweep

		#create arrays to hold the average values across averaging runs
		length = config['N_pts']
		total_pts = length * config['Navg']
		average_x = sweep
		average_y = np.zeros(length)

		#create arrays to hold realtime values during an averaging run, xs and ys will be plotted while signal and background are saved
		signal = np.zeros(length)
		background = np.zeros(length)
		xs = sweep
		ys = np.zeros(length)

		#the data array holds new samples that come from a DAQ read since we're using stream readers
		data = np.zeros(config['N_samples'] * 4)

		#plot the data for the first time and get the line variable (which isn't really used)
		line, = ax.plot(xs, ys, 'b-')

		#run the initPB function from the PBinit file 
		initPB()

		#initiate RF generator with channel and model type; set amplitude
		my_SRS = SRSctl.initSRS(27, 'SG386') 
		SRSctl.setSRS_RFAmplitude(my_SRS, .01, units = "Vpp") 

		#set test frequency and modulation; ESR has no modulation but that's handled in the modulation function
		SRSctl.setSRS_Freq(my_SRS, config['MW_FREQ'], 'GHz') 
		SRSctl.setupSRSmodulation(my_SRS, config['sequence_name']) 

		#Get the instruction Array
		instructionArray = []
		for i in sweep:
			sequenceArgs = [i*ns, config['t_AOM'] * ns, config['t_readoutDelay'] * ns, config['t_pi'] * ns]
			instructionArray.extend(PBctl.programPB(config['sequence_name'], sequenceArgs))
		print(instructionArray)


		#Program the PulseBlaster
		status = pb_start_programming(PULSE_PROGRAM)
		for i in range(0, len(instructionArray)):
			PBctl.pb_inst_pbonly(instructionArray[i][0],instructionArray[i][1],instructionArray[i][2],instructionArray[i][3])
		pb_stop_programming()

		#Configure the DAQ
		config['task'], reader = DAQ.configureDAQ(config['N_samples'])

		#turn on the microwave excitation 
		SRSctl.enableSRS_RFOutput(my_SRS)

		#Function to close all running tasks
		def closeExp():
			#turn off the microwave excitation
			SRSctl.disableSRS_RFOutput(my_SRS) 

			#stop the pulse blaster
			pb_stop()

			#Close the DAQ once we are done
			DAQ.closeDAQTask(config['task'])
			return

		#Function to save data 
		def save():
			#check if user wants to save the plot
			saved = input("Save plot? y/n")
			if saved == 'y':
				name = input("Enter a filename:")

				#save the figure
				plt.savefig(name)

				#save the pandas dataframe with background, signal, and frequency
				dataset = pd.DataFrame(save_dict)
				dataset.to_csv(name + '.csv')

				#closeExp()
				#sys.exit()

			elif saved == 'n':
				#closeExp()
				#sys.exit()
				x=0
			else:
				print('Error, try again')
				save()

		#start the pulse blaster with the sequence that was programmed
		pb_start()

		#Throw away the first NThrow samples to get the photon counter warmed up (not really necessary)
		for i in range(NThrow):
			DAQ.readDAQ(reader, config['N_samples'] * 2, config['DAQtimeout'], data)

		#Init function used by FuncAnimation to setup the initial plot; only used if blit = True
		def init():
			line.set_data([], [])
			return line, 

		#Initialize f to be the start frequency, avg_run to be 0, and step to be 0
		f = sweep[0]
		avg_run = 0
		step = 0
		begin = time.time()
		#This is the function that runs the experiment and does the plotting
		def animate(k):
			#Defines f,avg_run,step as global variables so we can update between function calls
			nonlocal f
			nonlocal avg_run
			nonlocal step

			#If f goes past end frequency, we are done
			if step >= length:
				#Save the signal and background arrays to the dictionary
				save_dict['Signal Run ' + str(int(avg_run))] = copy.deepcopy(signal)
				save_dict['Background Run ' + str(int(avg_run))] = copy.deepcopy(background)

				#if we haven't finished all averaging runs yet, reset all temp variables and continue
				if avg_run < config['Navg'] - 1:
					f = sweep[0]
					step = 0
					avg_run += 1
					return 

				#get the end of the progress time and calculate time elapsed
				end = time.process_time()
				print('time elapsed: ' + str(end - start))

				#Save everything and exit
				#save()
				sys.exit()

			#Otherwise, increment the frequency and continue
			else:
				#Get new frequency value
				f = sweep[step]
				
				#Read from the DAQ
				output = DAQ.readDAQ(reader, config['N_samples'] * 2, config['DAQtimeout'], data)

				#the signal is the even points and background is the odd points from the data array
				current_signal = data[0::2]
				current_background = data[1::2]

				#average both arrays
				sig_average = np.mean(current_signal)
				back_average = np.mean(current_background)

				#append signal to signal array and background to background array
				signal[step] = sig_average
				background[step] = back_average

				#Depending on the plotting type, either append the signal or the contrast
				if config['plotting_type'] == 'signal':
					ys[step] = sig_average
				elif config['plotting_type'] == 'contrast':
					ys[step] = sig_average - back_average
			    
			    #Average the y correctly 
				average_y[step] = ((average_y[step] * avg_run) + ys[step]) / (avg_run+1)

				#plot the new data, we plot the entire average arrays, but we only plot the realtime data up to what we have so far
				ax.clear()
				ax.plot(xs[:step + 1], ys[:step + 1], 'o')
				if avg_run == 0:
					ax.plot(average_x[:step + 1], average_y[:step + 1], 'r-')
				else:
					ax.plot(average_x, average_y, 'r-')

				#Make the plot look good
				plt.xticks(rotation=45, ha='right')
				plt.subplots_adjust(bottom=0.30)
				plt.title('Photo Counter Readout vs Frequency')
				plt.ylabel('Photodiode Voltage (V)')
				plt.xlabel('Frequency (GHz)')

				#If we are starting a new averaging run, print it
				if step == 0:
					print('Starting Averaging Round: ' + str(avg_run))
				step += 1

				#Test code to calculate the % complete and time left for the experiment
				pts_complete = (avg_run * length) + step
				fraction_complete = (pts_complete / total_pts) 
				intermediate_time = time.time()
				time_spent = intermediate_time - begin
				time_left = (time_spent / fraction_complete) - time_spent
				if step % 10 == 0:
					print('Percent Complete: ' + str(int((fraction_complete * 100))))
					print('Approx. Time Left (s): ' + str(int(time_left)))

		#Begin the animation - All of the experiment work is done in the animate function
		ani = animation.FuncAnimation(fig, animate, init_func = init, interval = 1, blit = False)
		plt.show()
	finally:
		closeExp()
		save()

