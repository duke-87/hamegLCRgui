# Author: Andrej Debenjak -- andrej.debenjak@ijs.si
import sys
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
import imp

import hamegLCR
from hamegLCRutil import *

try:
    imp.find_module('openpyxl')
    imp.find_module('pandas')
    foundPandas = True
except ImportError:
    foundPandas = False

if foundPandas:
    import pandas
    
import numpy as np


DEVICE = '/dev/ttyUSB0'
#DEVICE = '/home/andrej/vmodem0
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
    
    def __init__(self):
        super(MainTab, self).__init__()
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
        #self.hameg = hamegLCR.HamegLCR(port='/home/andrej/vmodem0', timeout=5) #tty over socat
        self.hameg = hamegLCR.HamegLCR(port=DEVICE)
        
        self.sweepTimer = QTimer()
        self.sweepTimer.setSingleShot(True)
        self.sweepTimer.timeout.connect(self.sweepTimer_slot)

        self._sweepActive = False
        self.excelData = MeasurementData()

        self.initUI()
        
    def initUI(self):
        """Generates the GUI."""
        self.layout = QtGui.QVBoxLayout()
        self.setLayout(self.layout)
        
        # Create Alarm Group
        self.graphGrp = QGroupBox(self.tr('Measurements'))
        self.graphGrp_lyt = QVBoxLayout()
        self.graphGrp.setLayout(self.graphGrp_lyt)
        
        self.plot1 = LCRPlot()
        self.plot2 = LCRPlot()
        
        self.graphGrp_lyt.addWidget(self.plot1)
        self.graphGrp_lyt.addWidget(self.plot2)
        
        self.plot1.axisWidget(QwtPlot.yLeft).scaleDraw().setMinimumExtent(80)
        self.plot2.axisWidget(QwtPlot.yLeft).scaleDraw().setMinimumExtent(80)
        
        self.layout.addWidget(self.graphGrp)
        
        self.startBtn = QPushButton(self.tr('Start Sweep'))
        self.startBtn.clicked.connect(self.startSweep)
        
        self.saveBtn = QPushButton(self.tr('Save to File'))
        self.saveBtn.clicked.connect(self.saveToFile)
        
        self.sliderValue = QLineEdit()
        self.sliderValue.setDisabled(True)
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(1000, 10000)
        self.slider.setTickInterval(1000)
        self.slider.setPageStep(100)
        self.slider.valueChanged.connect(self.sliderValueChangeg_slot)
        self.slider.setValue(5000)
        self.slider.setToolTip(self.tr('Delay in milisecond between two measurements.'))
        
        self.cb = QComboBox()
        self.cb.activated.connect(self.modeCombo_slot)
        for idx in hamegLCR.MODE:
            self.cb.addItem(idx)
        
        mode = int(self.hameg.getMode())    
        self.cb.setCurrentIndex(mode)
        self.modeCombo_slot(mode)
        
        hbox = QHBoxLayout()
        hbox.addStretch(3)
        hbox.addWidget(self.slider,7)
        hbox.addWidget(self.sliderValue,1)
        hbox.addWidget(self.cb,1)
        hbox.addWidget(self.saveBtn)
        hbox.addWidget(self.startBtn,2)
        self.layout.addLayout(hbox)
    
    @pyqtSlot()
    def sliderValueChangeg_slot(self):
        self.sliderValue.setText(str(self.slider.value()))
    
    @pyqtSlot()
    def saveToFile(self):
        fdiag = QFileDialog()
        
        selectedFilter = QString()
        
        if foundPandas:
            filt = self.tr("Excel Open XML Document  .xlsx (*.xlsx);;Portable Network Graphics  .png (*.png)")
        else:
            filt = self.tr("Portable Network Graphics  .png (*.png)")
        
        fileName = fdiag.getSaveFileName(self.parentWidget(), self.tr("Save Data As"),
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
        
    @pyqtSlot()
    def sweepTimer_slot(self):
        
        if not self._sweepActive:
            return
        
        freq = hamegLCR.FREQ[self.sweepCnt]
        
        if self._sweepRead:
            self.graphGrp.setTitle(self.modeUtf + ' ' + self.tr('Measurements'))
            self.modeTuple = hamegLCR.MODE_TUPLE[self.modeIDX]
            
            x1 = self.hameg.getMainValue()
            self.plot1.setData(freq, x1)
            
            x2 = self.hameg.getSecondaryValue()
            self.plot2.setData(freq, x2)
            
            self.excelData.addMeasurement(freq, x1, x2)
            
        
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
        self.excelRowLabels = []

        self.sweepCnt = -1
        self.sweepTimer.start(10)

class MeasurementData(object):
    def __init__(self):
        super(MeasurementData, self).__init__()
        
        self.__data = None
    
    def addMeasurement(self, *args):
        if len(args) < 1:
            raise Exception('Function requires at least one argument, none provided.')
        
        data = np.array(args)

        if self.__data is None:
            self.__data = data
            return
        
        self.__data = np.vstack((self.__data, data))
    
    def getData(self):
        if self.__data is None:
            return np.array([])
        
        return self.__data
            
        
        

class FrequenciesTab(QtGui.QWidget):
    """Tab where the frequencies which are to be measured can be selected."""
    
    def __init__(self):
        super(FrequenciesTab, self).__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.initUI()
        
    def initUI(self):
        """Generates the GUI."""
        self.layout = QtGui.QVBoxLayout()
        self.setLayout(self.layout)
        
        # Create Group
        self.freqGrp = QGroupBox(self.tr('Frequencies'))
        self.freqGrp_lyt = QVBoxLayout()
        self.freqGrp.setLayout(self.freqGrp_lyt)
        self.layout.addWidget(self.freqGrp)
        
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
        
        self.layout.addStretch()
        
        self.checkBoxes = FreqCheckBoxes()     
        self.freqGrp_lyt.addWidget(self.checkBoxes)
    
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
        
        
class LCRPlot(QwtPlot):
    """
    Class for plotting the measured data.
    """
    def __init__(self):
        super(LCRPlot, self).__init__()
        
        self.colors = [Qt.darkCyan,Qt.darkGray,Qt.darkYellow]
        self.setAxisScaleEngine(QwtPlot.xBottom,QwtLog10ScaleEngine())
        #self.setAxisOptions(QwtPlot.xBottom, QwtAutoScale.Logarithmic)
        self.setAxisScale(QwtPlot.xBottom, hamegLCR.FREQ[0], hamegLCR.FREQ[-1]+hamegLCR.FREQ[-1]*0.01)
        self.ymax = 0
        self.ymin = 0
        
        self.zoomer = QwtPlotZoomer(self.canvas())                 
        self.zoomer.setRubberBandPen(QPen(Qt.black, 2, Qt.DotLine))
        #self.zoomer.setTrackerPen(QPen(Qt.black));
        
    def clearData(self):
        for pItem in self.itemList():
          pItem.detach()
        
        self.ymax = -1000000000000
        self.ymin = 1000000000000
        
        grid = QwtPlotGrid()
        grid.enableXMin(True)
        grid.enableYMin(True)
        grid.setMajPen(QPen(Qt.black, 0, Qt.DotLine))
        grid.setMinPen(QPen(Qt.gray, 0 , Qt.DotLine))
        grid.attach(self)
        
        self.replot()
     
    def setData(self, x, y):
        """Draws individual measurement on the graph."""
        
        m = QwtPlotMarker()
        
        m.setSymbol( QwtSymbol( QwtSymbol.Diamond, QBrush( Qt.red), QPen( Qt.green), QSize( 10, 10 ) ) )
        m.setValue( QPointF( x,y ) )
        m.attach( self )
        
        if y > self.ymax:
            self.ymax = y
            
        if y < self.ymin:
            self.ymin = y
                
        delta = (self.ymax -self.ymin)*0.02
        if delta==0:
            delta = 0.01*self.ymin
        self.setAxisScale(QwtPlot.yLeft, self.ymin-delta, self.ymax+delta)

        self.replot()
        
        #after reploting set new zoomer base (the new rectangle can bo only as big as current canvas
        self.zoomer.setZoomBase(QRectF(hamegLCR.FREQ[0],  self.ymin-delta, hamegLCR.FREQ[-1]+hamegLCR.FREQ[-1]*0.01-hamegLCR.FREQ[0], self.ymax+delta - (self.ymin-delta)))
    
class Frequencies(object):
    """Singletone object, which holds the list of frequencies that have been checked to measure.
       If any instance of this class exist, the constructor returns its reference.
    """ 
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Frequencies, cls).__new__(cls, *args, **kwargs)

        return cls._instance
    
    def __init__(self):
             
        if not self._initialized:
            super(Frequencies, self).__init__()
            self._initialized = True
            self.frequencies = {}
            for freq in hamegLCR.FREQ:
                self.frequencies[freq] = True
            

class FreqCheckBoxes(QWidget):
    def __init__(self):
        super(FreqCheckBoxes, self).__init__()
        self.fdict = Frequencies()
        self.initUI()      
            
    def initUI(self):
        self.lyt = QHBoxLayout()
        self.setLayout(self.lyt)
        
        self.boxes = []
        idx = 0
        for col in range(0,6):
            vbox = QVBoxLayout()
            self.lyt.addLayout(vbox)
            while True:
                #for line in range(0,12):
                if idx > 68:
                    vbox.addStretch()
                    break
                f = hamegLCR.FREQ[idx]
                
                if f >= 10**(col+1):
                    vbox.addStretch()
                    break
                
                cb = QCheckBox()
                cb.setText(str(f))
                cb.setChecked(self.fdict.frequencies[f])
                cb.stateChanged.connect(self.checkBoxChanged)
                vbox.addWidget(cb)
                self.boxes.append(cb)
                
                idx += 1

    @pyqtSlot(int)
    def checkBoxChanged(self, state):
        freq = int(self.sender().text())
        self.fdict.frequencies[freq] = self.sender().isChecked()
        #print freq
        #print self.sender().isChecked()


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
