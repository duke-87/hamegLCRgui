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

import time
import serial
import imp
#import os

try:
    imp.find_module('PyQt4')
    defQHamegLCR = True
except ImportError:
    defQHamegLCR = False


if defQHamegLCR:
    from PyQt4.QtCore import QObject, QThread, pyqtSlot
    from PyQt4.Qt import pyqtSignal
    import threading

FREQ = [20, 24, 25, 30, 36, 40, 45, 50, 60, 72, 75, 80,
        90, 100, 120, 150, 180, 200, 240,  250, 300, 360, 400, 450,
        500, 600, 720,  750,  800, 900,  1000, 1200, 1500, 1800, 2000, 2400,
        2500, 3000, 3600, 4000, 4500, 5000, 6000, 7200, 7500, 8000, 9000, 10000,
        12000, 15000, 18000, 20000, 24000, 25000, 30000, 36000, 40000, 45000, 50000, 60000,
        72000, 75000, 80000, 90000, 100000, 120000, 150000, 180000, 200000]

FREQ_REDUCED = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000]

MODE = ['AUTO', 'L-Q', 'L-R', 'C-D', 'C-R', 'R-Q', u'Z-\u03B8', u'Y+\u03B8', 'R+X', 'G+B', u'N+\u03B8', 'M']
MODE_ASCII = ['AUTO', 'L-Q', 'L-R', 'C-D', 'C-R', 'R-Q', 'Z-Theta', 'Y-Theta', 'R+X', 'G+B', 'N-Theta', 'M']
MODE_TUPLE = [['AUTO', 'AUTO'], ['L', 'Q'], ['L', 'R'], ['C', 'D'], ['C', 'R'], ['R', 'Q'], ['Z', 'Theta'], ['Y', 'Theta'], ['R', 'X'], ['G', 'B'], ['N', 'Theta'], ['M', 'xy']]

TRIGGER = ['Continuous', 'Manual', 'External']

RATE = ['Fast', 'Medium', 'Slow']
class HamegLCR:
    """
        :param port: Serial port.
        :type port: str
    """
       
    def __init__(self, port='/dev/ttyUSB0', timeout=2):
        
        try:
            self.dev = serial.Serial(port=port, baudrate=9600, bytesize=serial.EIGHTBITS,
                                parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, 
                                timeout=timeout, xonxoff=False, rtscts=False, 
                                writeTimeout=0.5, dsrdtr=False, 
                                interCharTimeout=None)
        except:
            raise Exception('Could not open serial port. Please specify the right port.')
        
        #apply new settings due
        #os.system('stty -F %s icrnl isig icanon iexten echo echoe echok echoctl echoke icrnl opost' % port)
        
        description = self.get_id()
        
        if 'HAMEG' in description:
            self.IDN = description
        else:
            raise Exception('Not a HAMEG device')
        
    def close(self):
        """Close serial connection with Hameg LCR."""
        self.dev.close()
        
    def write(self, string):
        self.dev.flushInput()
        self.dev.write(string + '\r\n')

    def read(self):
        #return self.dev.readline(eol='\r').strip() #not supported from 2.6 onwards
        return self._readline(eol='\r').strip() #workaround
    
    def _readline(self, size=None, eol='\r'):
        """read a line which is terminated with end-of-line (eol) character
        ('\n' by default) or until timeout."""
        leneol = len(eol)
        line = bytearray()
        while True:
            c = self.dev.read(1)
            if c:
                line += c
                if line[-leneol:] == eol:
                    break
                if size is not None and len(line) >= size:
                    break
            else:
                break
        return bytes(line)
    
    def get_id(self):
        self.write('*IDN?')
        return self.read()
    
    def setMode(self, mode):
        self.write('PMOD %s' % mode)
    
    def getMode(self):
        self.write('PMOD?')
        return self.read()
    
    def setTriggerMode(self, mode):
        self.write('MMOD %s' % mode)
    
    def getTriggerMode(self):
        self.write('MMOD?')
        return self.read()
    
    def setRate(self, mode):
        self.write('RATE %s' % mode)
    
    def getRate(self):
        self.write('RATE?')
        return self.read()
    
    def setFrequency(self, freq):
        if freq not in FREQ:
            raise Exception('Invalid frequency')
        
        self.write('FREQ %s' % freq)
        
    def triggerAndWait(self): 
        self.write('*TRG')
        self.write('*WAI')
    
    def getMainValue(self):
        self.write('XMAJ?')
        return self._getFloat()
        
    def getSecondaryValue(self):
        self.write('XMIN?')
        return self._getFloat()
        
    def _getFloat(self):
        x = self.read()
        try:
            x = float(x)
        except:
            #raise
            x = 0 #TODO implement logging
            print 'Could not convert to float...'#TODO implement logging
        
        return x

if defQHamegLCR:
    
    class QHamegLCR(QObject, HamegLCR):
        """ 
            Extension of the HamegLCR class. It enables a number of
            nonblocking functionalities by employing the Qt signal-slot
            mechanism. Note that even though the object is self moved in 
            its separate thread, direct calling of it methods does not execute
            in this thread but in the thread from which the method was called.
        """
        values_signal = pyqtSignal(float, float)
        
        def __init__(self, *args, **kwargs):
            self.__lock = threading.Lock()
            
            QObject.__init__(self)
            HamegLCR.__init__(self, *args, **kwargs)
            
            self._thread = QThread()
            self._thread.start()
            
            self.moveToThread(self._thread)
       
        @pyqtSlot()
        def nonblockingGetValues(self):
            self.triggerAndWait()
                
            x1 = self.getMainValue()
            x2 = self.getSecondaryValue()
            
            self.values_signal.emit(x1, x2)
            
        def read(self):
            self.__lock.acquire()
            val = HamegLCR.read(self)
            self.__lock.release()
            return val
        
        def write(self, string):
            self.__lock.acquire()
            HamegLCR.write(self, string)
            self.__lock.release()        
    
def main():
    
    PORT = '/dev/ttyUSB0'
    #PORT = 'COM27'
    
    try:
        print 'Trying to connect through serial port: %s' % PORT
        hameg = HamegLCR(port=PORT)
    except:
        print 'Could not connect to the LCR Bridge.'
        print 'Please specify the right serial port.'
        return
    
    print 'Connected to: %s' % hameg.IDN
    print 'The bridge is in the %s mode.' % MODE_ASCII[int(hameg.getMode())]
    print 'Main value: %s' % hameg.getMainValue()
    print 'Secondary value: %s' % hameg.getSecondaryValue()
    
    hameg.close()


if __name__ == '__main__':
  main()    
