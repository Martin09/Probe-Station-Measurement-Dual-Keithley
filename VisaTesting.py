# -*- coding: utf-8 -*-
"""
Created on Wed Mar 25 10:51:54 2015

@author: friedl
"""

import visa
rm = visa.ResourceManager()
print str(rm.list_resources()) + '\n'

k6487_12 = rm.open_resource('GPIB0::12::INSTR')
print(k6487_12.query('*IDN?'))

k6487_22 = rm.open_resource('GPIB0::22::INSTR')
print(k6487_22.query('*IDN?'))

k6517A_27 = rm.open_resource('GPIB0::27::INSTR')
print(k6517A_27.query('*IDN?'))