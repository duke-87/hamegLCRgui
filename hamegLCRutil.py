# Author: Andrej Debenjak -- andrej.debenjak@ijs.si
from PyQt4 import QtGui, Qt
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtCore import QObject, pyqtSlot, pyqtSignal
from PyQt4.Qwt5 import *
    
import numpy as np


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

