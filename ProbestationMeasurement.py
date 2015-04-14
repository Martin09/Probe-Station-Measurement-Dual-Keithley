# -*- coding: utf-8 -*-
"""
Created on Tue Mar 17 10:05:31 2015

@author: Martin Friedl
"""
#TODO: implement median and digital filtering
#TODO: come up with a better data file format (include all the settings)

# for command-line arguments
import sys
import os.path
from time import sleep,time
import datetime
from random import randint
# Python Qt4 bindings for GUI objects
from PyQt4 import QtCore,QtGui, uic
# Numpy functions for image creation
import numpy as np
# Pandas for manipulating datasets
import pandas as pd
# Scipy Signal library for Savitzky-Golay filtering of data
import scipy.signal
# Matplotlib Figure object
#from matplotlib.figure import Figure
# import the Qt4Agg FigureCanvas object, that binds Figure to
# Qt4Agg backend. It also inherits from QWidget
#from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar

from KeithleyDevice import Keithley
from saveLoadGUI import guirestore, guisave
    
#Dictionaries used for keithley settings        
dict_Is = {"25 uA":25e-6,"250 uA":250e-6,"2.5 mA":2.5e-3}
dict_Vs = {"10 V":10,"50 V":50,"500 V":500}
dict_Im = {"2 nA":2e-9,"20 nA":20e-9,"200 nA":200e-9,"2 uA":2e-6,"20 uA":20e-6,"200 uA":200e-6,"2 mA":2e-3}
#Dictionaries used for the plot settings
dict_linestyle = {0:'-',1:'--',2:'-.',3:':',4:''}
dict_markerstyle = {0:'.',1:'o',2:'+',3:'.',4:'1',5:'2',6:'3',7:'4',8:''}
dict_linecolour = {0:'b',1:'g',2:'r',3:'c',4:'m',5:'y',6:'k',7:'w'}

#Allows for the program to be run without a connected keithley (generates random dummy data)
testing = True

