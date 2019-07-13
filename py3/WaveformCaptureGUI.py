# -*- coding: utf-8 -*-
"""
Created on Mon Jul  1 07:40:11 2019

@author: Erik
"""
import os
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, qApp, QLabel, QWidget, QMessageBox, QPushButton
from PyQt5.QtCore import pyqtSignal, QObject, pyqtSlot
from PyQt5.QtGui import QValidator
from PyQt5 import uic
import pyvisa
from datetime import datetime
import time
import pandas as pd
import numpy as np
from telnetlib import Telnet
from threading import Thread
import re
from rigol_ds1054z import rigol_ds1054z
from math import ceil
import tek2024b
from ipaddress import ip_address
from RigolLAN import RigolLAN

qtCreatorFile = "C:\\Users\\Erik\\git\\DS1054Z_screen_capture\\py3\\DS1054Z_GUI.ui"
Ui_MainWindow, QtBaseClass = uic.loadUiType(qtCreatorFile)

class MyApp(QMainWindow, Ui_MainWindow):
    """ The main window and the main class of the WaveformCaptureGUI. 
    
    """
    sendIPSignal = pyqtSignal(str)
    
    def __init__(self,):
        """
        There are no arguments to the init method. 
        """
        super(MyApp, self).__init__()
        QMainWindow.__init__(self,)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.setGeometry(200, 50, 600, 350)
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
        self.CaptureButton.pressed.connect(self.dispatchCapture)
        self.Connection.Result.connect(self.showResult)
        self.FileNameLineEdit.editingFinished.connect(self.updateFilename)
        self.FilePathLineEdit.editingFinished.connect(self.updateFilename)
        
        #self.IPAddressLineEdit.setValidator(IPValidator())
        self.IPAddressLineEdit.setText('000.000.000.000')
        self.IPAddressLineEdit.inputRejected.connect(self.wrongIPwarning)
        self.IPAddressLineEdit.editingFinished.connect(self.sendIP)
        self.sendIPSignal.connect(self.Connection.takeIP)
        #self.IPAddressLineEdit.textChanged.connect(self.Connection.takeIP)
        self.updateFilename()
    
    @pyqtSlot()
    def sendIP(self):
        if self.IPAddressLineEdit.text() != '000.000.000.000':
            self.sendIPSignal.emit(self.IPAddressLineEdit.text())
    
    @pyqtSlot()
    def wrongIPwarning(self):
        self.plainTextEdit.setPlainText('That IP Address is not valid!')
        
    @pyqtSlot()
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
        
  
    def openFileNameDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        options |= QFileDialog.ShowDirsOnly
        filepath = QFileDialog.getExistingDirectory(self,"QFileDialog.getExistingDirectory()", "", options=options)
        if filepath:
            self.FilePathLineEdit.setText(filepath)
            self.filepath = filepath
            self.FilePathLineEdit.editingFinished.emit()
    
    @pyqtSlot()
    def dispatchCapture(self):
        """
        The capture button was pressed, and this function is called. 
        
        """
        
        self.updateFilename()
        self.plainTextEdit.setPlainText('Starting Capture!')
        self.CaptureButton.setDisabled(True)
        self.CaptureButton.setChecked(True)
        
        if self.ScreenImageRadioButton.isChecked():
            imageThread = Thread(target=self.Connection.getImage, args=(self.FullPathAndName,))
            imageThread.start()
        if self.ScreenDataButton.isChecked():
            screenDataThread = Thread(target=self.Connection.screenCapture, args=(self.FullPathAndName,))
            screenDataThread.start()
        if self.FullMemoryButton.isChecked():
            fullMemoryThread = Thread(target=self.Connection.fullCapture, args=(self.FullPathAndName,))
            fullMemoryThread.start()
        self.plainTextEdit.setPlainText('Working...')
    
    @pyqtSlot(int)
    def setEnabled(self, i):
        """ Enables the appropriate user input options in the GUI. 
        
        Called automatically when ConnectionGood signal is emitted from the 
        Connection object.
        
        Args:
            i (int): If 0, the scope discovered is a Tek TPS2024B , which 
                only implements the screen waveform data transfer. If 1, 
                the scope is rigol and does all 3 radio button functions. If 2, 
                there is no scope, and the capture button should be disabled. 
        
        """
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
            
    def showResult(self, adict):
        self.CaptureButton.setEnabled(True)
        self.CaptureButton.setChecked(False)
        if adict['code'] == 0:
            text = 'wrote a dataframe of size {} with columns {}'.format(adict['size'], adict['columns'])
            self.plainTextEdit.setPlainText(text)
        if adict['code'] == 1:
            self.plainTextEdit.setPlainText('saved the image!')
        #if adict['code'] == 3: 
        #    self.plainTextEdit.setPlainText('')
        #if adict['code'] == 4:
        #    self.plainTextEdit.setPlainText('LAN Timeout Error!')
        #if adict['code'] == 5:
        #    self.plainTextEdit.setPlainText('Scope Refused Connection')

