#    hamegLCRgui - GUI for automated measurements with Hameg LCR Bridge
#    Copyright (C) 2015  Andrej Debenjak (andrej.debenjak@ijs.si)
#
#    This file is part of hamegLCRgui.
#
#    hamegLCRgui is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    hamegLCRgui is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import imp
import time
from datetime import datetime
import logging
import traceback
from PyQt4 import QtGui, Qt
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtCore import QObject, pyqtSlot, pyqtSignal
from PyQt4.Qwt5 import *
from PyQt4.Qt import QFileDialog, QRect

import hamegLCR
from hamegLCRutil import *

import numpy as np

try:
    imp.find_module('openpyxl')
    imp.find_module('pandas')
    foundPandas = True
except ImportError:
    foundPandas = False

if foundPandas:
    import pandas

DEVICE = '/dev/ttyUSB0'
#DEVICE = '/home/andrej/vmodem0'
#DEVICE = 'COM27'

class MainGUI(QWidget):
    """A GUI for contolling a Hameg LCR Programmable Bridge and performing automated measurements."""
    
    def __init__(self):
        super(MainGUI, self).__init__()
        self.log = logging.getLogger("GUI")
        
        #self.showFullScreen()
        self.setGeometry(0, 0, 1280, 1024)
        self.show()
        #self.centerOnScreen()
            
        self.initUI()

    @pyqtSlot()
    def goHome(self):
        """PyQt slot for quick access to the Main Page tab.""" 
        self.allTabs.setCurrentIndex(0)  
    
    def closeEvent(self, event):
        """Overloaded *closeEvent* which enables confirmation message box for closing.""" 
        self.confirmDialog.setDefaultButton(QMessageBox.Cancel)
        self.confirmDialog.exec_()
        if self.confirmDialog.result() != QMessageBox.Ok:
            event.ignore()
        else:
            self.mainTab.hameg.close()
        #return QtGui.QWidget.closeEvent(self, event)
              
    def initUI(self):
        """Generates the GUI."""
        
        self.confirmDialog = QMessageBox()
        self.confirmDialog.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        self.confirmDialog.setIcon(QMessageBox.Question)
        self.confirmDialog.setWindowTitle(self.tr('Confirm Exit'))
        self.confirmDialog.setText(self.tr('Exit LCR Bridge Software?'))
        #self.confirmDialog.finished.connect(self.exit_application_slot)
        #self.confirmDialog.exec_()
        '''----------------------------------------------------------------------------
        --------------------------   GUI Header    ------------------------------------
        ----------------------------------------------------------------------------'''
        # LOGOs
        hHeader = QtGui.QHBoxLayout()
        
        self.logo = QtGui.QLabel('LCR Bridge GUI')
        #logo = QPixmap(':/no_log.svg')
        #self.logo.setPixmap(logo)
        
        hHeader.addStretch()
        hHeader.addWidget(self.logo)
        
        '''----------------------------------------------------------------------------
        --------------------------   GUI Footer    ------------------------------------
        ----------------------------------------------------------------------------'''
        hboxBottom = QtGui.QHBoxLayout()
        self.exitBtn = QtGui.QPushButton(self.tr('EXIT'))
        #self.exitBtn.clicked.connect(QCoreApplication.instance().quit)
        #self.exitBtn.clicked.connect(self.confirmDialog.exec_)
        self.exitBtn.clicked.connect(self.close)
        self.homeBtn = QtGui.QPushButton(self.tr('Main Page'))
        self.homeBtn.clicked.connect(self.goHome)
        
        hboxBottom.addWidget(self.exitBtn)
        hboxBottom.addWidget(self.homeBtn)
        hboxBottom.addStretch()
           
        '''----------------------------------------------------------------------------
        --------------------------       TABS      ------------------------------------
        ----------------------------------------------------------------------------'''
        self.allTabs = QtGui.QTabWidget()
        
        # Creation of the MAIN tab
        self.mainTab = MainTab()
        self.freqTab = FrequenciesTab()
        
        # PUT all the pages into the QTabWidget
        self.allTabs.addTab(self.mainTab,self.tr('Main Page'))
        self.allTabs.addTab(self.freqTab,self.tr('Settings'))
        
        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(hHeader)
        vbox.addWidget(self.allTabs)
        vbox.addLayout(hboxBottom)
        
        self.setLayout(vbox)
        
        
