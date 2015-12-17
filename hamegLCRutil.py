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

from PyQt4 import QtGui, Qt
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtCore import QObject, pyqtSlot, pyqtSignal
from PyQt4.Qwt5 import *
    
import numpy as np

import hamegLCR


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
    def __init__(self, xmin=None, xmax=None, logscale=False):
        super(LCRPlot, self).__init__()
        self.xmin = xmin
        self.xmax = xmax
        self.logscale = logscale
        
        self.colors = [Qt.darkCyan,Qt.darkGray,Qt.darkYellow]

        if self.logscale:
            self.setAxisScaleEngine(QwtPlot.xBottom,QwtLog10ScaleEngine())
        #self.setAxisOptions(QwtPlot.xBottom, QwtAutoScale.Logarithmic)
        
        #self.setAxisScale(QwtPlot.xBottom, hamegLCR.FREQ[0], hamegLCR.FREQ[-1]+hamegLCR.FREQ[-1]*0.01)
        if (xmin is not None) and (xmax is not None):
            self.setAxisScale(QwtPlot.xBottom, self.xmin, self.xmax)
        
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
        
        #after reploting set new zoomer base (the new rectangle can bo only as small as current canvas
        if (self.xmin is not None) and (self.xmax is not None):
            #self.zoomer.setZoomBase(QRectF(hamegLCR.FREQ[0],  self.ymin-delta, hamegLCR.FREQ[-1]+hamegLCR.FREQ[-1]*0.01-hamegLCR.FREQ[0], self.ymax+delta - (self.ymin-delta)))
            self.zoomer.setZoomBase(QRectF(self.xmin,  self.ymin-delta, self.xmax-self.xmin, self.ymax+delta - (self.ymin-delta)))
    
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


class DoubleSlider(QWidget):
    
    def __init__(self):
        super(DoubleSlider, self).__init__()
        self.slider1 = QSlider(Qt.Horizontal)
        #self.slider1.setInvertedAppearance(True)
        #self.slider1.setInvertedControls(True)
        self.slider2 = QSlider(Qt.Horizontal)

        """        
        self.setStyleSheet("\
        QSlider::handle:horizontal {\
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #b4b4b4, stop:1 #ffffff);\
        border: 1px solid #5c5c5c;\
        width: 18px;\
        color: red;\
        margin: -2px 0;\
        border-radius: 3px;\
        }  \
        QSlider::groove:horizontal {\
        border: 1px solid #bbb;\
        background: white;\
        height: 10px;\
        border-radius: 4px;\
        }  \
        QSlider::sub-page:horizontal {\
        background: transparent\
        border: 1px solid #777;\
        height: 10px;\
        border-radius: 4px;\
        }\
        ")
        """     
                
        self.slider1.valueChanged.connect(self.slider1__changed_slot)
        self.slider2.valueChanged.connect(self.slider1__changed_slot)
        #self.slider1.setTracking(False)
        #self.slider2.setTracking(False)
        self.initUI()
        
    def initUI(self):
        """Generates the GUI."""
        self.lyt = QtGui.QHBoxLayout()
        self.setLayout(self.lyt)
        
        self.lyt.addWidget(self.slider1)
        self.lyt.addWidget(self.slider2)
    
    @pyqtSlot()
    def slider1__changed_slot(self):
        s1 = self.slider1.value()
        s2 = self.slider2.value()
        
        if s1>s2:
            if self.sender() == self.slider1:
                self.slider2.setValue(s1)
            else:
                self.slider1.setValue(s2)
    
    @pyqtSlot()
    def slider2__changed_slot(self):
        s1 = self.slider1.value()
        s2 = self.slider2.value()
        
        if s1>s2:
            self.slider2.setValue(s1)
