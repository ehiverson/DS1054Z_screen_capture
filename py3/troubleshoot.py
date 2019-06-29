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

__version__ = 'v1.1.0'
# Added TMC Blockheader decoding
# Added possibility to manually allow run for scopes other then DS1000Z
__author__ = 'RoGeorge'



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