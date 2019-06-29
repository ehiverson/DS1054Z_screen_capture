# -*- coding: utf-8 -*-
"""
Created on Sun Jun 16 10:12:22 2019

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
path_to_save = "captures/"
#my_str = 'CHAN3\r\n7.999732e-02\r\n3.999732e-02\r\n7.999732e-02\r\n3.999732e-02\r\n7.999732e-02\r\n3.999732e-02\r\n7.999732e-02\r\n3.999732e-02\r\n3.999732e-02\r\n7.999732e-02\r\n7.999732e-02\r\n3.999732e-02\r\n'
# Prepare filename as C:\MODEL_SERIAL_YYYY-MM-DD_HH.MM.SS
my_str2 = 'CHAN3\n7.999732e-02\n3.999732e-02\n7.999732e-02\n3.999732e-02\r\n7.999732e-02\r\n3.999732e-02\r\n7.999732e-02\r\n3.999732e-02\r\n3.999732e-02\r\n7.999732e-02\r\n7.999732e-02\r\n3.999732e-02\r\n'

timestamp = time.strftime("%Y-%m-%d_%H.%M.%S", time.localtime())
filename = path_to_save + 'sample' + "_" + timestamp


scr_file = open(filename + ".csv", "w")



scr_file.write(my_str2)
scr_file.close()