class MainTab(QtGui.QWidget):
    """*Home page* of the GUI."""
    
    getValues_trigger = pyqtSignal()
    
    def __init__(self):
        super(MainTab, self).__init__()
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.hameg = hamegLCR.QHamegLCR(port=DEVICE, timeout=5)
        self.getValues_trigger.connect(self.hameg.nonblockingGetValues)
        self.hameg.values_signal.connect(self.newMeasurements_slot)
        
        self.sweepTimer = QTimer()
        self.sweepTimer.setSingleShot(True)
        self.sweepTimer.timeout.connect(self.sweepTimer_slot)

        self._sweepActive = False
        self.excelData = MeasurementData()

        self.initUI()
        
    def initUI(self):
        """Generates the GUI."""
        self.lyt = QtGui.QVBoxLayout()
        self.setLayout(self.lyt)
        
        # Create Alarm Group
        self.graphGrp = QGroupBox(self.tr('Measurements'))
        self.graphGrp_lyt = QVBoxLayout()
        self.graphGrp.setLayout(self.graphGrp_lyt)
        
        self.plot1 = LCRPlot(xmin=hamegLCR.FREQ[0], xmax=hamegLCR.FREQ[-1]+hamegLCR.FREQ[-1]*0.01, logscale=True)
        self.plot2 = LCRPlot(xmin=hamegLCR.FREQ[0], xmax=hamegLCR.FREQ[-1]+hamegLCR.FREQ[-1]*0.01, logscale=True)
        
        self.plot3 = LCRPlot()
        self.plot4 = LCRPlot()
        
        self.graphGrp_lyt.addWidget(self.plot1)
        self.graphGrp_lyt.addWidget(self.plot2)
        
        self.plot1.axisWidget(QwtPlot.yLeft).scaleDraw().setMinimumExtent(80)
        self.plot2.axisWidget(QwtPlot.yLeft).scaleDraw().setMinimumExtent(80)
        
        self.lyt.addWidget(self.graphGrp)
        
        self.startBtn = QPushButton(self.tr('Start Sweep'))
        self.startBtn.clicked.connect(self.startSweep)
        
        self.saveBtn = QPushButton(self.tr('Save to File'))
        self.saveBtn.clicked.connect(self.saveToFile)
        
                
        self.testBtn = QtGui.QPushButton(self.tr('Test'))
        self.testBtn.clicked.connect(self.test)
        self.tt = True
        
        self.sliderValue = QLineEdit()
        self.sliderValue.setDisabled(True)
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.valueChanged.connect(self.sliderValueChangeg_slot)
        self.slider.setRange(0, 10000)
        self.slider.setTickInterval(1000)
        #self.slider.setTickPosition(QSlider.TicksBothSides)
        self.slider.setPageStep(100)
        #self.slider.setSingleStep(50)
        
        self.slider.setValue(1)
        self.slider.setValue(0)
        self.slider.setToolTip(self.tr('Additional delay in milisecond between measurements.'))
        
        self.cb = QComboBox()
        self.cb.setToolTip(self.tr('Measurement Mode'))
        self.cb.activated.connect(self.modeCombo_slot)
        for idx in hamegLCR.MODE:
            self.cb.addItem(idx)
        
        mode = int(self.hameg.getMode())    
        self.cb.setCurrentIndex(mode)
        self.modeCombo_slot(mode)
        
        self.trigCbox = QComboBox()
        self.trigCbox.setToolTip(self.tr('Trigger Mode'))
        self.trigCbox.activated.connect(self.trigModeCombo_slot)
        for idx in hamegLCR.TRIGGER:
            self.trigCbox.addItem(idx)
        
        mode = int(self.hameg.getTriggerMode())    
        self.trigCbox.setCurrentIndex(mode)
        self.trigModeCombo_slot(mode)
        
        self.rateCbox = QComboBox()
        self.rateCbox.setToolTip(self.tr('Measurement Speed'))
        self.rateCbox.activated.connect(self.rateCombo_slot)
        for idx in hamegLCR.RATE:
            self.rateCbox.addItem(idx)
        
        mode = int(self.hameg.getRate())    
        self.rateCbox.setCurrentIndex(mode)
        self.rateCombo_slot(mode)
        
        
        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self.slider,7)
        hbox.addWidget(self.sliderValue,2)
        hbox.addWidget(self.rateCbox,1)
        hbox.addWidget(self.trigCbox,1)
        hbox.addWidget(self.cb,1)
        hbox.addWidget(self.saveBtn)
        hbox.addWidget(self.startBtn,2)
        #hbox.addWidget(self.testBtn,2)
        self.lyt.addLayout(hbox)
    
    @pyqtSlot()
    def test(self):
        if self.tt:
            #self.lyt.removeWidget(self.graphGrp)
            print self.graphGrp_lyt.count()
            self.graphGrp_lyt.removeWidget(self.plot1)
            self.plot1.setParent(None)
            self.graphGrp_lyt.removeWidget(self.plot2)
            self.plot2.setParent(None)
            print self.graphGrp_lyt.count()
            
        else:
            self.graphGrp_lyt.addWidget(self.plot3)
            self.graphGrp_lyt.addWidget(self.plot4)
            
        self.tt = not self.tt
        
    @pyqtSlot()
    def sliderValueChangeg_slot(self):
        self.sliderValue.setText(str(self.slider.value()))
    
    @pyqtSlot()
    def saveToFile(self):
        fdiag = QFileDialog()
        
        selectedFilter = QString()
        
        if foundPandas:
            filt = self.tr("Excel Open XML Document (*.xlsx);;Portable Network Graphics (*.png)")
        else:
            filt = self.tr("Portable Network Graphics (*.png)")

        fileName = fdiag.getSaveFileName(self, self.tr("Save Data As"),
                                        datetime.now().strftime('%Y-%m-%d-T%H%M%S-') + self.modeAscii,
                                        filt, selectedFilter)
        
        if len(fileName) == 0:
            return
        
        if 'png' in  selectedFilter:
            if fileName[-4:] == '.png':
                fileName = fileName[0:-4]
            
            px =  QPixmap.grabWidget(self.graphGrp)
            px.save(fileName + '.png', "PNG")
            return
        
        if fileName[-5:] == '.xlsx':
                fileName = fileName[0:-5]
        
        data = self.excelData.getData()
        if len(data) == 0:
            mb = QMessageBox()
            mb.setIcon(QMessageBox.Warning)
            mb.setWindowTitle(self.tr('Warning'))
            mb.setText(self.tr('No data exists. No output file has been produced.'))
            mb.exec_()
            return
        
        
        if data.ndim == 1: #Bad workaround if only one line exists
            add = []
            for idx in range(0,len(data)):
                add.append(0)
            data = np.vstack((data, np.array(add)))

        df = pandas.DataFrame(data, columns=['Frequency', self.modeTuple[0], self.modeTuple[1]])
        df.to_excel(str(fileName) + '.xlsx', index=False)
               
    @pyqtSlot(int)
    def modeCombo_slot(self, mode):
        self.hameg.setMode(mode)
        
        self.modeAscii = hamegLCR.MODE_ASCII[mode]
        self.modeUtf = hamegLCR.MODE[mode]
        self.modeIDX = mode
        
    @pyqtSlot(int)
    def trigModeCombo_slot(self, mode):
        self.hameg.setTriggerMode(mode)
    
    @pyqtSlot(int)
    def rateCombo_slot(self, mode):
        self.hameg.setRate(mode)
        
    @pyqtSlot()
    def sweepTimer_slot(self):
        
        if not self._sweepActive:
            return
        
        freq = hamegLCR.FREQ[self.sweepCnt]
        
        if not self._sweepRead:
            self.trigCbox.setCurrentIndex(1) #set manual mode
            
        if self._sweepRead:
            self.graphGrp.setTitle(self.modeUtf + ' ' + self.tr('Measurements'))
            self.modeTuple = hamegLCR.MODE_TUPLE[self.modeIDX]
            
            self.getValues_trigger.emit()
        
        if self.sweepCnt == -1:
            self.setNextFrequency()
            
    @pyqtSlot(float, float)
    def newMeasurements_slot(self, x1, x2):
        freq = hamegLCR.FREQ[self.sweepCnt]
        
        self.plot1.setData(freq, x1)
        self.plot2.setData(freq, x2)
        
        self.excelData.addMeasurement(freq, x1, x2)
        
        self.setNextFrequency()
    
    def setNextFrequency(self):
        freq = hamegLCR.FREQ[self.sweepCnt]
        
        self.sweepCnt += 1
        
        fdict = Frequencies()
        
        while self.sweepCnt < len(hamegLCR.FREQ):
            freq = hamegLCR.FREQ[self.sweepCnt]
            if not fdict.frequencies[freq]:
                self.sweepCnt += 1
            else:
                break
            
        if self.sweepCnt == len(hamegLCR.FREQ):
            self._sweepActive = False
            self.startBtn.setText(self.tr('Start Sweep'))
            return
        
        self.hameg.setFrequency(freq)
        
        if not self._sweepRead:
            #dummy read, otherwise it happens, that old value is read 
            self.hameg.triggerAndWait()
            self.hameg.getMainValue()
        
        self._sweepRead = True    
        
        self.sweepTimer.start( self.slider.value())

    @pyqtSlot()
    def startSweep(self):
        
        if self._sweepActive:
            self._sweepActive = False
            self.startBtn.setText(self.tr('Start Sweep'))
            return
        
        self.startBtn.setText(self.tr('Stop Sweep'))
        self._sweepActive = True
        self._sweepRead = False
        
        self.plot1.clearData()
        self.plot2.clearData()
        
        self.excelData = MeasurementData()

        self.sweepCnt = -1
        self.sweepTimer.start(10)

