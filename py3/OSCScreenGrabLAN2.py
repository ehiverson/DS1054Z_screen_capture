#!/usr/bin/env python

#from telnetlib_receive_all import Telnet
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


def print_help():
    print()
    print("Usage:")
    print("    " + "python " + script_name + " png|bmp|csv [oscilloscope_IP [save_path]]")
    print()
    print("Usage examples:")
    print("    " + "python " + script_name + " png")
    print("    " + "python " + script_name + " csv 192.168.1.3")
    print()
    print("The following usage cases are not yet implemented:")
    print("    " + "python " + script_name + " bmp 192.168.1.3 my_place_for_captures")
    print()
    print("This program captures either the waveform or the whole screen")
    print("    of a Rigol DS1000Z series oscilloscope, then save it on the computer")
    print("    as a CSV, PNG or BMP file with a timestamp in the file name.")
    print()
    print("    The program is using LXI protocol, so the computer")
    print("    must have LAN connection with the oscilloscope.")
    print("    USB and/or GPIB connections are not used by this software.")
    print()
    print("    No VISA, IVI or Rigol drivers are needed.")
    print()

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

if file_format in ["png", "bmp"]:
    # Ask for an oscilloscope display print screen
    print("Receiving screen capture...")
    buff = command(tn, "DISP:DATA?")

    expectedBuffLen = expected_buff_bytes(buff)
    # Just in case the transfer did not complete in the expected time, read the remaining 'buff' chunks
    while len(buff) < expectedBuffLen:
        logging.warning("Received LESS data then expected! (" +
                        str(len(buff)) + " out of " + str(expectedBuffLen) + " expected 'buff' bytes.)")
        tmp = tn.read_until( b'\n', smallWait) #added b prefix
        if len(tmp) == 0:
            break
        buff += tmp
        logging.warning(str(len(tmp)) + " leftover bytes added to 'buff'.")

    if len(buff) < expectedBuffLen:
        logging.error("After reading all data chunks, 'buff' is still shorter then expected! (" +
                      str(len(buff)) + " out of " + str(expectedBuffLen) + " expected 'buff' bytes.)")
        sys.exit("ERROR")

    # Strip TMC Blockheader and keep only the data
    tmcHeaderLen = tmc_header_bytes(buff)
    expectedDataLen = expected_data_bytes(buff)
    buff = buff[tmcHeaderLen: tmcHeaderLen+expectedDataLen]

    # Save as PNG or BMP according to file_format
    im = Image.open(io.StringIO(buff))
    im.save(filename + "." + file_format, file_format)
    print("Saved file:", "'" + filename + "." + file_format + "'")

# TODO: Change WAV:FORM from ASC to BYTE
elif file_format == "csv":
    # Put the scope in STOP mode - for the moment, deal with it by manually stopping the scope
    # TODO: Add command line switch and code logic for 1200 vs ALL memory data points
    # tn.write("stop")
    # response = tn.read_until("\n", 1)

    # Scan for displayed channels
    chanList = []
    for channel in ["CHAN1", "CHAN2", "CHAN3", "CHAN4", "MATH"]:
        response = command(tn, channel + ":DISP?")

        # If channel is active
        if response == '1\n':
            chanList += [channel]

    # the meaning of 'max' is   - will read only the displayed data when the scope is in RUN mode,
    #                             or when the MATH channel is selected
    #                           - will read all the acquired data points when the scope is in STOP mode
    # TODO: Change mode to MAX
    # TODO: Add command line switch for MAX/NORM
    command(tn, "WAV:MODE MAX")
    #command(tn, "WAV:STAR 1")
    '''
    try bytes too in another file
    '''
    command(tn, "WAV:FORM ASC")
    memdepth = int(command( tn, 'ACQuire:MDepth?'))
    max_read = 15625
    num_reads = ceil(memdepth / max_read)
    data = pd.DataFrame(data=np.zeros((memdepth,len(chanList))),columns = chanList)
    #find out if the mode is normal, max, or raw
    #if not in normal mode, stop the scope from triggering
    
      mode = command(tn, 'WAV:MODE?').strip()
    if mode in ['MAX', 'RAW']:
        command(tn, 'STOP')
    #csv_buff = ""
    #csv_buff = pd.DataFrame(columns = chanList)
    
    # for each active channel
    for channel in chanList:
        print()

        # Set WAVE parameters
        command(tn, "WAV:SOUR " + channel)
   
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
            print('start: {}'.format(command(tn, "WAV:STARt?")))
            print('stop: {}'.format(command(tn, "WAV:STOP?")))
            chunk = command(tn, "WAV:DATA?")
        # Append data chunks
        # Strip TMC Blockheader and terminator bytes
            chunk = chunk[tmc_header_bytes(chunk):-1]
            chunkList = chunk.split(",")
            chunkListFloats = [float(y) for y in chunkList]
            ser = ser.append(pd.Series(chunkListFloats) )
        # Process data
        data[channel][:] = ser[:]
     
    
    data['time'] = [x * x_incr for x in range(len(ser))]
    #csv_buff.to_csv(path_or_buf= filename + '.csv')
    #print("Saved file:", "'" + filename + "." + file_format + "'")

tn.close()
plt.plot(data['time'][0:1000], data['CHAN3'][0:1000] ,label='Measured' )

plt.xlabel('Time [sec]')
plt.ylabel('Voltage [V]')
plt.title("Interesting Square Wave")
plt.grid()
plt.legend()
plt.show()