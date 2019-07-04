# -*- coding: utf-8 -*-
"""
Created on Thu Jul  4 09:18:16 2019

@author: Erik
"""

import os
import sys
from PySide2.QtWidgets import QApplication, QMainWindow, QFileDialog, \
qApp, QLabel, QWidget, QMessageBox, QPushButton, QLineEdit, QRadioButton, QPlainTextEdit
from PySide2.QtCore import QObject, Signal, Slot, QFile
from PySide2.QtUiTools import QUiLoader


import pyvisa
from datetime import datetime
import pandas as pd
import numpy as np
from telnetlib import Telnet
from threading import Thread
import re
from rigol_ds1054z import rigol_ds1054z
import tek2024b
import time



class MyApp(QMainWindow):
    
    ConnectSignal = Signal()
  
    def __init__(self,ui_file, parent=None):
        super(MyApp, self).__init__()
        
        ui_file = QFile(ui_file)
        ui_file.open(QFile.ReadOnly)
        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()

        self.CaptureButton = self.window.findChild(QPushButton, 'CaptureButton')
        self.FileNameLineEdit= self.window.findChild(QLineEdit, 'FileNameLineEdit')
        self.FilePathButton= self.window.findChild(QPushButton, 'FilePathButton')
        self.FilePathLineEdit = self.window.findChild(QLineEdit, 'FilePathLineEdit')
        self.ScopeInfoLineEdit= self.window.findChild(QLineEdit, 'ScopeInfoLineEdit')
        self.ScreenDataButton= self.window.findChild(QRadioButton, 'ScreenDataButton')
        self.FullMemoryButton= self.window.findChild(QRadioButton, 'FullMemoryButton')
        self.ScreenImageRadioButton = self.window.findChild(QRadioButton, 'ScreenImageRadioButton')
        self.textEdit = self.window.findChild(QPlainTextEdit, 'plainTextEdit' )

        self.window.setGeometry(200, 50, 600, 350)
        self.CaptureButton.setDisabled(True)
        self.scopeConnected = False
        self.filepath = os.getcwd()
        self.filename = datetime.now().strftime('-%m_%d_%Y_%H_%M')
        self.FileNameLineEdit.setText(self.filename)
        self.FilePathLineEdit.setText(self.filepath)
        self.FullPathAndName = None
        self.FilePathButton.pressed.connect(self.openFileNameDialog)
        self.Connection = Connection()
        self.Connection.ScopeInfo.connect(self.ScopeInfoLineEdit.setText)
        #self.Connection.ScopeInfo.connect(self.getScope)
        self.ScopeInfoLineEdit.setText('No Scope')
        self.Connection.startConnectThread()
        self.Connection.ConnectionGood.connect(self.setEnabled)
        self.CaptureButton.pressed.connect(self.stupid)
        self.CaptureButton.pressed.connect(self.dispatchCapture)
        self.Connection.Result.connect(self.showResult)
        self.FileNameLineEdit.editingFinished.connect(self.updateFilename)
        self.FilePathLineEdit.editingFinished.connect(self.updateFilename)
        self.updateFilename()
        self.textEdit.setPlainText('Welcome!')
        self.window.show()
    
    @Slot()
    def updateFilename(self):
        string = self.FileNameLineEdit.text()
        dashindex = string.find('-')
        
        self.filename = datetime.now().strftime('-%m_%d_%Y_%H_%M')
        self.FileNameLineEdit.setText(self.filename)
        
        string = self.FileNameLineEdit.text()
        path = self.FilePathLineEdit.text()
        if self.ScreenDataButton.isChecked() or self.FullMemoryButton.isChecked():
            self.FullPathAndName = os.path.join(path, string + '.csv')
        elif self.ScreenImageRadioButton.isChecked():
            self.FullPathAndName = os.path.join(path, string + '.png')
        
    @Slot()
    def openFileNameDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        options |= QFileDialog.ShowDirsOnly
        filepath = QFileDialog.getExistingDirectory(self,"QFileDialog.getExistingDirectory()", "", options=options)
        if filepath:
            self.FilePathLineEdit.setText(filepath)
            self.filepath = filepath
            self.FilePathLineEdit.editingFinished.emit()
    
    @Slot()
    def stupid(self):
        self.textEdit.setPlainText('Starting Capture!{}{}'.format(1,2))
        return
    
    @Slot()
    def dispatchCapture(self):
        
        self.updateFilename()
        #self.textEdit.setPlainText('Starting Capture!{}{}'.format(1,2))
        
        #time.sleep(.5)
        self.CaptureButton.setDisabled(True)
        if self.ScreenImageRadioButton.isChecked():
            self.Connection.getImage(self.FullPathAndName)
            self.textEdit.setPlainText('Saved the Image!')
            time.sleep(1)
            self.textEdit.setPlainText('Ready...')
        if self.ScreenDataButton.isChecked():
            self.Connection.screenCapture(self.FullPathAndName)
        if self.FullMemoryButton.isChecked():
            self.Connection.fullCapture(self.FullPathAndName)
        self.CaptureButton.setEnabled(True)
        self.CaptureButton.setChecked(False)
            
        
    @Slot(int)
    def setEnabled(self, i):
        '''
        tekscope if i = 0 so disable full memory option and bmp
        '''
        self.ScreenDataButton.setEnabled(True)
        self.ScreenDataButton.setChecked(True)
        if i == 0:
            self.ScreenImageRadioButton.setDisabled(True)
            self.FullMemoryButton.setDisabled(True)
            self.CaptureButton.setEnabled(True)
        if i == 1:
            self.ScreenImageRadioButton.setEnabled(True)
            self.FullMemoryButton.setEnabled(True)
            self.CaptureButton.setEnabled(True)
        if i==2:
            self.CaptureButton.setDisabled(True)
    @Slot(dict)    
    def showResult(self, adict):
        text = 'wrote a dataframe of size {} with columns {}'.format(adict['size'], adict['columns'])
        self.textEdit.setPlainText(text)

