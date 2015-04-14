# -*- coding: utf-8 -*-
"""
Created on Tue Mar 17 10:05:31 2015

@author: Martin Friedl
"""

# for command-line arguments
import sys
import datetime
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

class MyWindow(QtGui.QMainWindow):
    def __init__(self):
        super(MyWindow, self).__init__()
        uic.loadUi('ProbestationMeasurementGUI.ui', self)
        self.show()


        
    def tabChangedSlot(self):
        selected_index = self.tabWidget.currentIndex()
        if selected_index == 0: #Plot chooser
            self.updatePlot_RawData()
        elif selected_index == 1: #Analysis
            self.updatePlotFromAxisSettings()
        
if __name__ == '__main__':
    # Create the GUI application
    qApp = QtGui.QApplication(sys.argv)
    window = MyWindow()
    window.show() 

    # start the Qt main loop execution, exiting from this script
    # with the same return code of Qt application
    sys.exit(qApp.exec_()) 
    
    