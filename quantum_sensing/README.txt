quantum_sensing package instructions:

1. Open Anaconda prompt

2. Navigate to C:\Users\Public\quantum_sensing\quantum_sensing

3. Edit config .txt file corresponding with your desired experiment (i.e. T1_config for T1, Rabi_config for Rabi, 
AWGESR_config for ESR with AWG, SRSESR_config for ESR with SRS etc.) The config file should contain all relevant parameters
that can be modified for the experiment (such as mw_power, t_AOM, Npts, N_avg etc.) Do not change the sequence_name at the top.

4. Run mainRun.py with the config file specified (i.e. python mainRun.py --config AWGESR_config.txt)