class FrequenciesTab(QtGui.QWidget):
    """Tab where the frequencies which are to be measured can be selected."""
    
    def __init__(self):
        super(FrequenciesTab, self).__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.initUI()
        
    def initUI(self):
        """Generates the GUI."""
        self.lyt = QtGui.QVBoxLayout()
        self.setLayout(self.lyt)
        
        self.buttonFreq = QRadioButton(self.tr('Frequency Sweep'))
        self.buttonFreq.setChecked(True)
        self.buttonBias = QRadioButton(self.tr('Bias Sweep'))
        
        self.buttonExcGroup = QButtonGroup()
        self.buttonExcGroup.setExclusive(True)
        
        self.buttonExcGroup.addButton(self.buttonFreq, 0)
        self.buttonExcGroup.addButton(self.buttonBias, 1)
        
        self.selectGropu = QGroupBox(self.tr('Sweep Mode'))
        self.selectGropuLyt = QVBoxLayout()
        self.selectGropu.setLayout(self.selectGropuLyt)
        
        self.selectGropuLyt.addWidget(self.buttonFreq)
        self.selectGropuLyt.addWidget(self.buttonBias)
        
        self.lyt.addWidget(self.selectGropu)
        
        self.buttonExcGroup.buttonClicked.connect(self.sweep_mode_slot)

        
        # Create Group
        self.freqGrp = QGroupBox(self.tr('Frequencies'))
        self.freqGrp_lyt = QVBoxLayout()
        self.freqGrp.setLayout(self.freqGrp_lyt)
        self.lyt.addWidget(self.freqGrp)
        
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.freqGrp_lyt.addLayout(buttons)
        
        self.reducedBtn = QPushButton(self.tr('Reduced Set'))
        self.reducedBtn.clicked.connect(self.onlyReduced)
        buttons.addWidget(self.reducedBtn)
        
        self.clearBtn = QPushButton(self.tr('Select/Deselect All'))
        self._clearAll = True
        self.clearBtn.clicked.connect(self.clearAll)
        buttons.addWidget(self.clearBtn)
        
        self.lyt.addStretch()
        
        self.checkBoxes = FreqCheckBoxes()     
        self.freqGrp_lyt.addWidget(self.checkBoxes)
    
    @pyqtSlot(QAbstractButton)
    def sweep_mode_slot(self, button):
        checked_id = self.buttonExcGroup.checkedId()
        print 'Not implemented'
        if checked_id == 0:
            pass
        
    @pyqtSlot()
    def clearAll(self):
        self._clearAll = not self._clearAll
        
        for box in self.checkBoxes.boxes:
            box.setChecked(self._clearAll)
    
    @pyqtSlot()
    def onlyReduced(self):
        
        for box in self.checkBoxes.boxes:
            if int(box.text()) in hamegLCR.FREQ_REDUCED:
                box.setChecked(True)
            else:
                box.setChecked(False)
        

def main():
    #logging.basicConfig(filename='hamegLCRgui.log',level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    #logger = logging.getLogger()
    #logger.setLevel(logging.DEBUG)
    
    app = QApplication(sys.argv)
    
    gui = MainGUI()
    
    try:
        sys.exit(app.exec_())
    except:
        ex, val, tb = sys.exc_info()
        traceback.print_exception(ex, val, tb)
        

if __name__ == '__main__':
  main()    
