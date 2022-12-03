#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# march 10 2017
# example program to get data to indigo through myprogram 
#
#
import sys
import os
import time
import json
import datetime
import subprocess
import copy
import smbus

sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G

G.program = "myprogram"

# ===========================================================================
# utils do not change
#  ===========================================================================


def readParams():
    inp,inpRaw = U.doRead()
    if inp == "": return
	U.getGlobalParams(inp)


### example how to read sensor and send it back to getsensorvalues
# ===========================================================================
# SHT21
# ===========================================================================
class SHT21:
    """Class to read temperature and humidity from SHT21.
      Ressources: 
      http://www.sensirion.com/fileadmin/user_upload/customers/sensirion/Dokumente/Humidity/Sensirion_Humidity_SHT21_Datasheet_V3.pdf
      https://github.com/jaques/sht21_python/blob/master/sht21.py
      Martin Steppuhn's code from http://www.emsystech.de/raspi-sht21"""

    def __init__(self, i2cAdd):
        self._I2C_ADDRESS = i2cAdd
        self._SOFTRESET   = 0xFE
        self._TRIGGER_TEMPERATURE_NO_HOLD = 0xF3
        self._TRIGGER_HUMIDITY_NO_HOLD = 0xF5
        """According to the datasheet the soft reset takes less than 15 ms."""
        self.bus = smbus.SMBus(1)
        self.bus.write_byte(self._I2C_ADDRESS, self._SOFTRESET)
        time.sleep(0.015)

    def read_temperature(self):    
        """Reads the temperature from the sensor.  Not that this call blocks
        for 250ms to allow the sensor to return the data"""
        data = []
        self.bus.write_byte(self._I2C_ADDRESS, self._TRIGGER_TEMPERATURE_NO_HOLD)
        time.sleep(0.250)
        data.append(self.bus.read_byte(self._I2C_ADDRESS))
        data.append(self.bus.read_byte(self._I2C_ADDRESS))
        """This function reads the first two bytes of data and 
        returns the temperature in C by using the following function:
        T = =46.82 + (172.72 * (ST/2^16))
        where ST is the value from the sensor
        """
        unadjusted = (data[0] << 8) + data[1]
        unadjusted *= 175.72
        unadjusted /= 1 << 16 # divide by 2^16
        unadjusted -= 46.85
        return unadjusted
        

    def read_humidity(self):    
        """Reads the humidity from the sensor.  Not that this call blocks 
        for 250ms to allow the sensor to return the data"""
        data = []
        self.bus.write_byte(self._I2C_ADDRESS, self._TRIGGER_HUMIDITY_NO_HOLD)
        time.sleep(0.250)
        data.append(self.bus.read_byte(self._I2C_ADDRESS))
        data.append(self.bus.read_byte(self._I2C_ADDRESS))
        """This function reads the first two bytes of data and returns 
        the relative humidity in percent by using the following function:
        RH = -6 + (125 * (SRH / 2 ^16))
        where SRH is the value read from the sensor
        """
        unadjusted = (data[0] << 8) + data[1]
        unadjusted *= 125
        unadjusted /= 1 << 16 # divide by 2^16
        unadjusted -= 6
        return unadjusted

def getSHT21(i2c=0):
        global cAddress
        global sensorSHT21, SHT21started
        t,h ="",""

        i2cAdd = 0x40
        if i2c != 0 :
            i2cAdd = int(i2c)

        try:
            ii= SHT21started
        except:    
            SHT21started=1
            sensorSHT21 ={}

        if str(i2cAdd) not in sensorSHT21:
            sensorSHT21[str(i2cAdd)]= SHT21(i2cAdd=i2cAdd)

        try:
            t =("%5.1f"%float(sensorSHT21[str(i2cAdd)].read_temperature())).strip()
            h =("%3d"%sensorSHT21[str(i2cAdd)].read_humidity()).strip()
            return t,h
        except  Exception as e:
                U.logger.log(20,"", exc_info=True)
                U.logger.log(30, u"return  value: t={}".format(t)+";  h={}".format(h)  )
                U.logger.log(30, u"i2c address used: {}".format(i2cAdd) )
        return "",""    




####################### main start ###############
U.setLogging()


# ===========================================================================
# Main, should wong ok as is
# ===========================================================================

###
###  do not use PRINT !!! any  sys out stuff goes as return message to the calling program 
###


readParams()           # get parameters send from indigo
U.logger.log(30,"input params: {}".format(sys.argv))
   
try:
    params = sys.argv[1]
    params = json.loads(params)
except  Exception, e :
    U.logger.log(30,"", exc_info=True)
    params ={"devId":"","freeParameter":""}
deviceID      = params["devId"]
freeParameter = params["freeParameter"]


# assuming freeParameter is the i2c number:
##  t,h =getSHT21(i2c=int(freeParameter))
#set dummy variables:
t=55
h=33
    
returnMessage = {"INPUT_0":t,"INPUT_1":h,"INPUT_2":55,"INPUT_3":10,"INPUT_9":"abc"}
sys.stdout.write(json.dumps(returnMessage))

# you find the logoutput in /var/log/myprogram.log, if U.logger.log(30,
U.logger.log(10, u"returning message:"+ json.dumps(returnMessage))
    
sys.exit(0)        
