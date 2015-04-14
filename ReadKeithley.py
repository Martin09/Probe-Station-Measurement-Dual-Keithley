# -*- coding: utf-8 -*-
"""
Created on Tue Mar 24 17:22:07 2015

@author: Martin Friedl @ EPFL
"""
from KeithleyDevice import Keithley

#Settings Keihtley
Address=22
timeout=1000.
NPLC=0.01
VsRange=10
IsRange=2.5e-3
ImRange= 2E-3
delay_SP=10E-3
N_ppSP = 1
delay_trig=1E-3
Verbose = True
zeroCheck = True
displayOff = False

setpoints = [1,2,3,4,5]

def outToScr(message):
    print message

#keithley = measure_sweep.devices.Keithley_Delta('GPIB::10')
keithley=Keithley(address="GPIB::%d"%Address,
                  timeout=timeout,
                  NPLC=NPLC,
                  VsRange=VsRange,
                  IsRange=IsRange,
                  ImRange=ImRange,
                  setpoints=setpoints,
                  delay_SP=delay_SP,
                  N_ppSP=N_ppSP,
                  delay_trig=delay_trig,
                  verbose=Verbose,
                  zeroCheck=zeroCheck,
                  displayOff=displayOff,
                  logfunc=outToScr)

keithley.initialize()
data = keithley.start()
keithley.close()
print data
#print data.mean(0)