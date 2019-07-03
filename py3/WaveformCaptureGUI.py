# -*- coding: utf-8 -*-
"""
Created on Mon Jul  1 07:40:11 2019

@author: Erik
"""

import os
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, qApp, QLabel, QWidget, QMessageBox, QPushButton#, QPixmap, QAction
from PyQt5.QtCore import pyqtSignal, QObject, pyqtSlot#, QThread, QObject
import pyvisa
from datetime import datetime
from PyQt5 import uic
import pandas as pd
import numpy as np
from telnetlib import Telnet
from threading import Thread
import re
from rigol_ds1054z import rigol_ds1054z
import tek2024b

qtCreatorFile = "DS1054Z_GUI.ui"
Ui_MainWindow, QtBaseClass = uic.loadUiType(qtCreatorFile)

class MyApp(QMainWindow, Ui_MainWindow):
    
    ConnectSignal = pyqtSignal()
  
    def __init__(self,):
        QMainWindow.__init__(self,)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.setGeometry(200, 50, 600, 350)
        self.scopeConnected = False
        self.filepath = os.getcwd()
        self.FilePathLineEdit.setText(self.filepath)
        self.FilePathButton.pressed.connect(self.openFileNameDialog)
        self.Connection = Connection()
        self.Connection.ScopeInfo.connect(self.ScopeInfoLineEdit.setText)
        #self.Connection.ScopeInfo.connect(self.getScope)
        self.ScopeInfoLineEdit.setText('No Scope')
        self.Connection.startConnectThread()
        self.Connection.ConnectionGood.connect(self.setEnabled)
        self.CaptureButton.pressed.connect(self.Connection.capture)
        
        
 

    def openFileNameDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        options |= QFileDialog.ShowDirsOnly
        filepath = QFileDialog.getExistingDirectory(self,"QFileDialog.getExistingDirectory()", "", options=options)
        if filepath:
            self.FilePathLineEdit.setText(filepath)
            self.filepath = filepath
            self.FilePathLineEdit.editingFinished.emit()
            
class Connection(QObject):
    
    ScopeInfo = pyqtSignal(str)
    ConnectionGood = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self.ScopeInfoString = None
        self.scope = None
        return 
        
    @pyqtSlot()
    def startConnectThread(self):
        self.ConnectThread = Thread(target=self.makeConnection, name='connect')
        self.ConnectThread.start()
        return
    
    def makeConnection(self):     
        
        tekPattern = re.compile('TEKTRONIX,TPS 2024B,')
        rigolPattern = re.compile('RIGOL TECHNOLOGIES,DS1104Z')
        #ip = IPAddressLineEdit.text()
        while True:
            rm = pyvisa.ResourceManager()
            tup =  rm.list_resources()
            
            for resource_id in tup :
                name_str = 'none'
                try:
                    inst = rm.open_resource(resource_id, send_end=True )
                    name_str = inst.query('*IDN?').strip()
                    if tekPattern.match(name_str) is not None:
                        self.scope = tek2024b.tek2024b(inst)            
                    if rigolPattern.match(name_str) is not None:
                        self.scope = rigol_ds1054z(inst)
                except pyvisa.errors.VisaIOError:
                    pass
                if self.scope is None:
                    self.ScopeInfo.emit('No Scope')
                    self.ConnectionGood.emit(False)
                else:
                    self.ScopeInfo.emit(name_str[0:20])
                    self.ScopeInfoString = name_str
                    self.ConnectionGood.emit(True)
                    break
            if name_str is not None:
                break
            
   
            time.sleep(1)
    def capture(self):
        df = self.scope.capture()
        
        return
if __name__ == "__main__":
    app = QApplication(sys.argv)#sys.argv
    window = MyApp()
    window.show()
    sys.exit(app.exec_())