class Connection(QObject):
    
    ScopeInfo = Signal(str)
    ConnectionGood = Signal(int)
    Result = Signal(dict)
    
    
    def __init__(self):
        super().__init__()
        self.ScopeInfoString = None
        self.scope = None
        return 
        
    @Slot()
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
                
                name_str = None
                try:
                    inst = rm.open_resource(resource_id, send_end=True )
                    name_str = inst.query('*IDN?').strip()
                    if tekPattern.match(name_str) is not None:
                        self.scope = tek2024b.tek2024b(inst)  
                        self.ConnectionGood.emit(0)
                    if rigolPattern.match(name_str) is not None:
                        self.scope = rigol_ds1054z(inst)
                        self.ConnectionGood.emit(1)
                except pyvisa.errors.VisaIOError:
                    pass
                if self.scope is None:
                    self.ScopeInfo.emit('No Scope')
                    self.ConnectionGood.emit(2)
                else:
                    self.ScopeInfo.emit(name_str[0:20])
                    self.ScopeInfoString = name_str
                    break
            if name_str is not None:
                break
            
   
            time.sleep(1)
    #these functions below should run in separate threads
    
    def screenCapture(self, path):
        df = self.scope.capture()
        df.to_csv(path_or_buf=path,index=False)   
        self.Result.emit({'columns':df.columns, 'size':df.size})
        return
    def getImage(self, path):
        image = self.scope.getImage()
        fid = open(path, 'wb')
        print(path)
        fid.write(image)
        fid.close()
        
        return
    def fullCapture(self,path):
        df = self.scope.fullCapture()
        df.to_csv(path_or_buf=path,index=False)
        columns = df.columns
        size = df.size
        self.Result.emit({'columns':columns, 'size':size})
        
        return
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyApp("DS1054Z_GUI.ui")
    sys.exit(app.exec_())