class MyWindow(QtGui.QMainWindow):
    def __init__(self):
        super(MyWindow, self).__init__()
        uic.loadUi('ProbestationMeasurementGUI.ui', self)
        
        self.setpoints_Vgs = None
        self.setpoints_Vds = None
        self.tabledata = []
        self.headers = ['Vgs','Vds','Ids','Resistance','Power','Time']
        self.units = ['V','V','A','Ohms','W','s']
        
        self.lastPlotUpdate = 0
        self.plotUpdatePeriod = 0.1 #Update plot no faster than once every 100ms
        
        #Add NavigationToolbar
        self.mplwidget.figure.set_dpi(150)
        self.mplwidget.mpl_toolbar = NavigationToolbar(self.mplwidget.figure.canvas, self.mplwidget)
        self.verticalPlotLayout.setDirection(QtGui.QBoxLayout.BottomToTop)
        self.verticalPlotLayout.addWidget(self.mplwidget.mpl_toolbar,1)
        self.mplwidget.myplot = self.mplwidget.figure.add_subplot(111)           
        
        #Connect signals from the GUI
        self.pbStartMeasure.clicked.connect(self.startMeasSlot)
        self.pbLoadIV_Vgs.clicked.connect(self.loadIV_VgsSlot)
        self.pbLoadIV_Vds.clicked.connect(self.loadIV_VdsSlot)        
        self.cbXAxis.currentIndexChanged.connect(self.updatePlot)
        self.cbYAxis.currentIndexChanged.connect(self.updatePlot)        
        self.cbLineStyle.currentIndexChanged.connect(self.updatePlot)      
        self.cbMarkerStyle.currentIndexChanged.connect(self.updatePlot)
        self.cbPlotColour.currentIndexChanged.connect(self.updatePlot)           
        self.pbSave.clicked.connect(self.saveGUISlot)
        self.pbLoad.clicked.connect(self.loadGUISlot)
        self.pbSaveDF.clicked.connect(self.saveDataFileSlot)

        #Add validators to the line edit inputs
        NPLCValidator = QtGui.QDoubleValidator()
        NPLCValidator.setRange(0.01,50)
        self.leNPLC.setValidator(NPLCValidator)
        
        pointsValidator = QtGui.QIntValidator()
        pointsValidator.setBottom(1)
        self.leNppSP.setValidator(pointsValidator)
        
        delayValidator=QtGui.QIntValidator()
        delayValidator.setBottom(0)
        self.ledelay_SPs.setValidator(delayValidator)
        self.ledelay_trig.setValidator(delayValidator)
        
        #Try to restore previous settings, if it fails then don't worry about it
        try:
            guirestore(self,QtCore.QSettings('startup.init', QtCore.QSettings.IniFormat))         
            self.setpoints_Vds = np.loadtxt(self.leIVFile_Vds.text(), comments="#", delimiter="\t", unpack=False)        
            self.setpoints_Vgs = np.loadtxt(self.leIVFile_Vgs.text(), comments="#", delimiter="\t", unpack=False)        

        except:
            pass
        
        #Populate the comboboxes for plotting
        self.cbXAxis.clear()
        self.cbXAxis.addItems(self.headers)
        self.cbYAxis.clear()        
        self.cbYAxis.addItems(self.headers)          
                
    def saveGUISlot(self):
        filename = QtGui.QFileDialog.getSaveFileName(self, 'Choose filename to save settings as', '.', filter='*.ini')        
        guisave(self,QtCore.QSettings(filename, QtCore.QSettings.IniFormat))

    def loadGUISlot(self):
        filename = QtGui.QFileDialog.getOpenFileName(self, 'Choose settings file to load', '.', filter='*.ini')                
        guirestore(self,QtCore.QSettings(filename, QtCore.QSettings.IniFormat)) 
                
    def startMeasSlot(self):

        dataFilename = self.leDataFile.text()        
        while os.path.isfile(dataFilename):
                overwrite_msg = "The data file exists, are you sure you want to overwrite it?"
                reply = QtGui.QMessageBox.question(self, 'Overwrite data file?', 
                     overwrite_msg, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No,QtGui.QMessageBox.Cancel)
                if reply == QtGui.QMessageBox.Yes:
                    break #User wants to overwrite the file
                elif reply == QtGui.QMessageBox.No:
                    self.saveDataFileSlot() #Allow user to change filename
                    dataFilename = self.leDataFile.text()
                else:
                    self.finishedMeasurement()
                    return
            
        self.Address = 12
        self.timeout = 100  
        self.NPLC = float(self.leNPLC.text())
        self.IgsRange = 25e-6
        self.VgsRange = 50
        self.ImRange = dict_Im[self.cbCurrentRang.itemText(self.cbCurrentRang.currentIndex())]
        self.delay_init = 10 #TODO: Add this to GUI
        self.N_meas = 1
        self.N_vgsSPs = len(self.setpoints_Vgs) 
        self.delay_SP = float(self.ledelay_SPs.text())/1000.
        self.N_ppSP = int(self.leNppSP.text())
        self.delay_trig = float(self.ledelay_trig.text())/1000.
        self.verbose = self.cbVerbose.isChecked()
        self.zeroCheck = self.cbZChk.isChecked()
        self.displayOff = self.cbDisplayOff.isChecked()
        
        keithley_vgs=Keithley(address="GPIB::%d"%self.Address,
                          timeout=self.timeout,
                          NPLC=self.NPLC,
                          VsRange=self.VgsRange,
                          IsRange=self.IgsRange,
                          ImRange=self.ImRange,
                          delay_init=self.delay_init,
                          setpoints=self.setpoints_Vgs,
                          N_SPs=self.N_vgsSPs,
                          delay_SP=self.delay_SP,
                          N_ppSP=self.N_ppSP,
                          delay_trig=self.delay_trig,
                          verbose=self.verbose,
                          zeroCheck=self.zeroCheck,
                          displayOff=self.displayOff,
                          logfunc=self.outToScr)
        self.Address2 = 24
        self.VdsRange = dict_Vs[self.cbVoltRang.itemText(self.cbVoltRang.currentIndex())]
        self.IdsRange = dict_Is[self.cbCurrentLim.itemText(self.cbCurrentLim.currentIndex())]
        self.N_vdsSPs=len(self.setpoints_Vds)         
        
        keithley_vds=Keithley(address="GPIB::%d"%self.Address,
                          VsRange=self.VdsRange,
                          IsRange=self.IdsRange,
                          delay_init=self.delay_init,
                          setpoints=self.setpoints_Vds,
                          N_SPs=self.N_vdsSPs,
                          verbose=self.verbose,
                          zeroCheck=self.zeroCheck,
                          displayOff=self.displayOff,
                          logfunc=self.outToScr)
        
        self.tabledata = []        
        self.initDataFile(dataFilename) #Write headers to output file
        
        tablemodel = MyTableModel(self.tabledata,self.headers,self)
        self.tvData.setModel(tablemodel)
              
        self.measThread = MeasurementThread(keithley_vgs,keithley_vds,dataFilename)
        self.connect(self.measThread, QtCore.SIGNAL("updateGUI"), self.updateThings)
        self.connect(self.measThread, QtCore.SIGNAL("measFinished"), self.finishedMeasurement)
        self.measThread.start()
