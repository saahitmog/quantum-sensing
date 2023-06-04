from collections import OrderedDict
#import ESR_with_photodiode
#import ESR_with_single_photon
#import Rabi_with_single_photon
#import T1_with_single_photon
#import optimized_ESR
#import optimized_Rabi
#import optimized_T2
#import optimized_XY8
#import optimized_T1
#import optimized_correlSpec
#import magnet_sweep
#import T2_with_single_photon
#import XY8_with_single_photon
#import PBcontrol as PBctl
import argparse, os
import AWGESR
import AWGReadoutDelay
import AWGRabi
import AWGSpinEcho
import AWGT1Seq
import AWGXY8
import AWGCorrelSpec
import SRSESR
import SRSESRparallel
import SRSESRparallel_photodiode

def main():
    config = cmdInput()
    if config['sequence_name'] == 'ESRseq':
        if config['photon_or_photodiode'] == 'photodiode':
            #ESR_with_photodiode.run(config)
            x=0
        elif config['photon_or_photodiode'] == 'photon':
            if config['optimized'] == 'false':
                #ESR_with_single_photon.run(config) 
                x=0
            else:
                magnet_sweep.run(config)
    if config['sequence_name'] == 'AWGESRseq':
        AWGESR.run(config) #CHANGE FOR AWG
        x=0
    if config['sequence_name'] == 'SRSESRseq':
        SRSESR.run(config)
        x=0
    if config['sequence_name'] == 'SRSESRparallelseq':
        if config['photon_or_photodiode'] == 'photodiode':
            SRSESRparallel_photodiode.run(config)
            x=0
        elif config['photon_or_photodiode'] == 'photon':
            if config['optimized'] == 'false':
                #ESR_with_single_photon.run(config) 
                x=0
            else:
                SRSESRparallel.run(config)
        x=0
    if config['sequence_name'] == 'AWGReadoutDelayseq':
        AWGReadoutDelay.run(config) #CHANGE FOR AWG
        x=0   
    if config['sequence_name'] == 'AWGRabiseq':
        AWGRabi.run(config) #CHANGE FOR AWG
        x=0
    if config['sequence_name'] == 'AWGT2seq':
        AWGSpinEcho.run(config) #CHANGE FOR AWG
        x=0  
    if config['sequence_name'] == 'AWGT1seq':
        AWGT1Seq.run(config) #CHANGE FOR AWG
        x=0
    if config['sequence_name'] == 'AWGXY8seq':
        AWGXY8.run(config) #CHANGE FOR AWG
        x=0
    if config['sequence_name'] == 'AWGcorrelSpecSeq':
        AWGCorrelSpec.run(config) #CHANGE FOR AWG
        x=0
    if config['sequence_name'] == 'RabiSeq':
        if config['photon_or_photodiode'] == 'photodiode':
            #Rabi_with_photodiode.run(config)
            x=0
        elif config['photon_or_photodiode'] == 'photon':
            if config['optimized'] == 'false':
                #Rabi_with_single_photon.run(config)
                x=0
            else: 
                optimized_Rabi.run(config)
    if config['sequence_name'] == 'T1seq':
        if config['photon_or_photodiode'] == 'photodiode':
            #T1_with_photodiode.run(config)
            x=0
        elif config['photon_or_photodiode'] == 'photon':
            if config['optimized'] == 'false':
                #T1_with_single_photon.run(config)
                x=0
            else:
                optimized_T1.run(config)
    if config['sequence_name'] == 'T2seq':
        if config['photon_or_photodiode'] == 'photodiode':
            #T1_with_photodiode.run(config)
            x=0
        elif config['photon_or_photodiode'] == 'photon':
            if config['optimized'] == 'false':
                #T2_with_single_photon.run(config)
                x=0
            else:
                optimized_T2.run(config)
    if config['sequence_name'] == 'XY8seq':
        if config['photon_or_photodiode'] == 'photodiode':
            #T1_with_photodiode.run(config)
            x=0
        elif config['photon_or_photodiode'] == 'photon':
            if config['optimized'] == 'false':
                #XY8_with_single_photon.run(config)
                x=0
            else:
                optimized_XY8.run(config)
    if config['sequence_name'] == 'correlSpecSeq':
        optimized_correlSpec.run(config)

def read_config(filename):
    fid = open(filename, 'r')
    lines = fid.readlines()
    fid.close()

    ret_val = OrderedDict()
    for line in lines:
        line = line.replace('\r', '').replace('\n', '')
        split_str = line.split(' = ')

        key = split_str[0]
        value_str = split_str[1].replace(' ', '')

        if value_str.find(',') > -1:
            # array detected
            split_str = value_str.split(',')
            value = []
            for s in split_str:
                try:
                    value.append(float(s))
                except:
                    value.append(s)
        else:
            try:
                value = float(value_str)
            except:
                value = value_str
                if value == "No":
                    value = False

        ret_val[key] = value
    return ret_val

def createCommandLineParser():
    ''' Creates parser for config file. '''
    parser = argparse.ArgumentParser() 
    parser.add_argument('--config', required=False, default='config.txt')
    return parser

def cmdInput():
    ''' Reads command line to configure variables. '''
    parser = createCommandLineParser()
    # try:
    #     args = parser.parse_args()
    #     config = read_config(args.config)
    # except:
    #     print('Fail, check config file')
    #     os.sys.exit(1)
    args = parser.parse_args()
    config = read_config(args.config) 
    return config

if __name__ == "__main__":
    main()