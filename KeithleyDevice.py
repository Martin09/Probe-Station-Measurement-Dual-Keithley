# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import numpy as np
import visa
from time import sleep,time
import socket
import struct

testing = False

class EmptyClass:
    pass

class Keithley(object):
    def __init__(self,address,
                 timeout=100,
                 NPLC=1,
                 VsRange=10,
                 IsRange=2.5E-5,
                 ImRange=2E-5,
                 delay_init=1000,
                 setpoints=[0],
                 N_SPs=5,
                 delay_SP=1E-3,
                 N_ppSP=1,
                 delay_trig=0.,
                 verbose=False,
                 zeroCheck=False,
                 displayOff=False,
                 logfunc=None):
                              
        self.__address__=address
        if testing:
            self.__instrument__ = EmptyClass()
        else:
            self.__rm__ = visa.ResourceManager()
            self.__instrument__ = self.__rm__.open_resource(address)
            self.__instrument__.timeout = timeout            
        
        self.__timeout__=timeout
        self.__NPLC__=NPLC
        self.__VsRange__=VsRange
        self.__IsRange__=IsRange
        self.__ImRange__=ImRange  
        self.__delay_init__=delay_init
        self.__setpoints__=setpoints
        self.__N_SPs__=N_SPs
        self.__delay_SP__=delay_SP
        self.__N_ppSP__=N_ppSP
        self.__delay_trig__=delay_trig                
        self.verbose=verbose
        self.__zeroCheck__=zeroCheck
        self.__displayOff__=displayOff
        self.logfunc=logfunc

    def write(self,message):
        if self.verbose:
            self.logfunc("Write: %s"%message)
        if not(testing):
            self.__instrument__.write(message)
        
    def ask(self,message):
        s = None
        if self.verbose:
            self.logfunc("Ask: %s"%message)
        if not(testing):
            s= self.__instrument__.ask(message)
        return s
    
    def setImRange(self,val):

        if val == None:
            Range=" AUTO ON"
        else:
            Range=" %.2E"%val
        self.write("RANG%s"%Range)
        
    def setVsRange(self,val):
        self.write("SOUR:VOLT:RANG %i"%val)
        
    def setVs(self,val):
        self.write("SOUR:VOLT %.2E"%val)
        
    def setIsRange(self,val):
        self.write("SOUR:VOLT:ILIM %.2E"%val)
        
    def setTrigDelay(self,val):
        self.write("TRIG:DEL %.2E"%val)
        
    def setTrigCount(self,val):
        self.write("TRIG:COUN %i"%val)
        
    def setNPLC(self,val):
        self.write("NPLC %.2f"%val)
    
    def configure(self):
        self.write("*RST") #Reset to defaults
        if self.__zeroCheck__:
            self.write("SYST:ZCH ON") #Turn on zero checking
            self.setImRange(2E-9) #Select the 2nA range
            self.write("INIT") #Trigger reading to be used as zero
            self.write("SYST:ZCOR:ACQ")  
            self.write("SYST:ZCOR ON")
            self.write("SYST:ZCH OFF")
#            self.write("SYST:AZER OFF") #Turn on auto-zero                        
        else:
            self.write("SYST:ZCOR OFF")         
            self.write("SYST:ZCH OFF") #Turn off zero checking
#            self.write("SYST:AZER OFF") #Turn off auto-zero            
            
        self.setTrigDelay(self.__delay_trig__) #Set trigger delay
        self.setTrigCount(self.__N_ppSP__) #Set points per setpoint
            
        if self.__displayOff__:
            self.write("DISP:ENAB OFF")
        else:
            self.write("DISP:ENAB ON")
            
        self.setVsRange(self.__VsRange__) # Select source range.
        self.setIsRange(self.__IsRange__) # Set current limit
        self.write("FORM:ELEM READ,TIME,VSO")        
        self.setImRange(self.__ImRange__)
        self.setNPLC(self.__NPLC__)
        self.setVs(0) #Set voltage voltage source to zero
        self.write("SOUR:VOLT:STAT ON")# Put voltage source in operate.        
        
    def waitForFirstMeasurement(self):
        self.__instrument__.timeout=1000
        self.ask("READ?")
#        print reply
        self.__instrument__.timeout=self.__timeout__        

    def parseData(self,string):
#        print string
        dat = np.array([float(x) for x in string.split(',')])
        dat = dat.reshape([-1,3])
        dat[dat[:,0] == 9.9e37,0] = np.NaN #Overflow data = NaN
        dat[dat[:,2] == -999,2] = np.NaN #Compliance data = NaN        
        return dat
            
    def start(self,starttime=0,startcount=0):
        self.write("*CLS")
        self.write("INIT")
        self.waitForFirstMeasurement()
        return
        
    def abort(self):
        self.write("SOUR:VOLT:SWE:ABOR")
        
    def close(self):
        self.abort()
#        self.write("*RST")
        self.write("SOUR:VOLT:STAT OFF")
        self.write("SYST:ZCH ON") #Turn on zero checking        
        self.write("DISP:ENAB ON")
        
    def initialize(self):
        #Don't do this: sets back to Float
#        self.write("*RST")
        self.abort()
        self.configure()
        
if __name__=='__main__':
    execfile( "ReadKeithley.py")
