# -*- coding: utf-8 -*-
"""
Created on Thu Jul 11 07:05:23 2019

@author: Erik
"""
import time
import io
import sys
import os
import platform
import logging
import pandas as pd
from math import ceil 
import numpy as np
from datetime import datetime

class RigolLAN():
    
    def __init__(self, tn):
        self.tn = tn
        return
    
    def command(self,scpi):
        tn = self.tn
        scpi_bytes = scpi.encode()
        #logging.info("SCPI to be sent: " + scpi)
        answer_wait_s = 1
        #response = ""
        response = bytearray()
        while response.decode() != "1\n":
            tn.write("*OPC?\n".encode())  # previous operation(s) has completed ?
            #logging.info("Send SCPI: *OPC? # May I send a command? 1==yes")
            response = tn.read_until(b"\n", 1)  # wait max 1s for an answer
            #logging.info("Received response: " + response.decode())
    
        tn.write(scpi_bytes + "\n".encode())
        #logging.info("Sent SCPI: " + scpi)
        response = tn.read_until(b"\n", answer_wait_s)
        #logging.info("Received response: " + response.decode())
        return response.decode()
    
    
    def command2(self,scpi):
        tn=self.tn
        scpi_bytes = scpi.encode()
        #logging.info("SCPI to be sent: " + scpi)
        answer_wait_s = 1
        response = bytearray()
        tn.write(scpi_bytes + "\n".encode())
        #logging.info("Sent SCPI: " + scpi)
        response = tn.read_until(b"\n", answer_wait_s)
        #logging.info("Received response: " + response.decode())
        return response
    
    # first TMC byte is '#'
    # second is '0'..'9', and tells how many of the next ASCII chars
    #   should be converted into an integer.
    #   The integer will be the length of the data stream (in bytes)
    # after all the data bytes, the last char is '\n'
    def tmc_header_bytes(self, buff):
        return 2 + int(buff[1])
    def expected_data_bytes(self, buff):
        return int(buff[2:tmc_header_bytes(buff)])
    def expected_buff_bytes(self, buff):
        return tmc_header_bytes(buff) + expected_data_bytes(buff) + 1
    
    def fullCapture(self):
        
        chanList = []
        for channel in ["CHAN1", "CHAN2", "CHAN3", "CHAN4", "MATH"]:
            response = self.command(channel + ":DISP?")
        
            # If channel is active
            if response == '1\n':
                chanList += [channel]
        
        self.command("WAV:MODE MAX")
        self.command("WAV:FORM BYTE")
        memdepth = int(self.command('ACQuire:MDepth?'))
        max_read = 250000
        num_reads = ceil(memdepth / max_read)
        data = pd.DataFrame(data=np.zeros((memdepth,len(chanList))),columns = chanList)
        
        mode = self.command('WAV:MODE?').strip()
        if mode in ['MAX', 'RAW']:
            self.command('STOP')
        
        for channel in chanList:
            
        
            # Set WAVE parameters
            self.command("WAV:SOUR " + channel)
            #command(tn, "WAV:FORM ")
        
            params = self.command('WAV:PRE?' ).split(',')
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
             
                self.command("WAVeform:STARt {}".format(start))
                self.command("WAVeform:STOP {}".format(stop))
                #print('start: {}'.format(command(tn, "WAV:STARt?")))
                #print('stop: {}'.format(command(tn, "WAV:STOP?")))
                chunk = self.command2("WAV:DATA?")
            # Append data chunks
            # Strip TMC Blockheader and terminator bytes
            #don't bother decoding the WHOLE chunk
                chunk = chunk[self.tmc_header_bytes(chunk[0:30].decode()):-1]
                scaled_data_y = [(int(y)-y_origin-y_ref)*y_increment for y in chunk]   
                ser = ser.append(pd.Series(scaled_data_y) )
            # Process data
            data[channel][:] = ser[:]
           
        self.command('RUN')
        data['time'] = [x * x_incr for x in range(len(ser))]
        return data
    
    
    
    
    