#        self.measThread.run()#For debugging      

    def updatePlot(self):
        if not(hasattr(self, 'measThread')): #Check if the measurement thread exists
            return
        if (time()-self.lastPlotUpdate)<self.plotUpdatePeriod:
            return
        
        plotdat = np.array(self.tabledata)
        pltXData = plotdat[:,self.cbXAxis.currentIndex()]
        pltYData = plotdat[:,self.cbYAxis.currentIndex()]         
        
#        self.mplwidget.myplot.cla()
        marker = dict_markerstyle[self.cbMarkerStyle.currentIndex()]
        linestyle = dict_linestyle[self.cbLineStyle.currentIndex()]
        colour = dict_linecolour[self.cbPlotColour.currentIndex()]        
        
        self.mplwidget.myplot.plot(pltXData,pltYData,marker=marker,linestyle=linestyle,color=colour)
        self.mplwidget.myplot.set_xlabel(self.headers[self.cbXAxis.currentIndex()]+" ("+self.units[self.cbXAxis.currentIndex()]+")")
        self.mplwidget.myplot.set_ylabel(self.headers[self.cbYAxis.currentIndex()]+" ("+self.units[self.cbYAxis.currentIndex()]+")")
        self.mplwidget.myplot.ticklabel_format(style='sci', axis='y', scilimits=(-2,2))
        self.mplwidget.myplot.ticklabel_format(style='sci', axis='x', scilimits=(-2,2))
