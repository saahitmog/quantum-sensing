Instructions for fancy_microscope ESR (on Pink Diamond in quantum_sensing/fancy_microscope):

Opening fancy_microscope interface:
1. Open Anaconda prompt
2. Navigate to C:\Users\Public\quantum_sensing\quantum_sensing\fancy_microscope
3. Activate scopefoundry environment (conda activate scopefoundry)
4. Run fancy_microscope python file (python fancy_microscope.py)

ESR procedure from interface:
1. Find Measurements window (towards bottom left of interface)
2. Expand ESR_measurement item
3. Set experiment parameters such as Npts, Navg, mw_power etc.
4. Set save directory and sample name in far bottom left of interface (in box area labelled App)
5. Click start button
6. Let experiment terminate (or click interrupt button to terminate before completion)

Data will be saved automatically as both an h5 and csv in the specified directory. 
H5 contains all paramaters, app settings, and the actual data. CSV contains only
the sweep frequencies and each signal and background run.

Camera instructions:

log files/settings