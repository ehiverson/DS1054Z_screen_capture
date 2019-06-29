# -*- coding: utf-8 -*-
"""
Created on Fri Jun 28 07:07:57 2019

@author: Erik
"""

from telnetlib import Telnet
from Rigol_functions import *
import time
#from PIL import Image
import io
import sys
import os
import platform
import logging
import pandas as pd
import matplotlib.pyplot as plt
from math import ceil 
import numpy as np
from datetime import datetime

__version__ = 'v1.1.0'
# Added TMC Blockheader decoding
# Added possibility to manually allow run for scopes other then DS1000Z
__author__ = 'RoGeorge'
'''
With TelNet:
    
%time command(tn, '*IDN?')
Wall time: 4 ms
Out[7]: 'RIGOL TECHNOLOGIES,DS1104Z,DS1ZA191605554,00.04.04.SP4\n'

'''


# Set the desired logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename=os.path.basename(sys.argv[0]) + '.log',
                    filemode='w')

logging.info("***** New run started...")
logging.info("OS Platform: " + str(platform.uname()))
log_running_python_versions()

# Update the next lines for your own default settings:
path_to_save = "captures/"
save_format = "PNG"
IP_DS1104Z = "192.254.212.61"

# Rigol/LXI specific constants
port = 5555

big_wait = 10
smallWait = 1

company = 0
model = 1
serial = 2

# Check command line parameters
script_name = os.path.basename(sys.argv[0])



# Read/verify file type
if len(sys.argv) <= 1:
    print_help()
    sys.exit("Warning - wrong command line parameters.")
elif sys.argv[1].lower() not in ["png", "bmp", "csv"]:
    print_help()
    print("This file type is not supported: ", sys.argv[1])
    sys.exit("ERROR")

file_format = sys.argv[1].lower()

# Read IP
if len(sys.argv) > 1:
    IP_DS1104Z = sys.argv[2]

# Check network response (ping)
if platform.system() == "Windows":
    response = os.system("ping -n 1 " + IP_DS1104Z + " > nul")
else:
    response = os.system("ping -c 1 " + IP_DS1104Z + " > /dev/null")

if response != 0:
    print()
    print("WARNING! No response pinging " + IP_DS1104Z)
    print("Check network cables and settings.")
    print("You should be able to ping the oscilloscope.")

# Open a modified telnet session
# The default telnetlib drops 0x00 characters,
#   so a modified library 'telnetlib_receive_all' is used instead
tn = Telnet(IP_DS1104Z, port)
instrument_id = command(tn, "*IDN?")    # ask for instrument ID

# Check if instrument is set to accept LAN commands
if instrument_id == "command error":
    print("Instrument reply:", instrument_id)
    print("Check the oscilloscope settings.")
    print("Utility -> IO Setting -> RemoteIO -> LAN must be ON")
    sys.exit("ERROR")

# Check if instrument is indeed a Rigol DS1000Z series
id_fields = instrument_id.split(",")

if (id_fields[company] != "RIGOL TECHNOLOGIES") or \
        (id_fields[model][:3] != "DS1") or (id_fields[model][-1] != "Z"):
    print("Found instrument model", "'" + id_fields[model] + "'", "from", "'" + id_fields[company] + "'")
    print("WARNING: No Rigol from series DS1000Z found at", IP_DS1104Z)
    print()
    typed = input("ARE YOU SURE YOU WANT TO CONTINUE? (No/Yes):")
    if typed != 'Yes':
        sys.exit('Nothing done. Bye!')

print("Instrument ID:", end=' ')
print(instrument_id)

# Prepare filename as C:\MODEL_SERIAL_YYYY-MM-DD_HH.MM.SS
timestamp = time.strftime("%Y-%m-%d_%H.%M.%S", time.localtime())
filename = path_to_save + id_fields[model] + "_" + id_fields[serial] + "_" + timestamp




chanList = []
for channel in ["CHAN1", "CHAN2", "CHAN3", "CHAN4", "MATH"]:
    response = command(tn, channel + ":DISP?")

    # If channel is active
    if response == '1\n':
        chanList += [channel]

command(tn, "WAV:MODE MAX")

command(tn, "WAV:FORM BYTE")
memdepth = int(command( tn, 'ACQuire:MDepth?'))
max_read = 250000
num_reads = ceil(memdepth / max_read)
data = pd.DataFrame(data=np.zeros((memdepth,len(chanList))),columns = chanList)

mode = command(tn, 'WAV:MODE?').strip()
if mode in ['MAX', 'RAW']:
    command(tn, 'STOP')

for channel in chanList:
    

    # Set WAVE parameters
    command(tn, "WAV:SOUR " + channel)
    #command(tn, "WAV:FORM ")

    params = command(tn, 'WAV:PRE?' ).split(',')
    form = params[0]
    typ = params[1]
    x_num = int(params[2])
    x_incr = float(params[4])
    x_origin = float(params[5])
    y_increment = float(params[7])
    y_origin = float(params[8])
    y_ref = float(params[9])
    
    '''
    # MATH channel does not allow START and STOP to be set. They are always 0 and 1200
    if channel != "MATH":
        command(tn, "WAV:STAR 1")
        command(tn, "WAV:STOP 1200")
    '''
    ser = pd.Series()
    for i in range(num_reads):
        start = max_read*i + 1 #1, 250,001, 500,001, ...
        if i == num_reads - 1:
            stop = memdepth
        else:
            stop = start + max_read - 1#start + max_read - 1 #250,000, 500,000, 750,000, ...
     
        command(tn, "WAVeform:STARt {}".format(start))
        command(tn, "WAVeform:STOP {}".format(stop))
        #print('start: {}'.format(command(tn, "WAV:STARt?")))
        #print('stop: {}'.format(command(tn, "WAV:STOP?")))
        chunk = command2(tn, "WAV:DATA?")
    # Append data chunks
    # Strip TMC Blockheader and terminator bytes
    #don't bother decoding the WHOLE chunk
        chunk = chunk[tmc_header_bytes(chunk[0:30].decode()):-1]
        scaled_data_y = [(int(y)-y_origin-y_ref)*y_increment for y in chunk]   
        ser = ser.append(pd.Series(scaled_data_y) )
    # Process data
    data[channel][:] = ser[:]
   
command(tn, 'RUN')
data['time'] = [x * x_incr for x in range(len(ser))]


timeStamp = datetime.now().strftime('-%m_%d_%Y_%H_%M')
save_loc = os.path.join(os.getcwd(), 'captures')
filename='DS1104Z' + timeStamp
data.to_csv(path_or_buf= os.path.join(save_loc,  filename +'.csv'),index=False)

'''
tn.close()
plt.plot(data['time'][0:50000], data['CHAN3'][0:50000] ,label='Measured' )
plt.xlabel('Time [sec]')
plt.ylabel('Voltage [V]')
plt.title("Interesting Square Wave")
plt.grid()
plt.legend()
plt.show()
'''