#TODO:Implement waferID etc.        self.mplwidget.myplot.set_title(self.fileInfo['Wafer']+" "+self.fileInfo['Device ID']+" Exp:"+self.fileInfo['Measurement'])        
        self.mplwidget.myplot.grid()
        self.mplwidget.figure.canvas.draw()
        
        #Reset the toolbar home button for the new plot
        self.mplwidget.mpl_toolbar._views.clear()
        self.mplwidget.mpl_toolbar._positions.clear()
        
        self.lastPlotUpdate = time()        
        
    def initDataFile(self,filename):
        with open(filename, 'w') as f:
            f.write("# Created by ProbestationMeasurement - Martin Friedl\n")
            f.write("# "+datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')+"\n")
            f.write('# Delay(init): %i' % self.delay_init)
            f.write('ms, delay(after set): %i' % self.delay_SP)
            f.write('ms, delay(bef.read): %i' % self.delay_trig)
            f.write('ms, np. of points: %i' % self.N_ppSP)
            f.write('ms, np. of measurements: %i' % self.N_meas)
            f.write(', np. of setpoints: %i' % self.N_vdsSPs)
            f.write(', %i' % self.N_vgsSPs+'\n'+'\n')
            f.write('# LifeTest\n')
            f.write('# Read Device 0 - KEITHLEY INSTRUMENTS INC.,MODEL 6487,1215030,A06   Jun 20 2006 15:08:40/A02  /C/G@GPIB0::22,  --\n')
            f.write('# Read Device 1 - KEITHLEY INSTRUMENTS INC.,MODEL 6487,1169708,A06   Jun 20 2006 15:08:40/A02  /C/F@GPIB0::12,  --\n')
            f.write('# Set Device 0 - KEITHLEY INSTRUMENTS INC.,MODEL 6487,1169708,A06   Jun 20 2006 15:08:40/A02  /C/F@GPIB0::12,  --\n')
            f.write('Vgs	Vds	Is	t\n')
            f.write('V	V	A	s\n')
            f.write('K6487/K6517A	K6487/K6517A	K6487/K6517A	time\n')
        
    #Output function for debugging keithley commands        
    def outToScr(self,message):
        print message        

    def loadIV_VgsSlot(self):
        filename = QtGui.QFileDialog.getOpenFileName(self, 'Choose IV file to load', '.', filter='*.iv')
        if filename == "":
            return
        self.leIVFile_Vgs.setText(filename)
        self.setpoints_Vgs = np.loadtxt(filename, comments="#", delimiter="\t", unpack=False)

    def loadIV_VdsSlot(self):
        filename = QtGui.QFileDialog.getOpenFileName(self, 'Choose IV file to load', '.', filter='*.iv')
        if filename == "":
            return
        self.leIVFile_Vds.setText(filename)
        self.setpoints_Vds = np.loadtxt(filename, comments="#", delimiter="\t", unpack=False)        
        
        
    def saveDataFileSlot(self):
        filename = QtGui.QFileDialog.getSaveFileName(self, 'Choose filename to save data as', '.', filter='*.dat')
        if filename == "":
            return
        self.leDataFile.setText(filename) 
        
    #This gets called when user tries to exit the program
    def closeEvent(self, event): 
        guisave(self,QtCore.QSettings('startup.init', QtCore.QSettings.IniFormat))#Save current settings for next time the program runs
        event.accept() # let the window close   

    def finishedMeasurement(self): #Gets called once the measurement thread finishes executing
        self.pbStartMeasure.setChecked(False)
        
    def updateThings(self): #Gets called from the measurement thread after every data point is collected
        #Update data table
        while len(self.measThread.dat)>0:
            self.tabledata.append(self.measThread.dat.pop(0))
        self.tvData.model().layoutChanged.emit()
        #Update data plot
        self.updatePlot()

#Thread which performs the keithely measurements in the background, allowing the GUI to be used during the measurement
class MeasurementThread(QtCore.QThread):
#class MeasurementThread(): #For debugging   
    def __init__(self,keithley1,keithley2,datFilename):
        QtCore.QThread.__init__(self)
        self.keithley1 = keithley1
        self.keithley2 = keithley2
        self.datFilename = datFilename
        self.dat = []
        
    def __del__(self):
        self.wait()
 
    #Gets called when the thread starts
    def run(self):
        self.keithley1.initialize()
        self.keithley2.initialize()
        sleep(self.keithley1.__delay_init__/1000.)
        self.keithley1.start()
        self.keithley2.start()
        self.measure(self.keithley1,self.keithley2,self.datFilename)
        self.keithley1.close()
        self.keithley2.close()
        print "Done!"

    def measure(self,keithley1,keithley2,filename):
        self.dat = []
        with open(filename, 'a') as f:
            time_start = time()            
            for j in xrange(keithley2.__N_SPs__):
                keithley2.setVs(float(keithley2.__setpoints__[j]))    # Set the voltage source
                readStr = keithley2.ask("READ?") 
                if testing:
                    meas = [time(),randint(1,100),j]                   
                else:
                    meas=keithley2.parseData(readStr)
                    if np.isnan(meas[2]):
                        print "Warning: Keithley Compliance"                   
                VdsSet = meas[2]            
                for i in xrange(keithley1.__N_SPs__):
                    keithley1.setVs(float(keithley1.__setpoints__[i]))    # Set the voltage source
                    sleep(keithley1.__delay_SP__)                         # Wait for the defined amount of time
                    readStr = keithley1.ask("READ?")                      # Measure the current
                    time_now = time()
                    if testing:
                        meas = [time(),randint(1,100),time()-time_start]                   
                    else:
                        meas=keithley1.parseData(readStr)
                        meas[:,1] = time_now-time_start
                        if np.isnan(np.array([meas]).T[0]).any():
                            print "Warning: Keithley Overflow"
                        if np.isnan(np.array([meas]).T[2]).any():
                            print "Warning: Keithley Compliance"
                    if isinstance(meas[0], list):
                        meas = [line.extend([VdsSet]) for line in meas]
                    else:
                        meas.extend([VdsSet])
                    self.dat.append(meas)
                    self.emit(QtCore.SIGNAL("updateGUI"), "from measurement thread")                
                    f.writelines( "%s\t" % item for item in meas)
                    f.write('\n')
        print "It took about %.2f ms per measurement"%((time_now-time_start)*1000./keithley1.__N_SPs__)
        self.emit(QtCore.SIGNAL("measFinished"), "from measurement thread")                
 
#Table model for use with the QTableView class for displaying the measurement data       
class MyTableModel(QtCore.QAbstractTableModel):
    def __init__(self, datain, headerdata, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self.arraydata = datain
        self.headerdata = headerdata

    def rowCount(self, parent=None):
        return len(self.arraydata)
        
    def setData(self,dat):
        self.arraydata = dat
        self.reset

    def columnCount(self, parent=None):
        if len(self.arraydata) > 0:
            return len(self.arraydata[0])
        return 0
        
    def append(self,newLine):
        self.arraydata.append(newLine)
        
    def addRow(self, dat):
        self.insertRow(self.rowCount())

    def setHorizontalHeaderData(self,labels):
        self.headerdata = labels
        
    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and self.headerdata is None: #No headers set yet
            return section
        elif role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self.headerdata[section]
        return QtCore.QAbstractTableModel.headerData(self, section, orientation, role)        

    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != QtCore.Qt.DisplayRole:
            return None
        return self.arraydata[index.row()][index.column()]
          
if __name__ == '__main__':

    # Create the GUI application
    qApp = QtGui.QApplication(sys.argv)
    window = MyWindow()
    window.show() 
#    window.loadIVFile(fileName=r"D:\Dropbox\LMSC\Programming\Probe Station Measurement\test.iv")

#    window.tvData.model().append(['43','54','23'])
#    window.tvData.model().setHorizontalHeaderData(['test1','test2','test3'])
#    window.tvData.model().reset() #Not very efficient
    
    # start the Qt main loop execution, exiting from this script
    # with the same return code of Qt application
    sys.exit(qApp.exec_()) 
    
    