class Connection(QObject):
    """DocString for class Connection.
    
    Attributes
        ScopeInfo (pyqtSignal): Emits a string to be shown in the MyApp.ScopeInfoLineEdit    
            Emitted each time through the while loop.
        ConnectionGood (pyqtSignal): Uses a code of type int, and
            0 means the scope is a tektronix tps2024b.
            1 means the scope is a Rigol DS1054Z on USB.
            2 means there was nothing found.
            3 means the scope is a Rigol DS1054Z on LAN.
        
    """
    ScopeInfo = pyqtSignal(str)
    ConnectionGood = pyqtSignal(int)
    Result = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.ScopeInfoString = None
        self.scope = None
        self.ip = None
        return 
    def takeIP(self, ip):
        self.ip = ip    
    
    @pyqtSlot()
    def startConnectThread(self):
        """ 
        Creates a Thread object with a target of makeConnection,
        and starts that Thread. 
        """
        self.ConnectThread = Thread(target=self.makeConnection, name='connect')
        self.ConnectThread.start()
        return
    
    def makeConnection(self): 
        """
        Use pyvisa to create a ResourceManager that can create VisaInstruments.
        
        The instrument instances are saved as instance attributes. Loops 
        indefinitely in its own thread. with 1 second delay until a scope is found, 
        and then the ConnectionGood signal is emitted with a code other than 2
        
        See Also
            ConnectionGood
        
        """
        tekPattern = re.compile('TEKTRONIX,TPS 2024B,')
        rigolPattern = re.compile('RIGOL TECHNOLOGIES,DS1104Z')
        port=5555
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
                if self.ip is not None:
                    try:                
                        tn = Telnet(self.ip, port,timeout=2)
                        self.scope = RigolLAN(tn)
                        name_str = self.scope.command('*IDN?').strip()
                        self.ConnectionGood.emit(1)
                    
                    except TimeoutError:
                        self.ScopeInfo.emit('timeout')
                        time.sleep(.5)
                    except ConnectionRefusedError:
                        self.ScopeInfo.emit('connection refused')
                        time.sleep(.5)
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
    
    def screenCapture(self, path):
        """Save a the scope screen waveforms to path as a csv. Emits the Result 
        signal which the MyApp class uses to display information. The scope instance 
        attribute must implement a capture() method. 
        
        Args:
            path (str): A full path and filename.
        """
        df = self.scope.capture()
        df.to_csv(path_or_buf=path,index=False)   
        self.Result.emit({'code':0,'columns':df.columns, 'size':df.size})
        return
    def getImage(self, path):
        """Save a the scope screenshot to path. Emits the Result 
        signal which the MyApp class uses to display information. The scope instance 
        attribute must implement a getImage() method. 
        
        Args:
            path (str): A full path and filename.
        """
        image = self.scope.getImage()
        fid = open(path, 'wb')
        print(path)
        fid.write(image)
        fid.close()
        self.Result.emit({'code':1,'columns':None, 'size':None})
        return
    def fullCapture(self,path):
        """Save a the scope screenshot to path. Emits the Result 
        signal which the MyApp class uses to display information. The scope instance 
        attribute must implement a fullCapture() method. 
        
        Args:
            path (str): A full path and filename.
        """
        df = self.scope.fullCapture()
        df.to_csv(path_or_buf=path,index=False)
        columns = df.columns
        size = df.size
        self.Result.emit({'code':0,'columns':columns, 'size':size})
        return


class IPValidator(QValidator):
    def __init__(self, parent=None):
        QValidator.__init__(self, parent)
        return
    def validate(self, arg1, arg2):
        try:
            ip_address(arg1)
            return (QValidator.Acceptable, arg1, arg2)
        except ValueError:
            return (QValidator.Invalid, arg1, arg2)
        return (QValidator.Acceptable, arg1, arg2)
     
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())