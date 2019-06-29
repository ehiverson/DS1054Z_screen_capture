# -*- coding: utf-8 -*-
"""
Created on Tue Jun 11 20:38:57 2019

@author: Erik
"""

#import pip
import pkg_resources
import sys
import logging

__author__ = 'RoGeorge'


def log_running_python_versions():
    logging.info("Python version: " + str(sys.version) + ", " + str(sys.version_info))  # () required in Python 3.
    
    installed_packages = [d for d in pkg_resources.working_set]
    installed_packages_ll = [ (x[0],x[1]) for x in (str(d).split() for d in installed_packages) ]
    installed_packages_list = sorted(["%s==%s" % ( i[0], i[1] ) for i in installed_packages_ll])
    logging.info("Installed Python modules: " + str(installed_packages_list))


def command(tn, scpi):
    scpi_bytes = scpi.encode()
    logging.info("SCPI to be sent: " + scpi)
    answer_wait_s = 1
    #response = ""
    response = bytearray()
    while response.decode() != "1\n":
        tn.write("*OPC?\n".encode())  # previous operation(s) has completed ?
        logging.info("Send SCPI: *OPC? # May I send a command? 1==yes")
        response = tn.read_until(b"\n", 1)  # wait max 1s for an answer
        logging.info("Received response: " + response.decode())

    tn.write(scpi_bytes + "\n".encode())
    logging.info("Sent SCPI: " + scpi)
    response = tn.read_until(b"\n", answer_wait_s)
    logging.info("Received response: " + response.decode())
    return response.decode()

def command2(tn, scpi):
    scpi_bytes = scpi.encode()
    logging.info("SCPI to be sent: " + scpi)
    answer_wait_s = 1
    response = bytearray()
    tn.write(scpi_bytes + "\n".encode())
    logging.info("Sent SCPI: " + scpi)
    response = tn.read_until(b"\n", answer_wait_s)
    #logging.info("Received response: " + response.decode())
    return response

# first TMC byte is '#'
# second is '0'..'9', and tells how many of the next ASCII chars
#   should be converted into an integer.
#   The integer will be the length of the data stream (in bytes)
# after all the data bytes, the last char is '\n'
def tmc_header_bytes(buff):
    return 2 + int(buff[1])


def expected_data_bytes(buff):
    return int(buff[2:tmc_header_bytes(buff)])


def expected_buff_bytes(buff):
    return tmc_header_bytes(buff) + expected_data_bytes(buff) + 1


def get_memory_depth(tn):
    # Define number of horizontal grid divisions for DS1054Z
    h_grid = 12

    # ACQuire:MDEPth
    mdep = command(tn, ":ACQ:MDEP?")

    # if mdep is "AUTO"
    if mdep == "AUTO\n":
        # ACQuire:SRATe
        srate = command(tn, ":ACQ:SRAT?")

        # TIMebase[:MAIN]:SCALe
        scal = command(tn, ":TIM:SCAL?")

        # mdep = h_grid * scal * srate
        mdep = h_grid * float(scal) * float(srate)

    # return mdep
    return int(mdep)