#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.7
import math
import struct
import logging


import sys, os, time, json, datetime,subprocess,copy
import smbus

sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "mpu9255"
G.debug = 2

MPU9255_DEFAULT_ADDRESS			=0x68
MPU9255_ALT_DEFAULT_ADDRESS		=0xD2	

MPU9255_SELF_TEST_X_GYRO		=0x00
MPU9255_SELF_TEST_Y_GYRO		=0x01
MPU9255_SELF_TEST_Z_GYRO		=0x02

MPU9255_SELF_TEST_X_ACCEL		=0x0D
MPU9255_SELF_TEST_Y_ACCEL		=0x0E
MPU9255_SELF_TEST_Z_ACCEL		=0x0F

MPU9255_XG_OFFSET_H				=0x13
MPU9255_XG_OFFSET_L				=0x14
MPU9255_YG_OFFSET_H				=0x15
MPU9255_YG_OFFSET_L				=0x16
MPU9255_ZG_OFFSET_H				=0x17
MPU9255_ZG_OFFSET_L				=0x18
MPU9255_SMPLRT_DIV				=0x19
MPU9255_CONFIG					=0x1A
MPU9255_GYRO_CONFIG				=0x1B
MPU9255_ACCEL_CONFIG			=0x1C
MPU9255_ACCEL_CONFIG2			=0x1D
MPU9255_LP_ACCEL_ODR			=0x1E
MPU9255_WOM_THR					=0x1F

MPU9255_FIFO_EN					=0x23
MPU9255_I2C_MST_CTRL			=0x24
MPU9255_I2C_SLV0_ADDR			=0x25
MPU9255_I2C_SLV0_REG			=0x26
MPU9255_I2C_SLV0_CTRL			=0x27
MPU9255_I2C_SLV1_ADDR			=0x28
MPU9255_I2C_SLV1_REG			=0x29
MPU9255_I2C_SLV1_CTRL			=0x2A
MPU9255_I2C_SLV2_ADDR			=0x2B
MPU9255_I2C_SLV2_REG			=0x2C
MPU9255_I2C_SLV2_CTRL			=0x2D
MPU9255_I2C_SLV3_ADDR			=0x2E
MPU9255_I2C_SLV3_REG			=0x2F
MPU9255_I2C_SLV3_CTRL			=0x30
MPU9255_I2C_SLV4_ADDR			=0x31
MPU9255_I2C_SLV4_REG			=0x32
MPU9255_I2C_SLV4_DO				=0x33
MPU9255_I2C_SLV4_CTRL			=0x34
MPU9255_I2C_SLV4_DI				=0x35
MPU9255_I2C_MST_STATUS			=0x36
MPU9255_INT_PIN_CFG				=0x37
MPU9255_INT_ENABLE				=0x38

MPU9255_INT_STATUS				=0x3A
MPU9255_ACCEL_XOUT_H			=0x3B
MPU9255_ACCEL_XOUT_L			=0x3C
MPU9255_ACCEL_YOUT_H			=0x3D
MPU9255_ACCEL_YOUT_L			=0x3E
MPU9255_ACCEL_ZOUT_H			=0x3F
MPU9255_ACCEL_ZOUT_L			=0x40
MPU9255_TEMP_OUT_H				=0x41
MPU9255_TEMP_OUT_L				=0x42
MPU9255_GYRO_XOUT_H				=0x43
MPU9255_GYRO_XOUT_L				=0x44
MPU9255_GYRO_YOUT_H				=0x45
MPU9255_GYRO_YOUT_L				=0x46
MPU9255_GYRO_ZOUT_H				=0x47
MPU9255_GYRO_ZOUT_L				=0x48
MPU9255_EXT_SENS_DATA_00		=0x49
MPU9255_EXT_SENS_DATA_01		=0x4A
MPU9255_EXT_SENS_DATA_02		=0x4B
MPU9255_EXT_SENS_DATA_03		=0x4C
MPU9255_EXT_SENS_DATA_04		=0x4D
MPU9255_EXT_SENS_DATA_05		=0x4E
MPU9255_EXT_SENS_DATA_06		=0x4F
MPU9255_EXT_SENS_DATA_07		=0x50
MPU9255_EXT_SENS_DATA_08		=0x51
MPU9255_EXT_SENS_DATA_09		=0x52
MPU9255_EXT_SENS_DATA_10		=0x53
MPU9255_EXT_SENS_DATA_11		=0x54
MPU9255_EXT_SENS_DATA_12		=0x55
MPU9255_EXT_SENS_DATA_13		=0x56
MPU9255_EXT_SENS_DATA_14		=0x57
MPU9255_EXT_SENS_DATA_15		=0x58
MPU9255_EXT_SENS_DATA_16		=0x59
MPU9255_EXT_SENS_DATA_17		=0x5A
MPU9255_EXT_SENS_DATA_18		=0x5B
MPU9255_EXT_SENS_DATA_19		=0x5C
MPU9255_EXT_SENS_DATA_20		=0x5D
MPU9255_EXT_SENS_DATA_21		=0x5E
MPU9255_EXT_SENS_DATA_22		=0x5F
MPU9255_EXT_SENS_DATA_23		=0x60

MPU9255_I2C_SLV0_DO				=0x63
MPU9255_I2C_SLV1_DO				=0x64
MPU9255_I2C_SLV2_DO				=0x65
MPU9255_I2C_SLV3_DO				=0x66
MPU9255_I2C_MST_DELAY_CTRL		=0x67
MPU9255_SIGNAL_PATH_RESET		=0x68
MPU9255_MOT_DETECT_CTRL			=0x69
MPU9255_USER_CTRL				=0x6A
MPU9255_PWR_MGMT_1				=0x6B
MPU9255_PWR_MGMT_2				=0x6C

MPU9255_FIFO_COUNTH				=0x72
MPU9255_FIFO_COUNTL				=0x73
MPU9255_FIFO_R_W				=0x74
MPU9255_WHO_AM_I				=0x75
MPU9255_XA_OFFSET_H				=0x77
MPU9255_XA_OFFSET_L				=0x78

MPU9255_YA_OFFSET_H				=0x7A
MPU9255_YA_OFFSET_L				=0x7B

MPU9255_ZA_OFFSET_H				=0x7D
MPU9255_ZA_OFFSET_L				=0x7E

#reset values
WHOAMI_RESET_VAL				=0x71
POWER_MANAGMENT_1_RESET_VAL		=0x01
DEFAULT_RESET_VALUE				=0x00

WHOAMI_DEFAULT_VAL				=0x68

#CONFIG register masks
MPU9255_FIFO_MODE_MASK			=0x40
MPU9255_EXT_SYNC_SET_MASK		=0x38
MPU9255_DLPF_CFG_MASK			=0x07

#GYRO_CONFIG register masks
MPU9255_XGYRO_CTEN_MASK			=0x80
MPU9255_YGYRO_CTEN_MASK			=0x40
MPU9255_ZGYRO_CTEN_MASK			=0x20
MPU9255_GYRO_FS_SEL_MASK		=0x18
MPU9255_FCHOICE_B_MASK			=0x03

MPU9255_GYRO_FULL_SCALE_250DPS	=0b00000000
MPU9255_GYRO_FULL_SCALE_500DPS	=0b00001000
MPU9255_GYRO_FULL_SCALE_1000DPS =0b00010000
MPU9255_GYRO_FULL_SCALE_2000DPS =0b00011000

#ACCEL_CONFIG register masks
MPU9255_AX_ST_EN_MASK			=0x80
MPU9255_AY_ST_EN_MASK			=0x40
MPU9255_AZ_ST_EN_MASK			=0x20
MPU9255_ACCEL_FS_SEL_MASK		=0x18

MPU9255_FULL_SCALE_2G			=0b00000000
MPU9255_FULL_SCALE_4G			=0b00001000
MPU9255_FULL_SCALE_8G			=0b00010000
MPU9255_FULL_SCALE_16G			=0b00011000

#ACCEL_CONFIG_2 register masks
MPU9255_ACCEL_FCHOICE_B_MASK	=0xC0
MPU9255_A_DLPF_CFG_MASK			=0x03

#LP_ACCEL_ODR register masks
MPU9255_LPOSC_CLKSEL_MASK		=0x0F

#FIFO_EN register masks
MPU9255_TEMP_FIFO_EN_MASK		=0x80
MPU9255_GYRO_XOUT_MASK			=0x40
MPU9255_GYRO_YOUT_MASK			=0x20
MPU9255_GYRO_ZOUT_MASK			=0x10
MPU9255_ACCEL_MASK				=0x08
MPU9255_SLV2_MASK				=0x04
MPU9255_SLV1_MASK				=0x02
MPU9255_SLV0_MASK				=0x01

#I2C_MST_CTRL register masks
MPU9255_MULT_MST_EN_MASK		=0x80
MPU9255_WAIT_FOR_ES_MASK		=0x40
MPU9255_SLV_3_FIFO_EN_MASK		=0x20
MPU9255_I2C_MST_P_NSR_MASK		=0x10
MPU9255_I2C_MST_CLK_MASK		=0x0F

#I2C_SLV0_ADDR register masks
MPU9255_I2C_SLV0_RNW_MASK		=0x80
MPU9255_I2C_ID_0_MASK			=0x7F

#I2C_SLV0_CTRL register masks
MPU9255_I2C_SLV0_EN_MASK		=0x80
MPU9255_I2C_SLV0_BYTE_SW_MASK	=0x40
MPU9255_I2C_SLV0_REG_DIS_MASK	=0x20
MPU9255_I2C_SLV0_GRP_MASK		=0x10
MPU9255_I2C_SLV0_LENG_MASK		=0x0F

#I2C_SLV1_ADDR register masks
MPU9255_I2C_SLV1_RNW_MASK		=0x80
MPU9255_I2C_ID_1_MASK			=0x7F

#I2C_SLV1_CTRL register masks
MPU9255_I2C_SLV1_EN_MASK		=0x80
MPU9255_I2C_SLV1_BYTE_SW_MASK	=0x40
MPU9255_I2C_SLV1_REG_DIS_MASK	=0x20
MPU9255_I2C_SLV1_GRP_MASK		=0x10
MPU9255_I2C_SLV1_LENG_MASK		=0x0F

#I2C_SLV2_ADDR register masks
MPU9255_I2C_SLV2_RNW_MASK		=0x80
MPU9255_I2C_ID_2_MASK			=0x7F

#I2C_SLV2_CTRL register masks
MPU9255_I2C_SLV2_EN_MASK		=0x80
MPU9255_I2C_SLV2_BYTE_SW_MASK	=0x40
MPU9255_I2C_SLV2_REG_DIS_MASK	=0x20
MPU9255_I2C_SLV2_GRP_MASK		=0x10
MPU9255_I2C_SLV2_LENG_MASK		=0x0F

#I2C_SLV3_ADDR register masks
MPU9255_I2C_SLV3_RNW_MASK		=0x80
MPU9255_I2C_ID_3_MASK			=0x7F

#I2C_SLV3_CTRL register masks
MPU9255_I2C_SLV3_EN_MASK		=0x80
MPU9255_I2C_SLV3_BYTE_SW_MASK	=0x40
MPU9255_I2C_SLV3_REG_DIS_MASK	=0x20
MPU9255_I2C_SLV3_GRP_MASK		=0x10
MPU9255_I2C_SLV3_LENG_MASK		=0x0F

#I2C_SLV4_ADDR register masks
MPU9255_I2C_SLV4_RNW_MASK		=0x80
MPU9255_I2C_ID_4_MASK			=0x7F

#I2C_SLV4_CTRL register masks
MPU9255_I2C_SLV4_EN_MASK		=0x80
MPU9255_SLV4_DONE_INT_EN_MASK	=0x40
MPU9255_I2C_SLV4_REG_DIS_MASK	=0x20
MPU9255_I2C_MST_DLY_MASK		=0x1F

#I2C_MST_STATUS register masks
MPU9255_PASS_THROUGH_MASK		=0x80
MPU9255_I2C_SLV4_DONE_MASK		=0x40
MPU9255_I2C_LOST_ARB_MASK		=0x20
MPU9255_I2C_SLV4_NACK_MASK		=0x10
MPU9255_I2C_SLV3_NACK_MASK		=0x08
MPU9255_I2C_SLV2_NACK_MASK		=0x04
MPU9255_I2C_SLV1_NACK_MASK		=0x02
MPU9255_I2C_SLV0_NACK_MASK		=0x01

#INT_PIN_CFG register masks
MPU9255_ACTL_MASK				=0x80
MPU9255_OPEN_MASK				=0x40
MPU9255_LATCH_INT_EN_MASK		=0x20
MPU9255_INT_ANYRD_2CLEAR_MASK	=0x10
MPU9255_ACTL_FSYNC_MASK			=0x08
MPU9255_FSYNC_INT_MODE_EN_MASK	=0x04
MPU9255_BYPASS_EN_MASK			=0x02

#INT_ENABLE register masks
MPU9255_WOM_EN_MASK				=0x40
MPU9255_FIFO_OFLOW_EN_MASK		=0x10
MPU9255_FSYNC_INT_EN_MASK		=0x08
MPU9255_RAW_RDY_EN_MASK			=0x01

#INT_STATUS register masks
MPU9255_WOM_INT_MASK			=0x40
MPU9255_FIFO_OFLOW_INT_MASK		=0x10
MPU9255_FSYNC_INT_MASK			=0x08
MPU9255_RAW_DATA_RDY_INT_MASK	=0x01

#I2C_MST_DELAY_CTRL register masks
MPU9255_DELAY_ES_SHADOW_MASK	=0x80
MPU9255_I2C_SLV4_DLY_EN_MASK	=0x10
MPU9255_I2C_SLV3_DLY_EN_MASK	=0x08
MPU9255_I2C_SLV2_DLY_EN_MASK	=0x04
MPU9255_I2C_SLV1_DLY_EN_MASK	=0x02
MPU9255_I2C_SLV0_DLY_EN_MASK	=0x01

#SIGNAL_PATH_RESET register masks
MPU9255_GYRO_RST_MASK			=0x04
MPU9255_ACCEL_RST_MASK			=0x02
MPU9255_TEMP_RST_MASK			=0x01

#MOT_DETECT_CTRL register masks
MPU9255_ACCEL_INTEL_EN_MASK		=0x80
MPU9255_ACCEL_INTEL_MODE_MASK	=0x40

#USER_CTRL register masks
MPU9255_FIFO_EN_MASK			=0x40
MPU9255_I2C_MST_EN_MASK			=0x20
MPU9255_I2C_IF_DIS_MASK			=0x10
MPU9255_FIFO_RST_MASK			=0x04
MPU9255_I2C_MST_RST_MASK		=0x02
MPU9255_SIG_COND_RST_MASK		=0x01

#PWR_MGMT_1 register masks
MPU9255_H_RESET_MASK			=0x80
MPU9255_SLEEP_MASK				=0x40
MPU9255_CYCLE_MASK				=0x20
MPU9255_GYRO_STANDBY_CYCLE_MASK =0x10
MPU9255_PD_PTAT_MASK			=0x08
MPU9255_CLKSEL_MASK				=0x07

#PWR_MGMT_2 register masks
MPU9255_DISABLE_XA_MASK			=0x20
MPU9255_DISABLE_YA_MASK			=0x10
MPU9255_DISABLE_ZA_MASK			=0x08
MPU9255_DISABLE_XG_MASK			=0x04
MPU9255_DISABLE_YG_MASK			=0x02
MPU9255_DISABLE_ZG_MASK			=0x01

MPU9255_DISABLE_XYZA_MASK		=0x38
MPU9255_DISABLE_XYZG_MASK		=0x07

#Magnetometer register maps
MPU9255_MAG_ADDRESS				=0x0C

MPU9255_MAG_WIA					=0x00
MPU9255_MAG_INFO				=0x01
MPU9255_MAG_ST1					=0x02
MPU9255_MAG_XOUT_L				=0x03
MPU9255_MAG_XOUT_H				=0x04
MPU9255_MAG_YOUT_L				=0x05
MPU9255_MAG_YOUT_H				=0x06
MPU9255_MAG_ZOUT_L				=0x07
MPU9255_MAG_ZOUT_H				=0x08
MPU9255_MAG_ST2					=0x09
MPU9255_MAG_CNTL				=0x0A
MPU9255_MAG_RSV					=0x0B #reserved mystery meat
MPU9255_MAG_ASTC				=0x0C
MPU9255_MAG_TS1					=0x0D
MPU9255_MAG_TS2					=0x0E
MPU9255_MAG_I2CDIS				=0x0F
MPU9255_MAG_ASAX				=0x10
MPU9255_MAG_ASAY				=0x11
MPU9255_MAG_ASAZ				=0x12

class MPU9255: 

	def __init__(self, busNumber=1, i2cAddress=""):

		self.busNumber			 = busNumber
		try:
			self.bus			= smbus.SMBus(self.busNumber)
		except Exception, e:
			U.toLog(-1,'couldn\'t open bus: {0}'.format(e))
			return 
			
		self.address	 = MPU9255_DEFAULT_ADDRESS
		self.mag_address = MPU9255_MAG_ADDRESS

		# hard reset
		self.bus.write_byte_data(self.address,MPU9255_PWR_MGMT_1,  0b10000000)
		time.sleep(0.1)
		#setClockSource(0) internal 20 MHz
		self.bus.write_byte_data(self.address,MPU9255_PWR_MGMT_1,  0)

		#set gyr sensitivity
		self.bus.write_byte_data(self.address,MPU9255_GYRO_CONFIG, MPU9255_GYRO_FULL_SCALE_2000DPS) 

		#set acc sensitivity
		self.bus.write_byte_data(self.address,MPU9255_ACCEL_CONFIG, MPU9255_FULL_SCALE_16G)

		# switch to bypass to enable magnetometer readings, now use mag_address to red mag sensor
		self.bus.write_byte_data(self.address,MPU9255_INT_PIN_CFG, MPU9255_BYPASS_EN_MASK)

		time.sleep(0.1)


	def readRegisters(self,addr, lsb_register): 
		value = self.bus.read_word_data(addr,lsb_register)
		if (value >= 0x8000):
			return -((65535 - value) + 1)
		return value




	def getSensordata(self): 
		try:
			#get acc
			a=["","",""]
			m=["","",""]
			g=["","",""]
			t=""
			a[0] = self.readRegisters(self.address, MPU9255_ACCEL_XOUT_L)
			a[1] = self.readRegisters(self.address, MPU9255_ACCEL_YOUT_L)
			a[2] = self.readRegisters(self.address, MPU9255_ACCEL_ZOUT_L)
			#get gyro
			g[0]=  self.readRegisters(self.address, MPU9255_GYRO_XOUT_L) 
			g[1]=  self.readRegisters(self.address, MPU9255_GYRO_YOUT_L) 
			g[2]=  self.readRegisters(self.address, MPU9255_GYRO_ZOUT_L) 
			# get temp
			t =	 int(float(self.readRegisters(self.address, MPU9255_TEMP_OUT_L))/340. +21.)
			#read magnetometer
			self.bus.write_byte_data(self.mag_address,MPU9255_MAG_CNTL, 0b00000001) #enable the magnetometer, single shot
			time.sleep(0.01)
			m[0] =	self.readRegisters(self.mag_address, MPU9255_MAG_XOUT_L) 
			m[1] =	self.readRegisters(self.mag_address, MPU9255_MAG_YOUT_L) 
			m[2] =	self.readRegisters(self.mag_address, MPU9255_MAG_ZOUT_L) 
		except: pass
		return	a,g,m,t




		
def startSENSOR(devId, i2cAddress):
	global theSENSORdict
	try:
		U.toLog(-1,"==== Start mpu9255 ===== @ i2c= " +unicode(i2cAddress)+"  devId=" +unicode(devId))
		theSENSORdict[devId] = MPU9255(i2cAddress=i2cAddress)

	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



#################################		 
def readParams():
	global sensors, sensor
	global rawOld
	global theSENSORdict, resetPin
	global oldRaw, lastRead
	try:

		inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
		if inp == "": return
		if lastRead2 == lastRead: return
		lastRead   = lastRead2
		if inpRaw == oldRaw: return
		oldRaw	   = inpRaw

		externalSensor=False
		sensorsOld= copy.copy(sensors)

	   
		U.getGlobalParams(inp)
		if "sensors"			in inp:	 sensors =				 (inp["sensors"])
		if "debugRPI"			in inp:	 G.debug=			  int(inp["debugRPI"]["debugRPISENSOR"])
		
 
		if sensor not in sensors:
			U.toLog(-1, "BNO055 is not in parameters = not enabled, stopping ina219.py" )
			exit()
			
				
		for devId in sensors[sensor]:
			U.getMAGReadParameters(sensors[sensor][devId],devId)


			try:
				if "resetPin" in sensors[sensor][devId]: 
					resetPin= int(sensors[sensor][devId]["resetPin"])
			except:
				resetPin = -1
				
			if devId not in theSENSORdict:
				startSENSOR(devId, G.i2cAddress)
				
		deldevID={}		   
		for devId in theSENSORdict:
			if devId not in sensors[sensor]:
				deldevID[devId]=1
		for dd in  deldevID:
			del theSENSORdict[dd]
		if len(theSENSORdict) ==0: 
			####exit()
			pass

	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))



#################################
def getValues(devId):
	global sensor, sensors,	 theSENSORdict
	try:
		data = {}
		ACC,GYR,MAG, temp=	theSENSORdict[devId].getSensordata()
		EULER = U.getEULER(MAG)
		data["ACC"]	  = fillWithItems(ACC,["x","y","z"],2)
		data["GYR"]	  = fillWithItems(GYR,["x","y","z"],2)
		data["MAG"]	  = fillWithItems(MAG,["x","y","z"],2)
		data["EULER"] = fillWithItems(EULER,["heading","roll","pitch"],2)
		data["temp"] = temp
		for xx in data:
			U.toLog(2, (xx).ljust(11)+" "+unicode(data[xx]))
		return data
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
	return {"MAG":"bad"}

def fillWithItems(theList,theItems,digits):
	out={}
	for ii in range(len(theItems)):
		out[theItems[ii]] = round(theList[ii],digits)
	return out


############################################
global rawOld
global sensor, sensors, badSensor
global deltaX, theSENSORdict
global oldRaw,	lastRead
oldRaw					= ""
lastRead				= 0

G.debug						= 5
loopCount					= 0
NSleep						= 100
sensors						= {}
sensor						= G.program
quick						= False
theSENSORdict				 ={}
myPID		= str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


if U.getIPNumber() > 0:
	time.sleep(10)
	exit()

readParams()

time.sleep(1)

lastRead = time.time()

U.echoLastAlive(G.program)



lastValueDefault	= {"EULER":{"heading":0,"roll":0,"pitch":0},"MAG":{"x":0,"y":0,"z":0},"GYR":{"x":0,"y":0,"z":0},"ACC":{"x":0,"y":0,"z":0}}
lastRead			= time.time()
G.lastAliveSend		= time.time() -1000
testDims			= ["GYR","ACC"]
testCoords			= ["x","y","z"]
testForBadSensor	= "MAG"
lastValue			= {}
thresholdDefault	= 0.1
sumTest				={"dim":"GRAV","limits":[0,250.]}
singleTest			={"dim":"EULER","coord":"heading","limits":[-9999.,400.]}

startTime = time.time()
while True:
	try:
		tt = time.time()
		if sensor in sensors:
			skip =False
			
		if sensor in sensors:
			for devId in sensors[sensor]:
				if devId not in lastValue: lastValue[devId] = copy.copy(lastValueDefault)
				if devId not in G.threshold: G.threshold[devId] = thresholdDefault
				values = getValues(devId)
				lastValue =U.checkMGACCGYRdata(
					values,lastValue,testDims,testCoords,testForBadSensor,devId,sensor,quick)
					#sumTest=sumTest,singleTest=singleTest)

		loopCount +=1

		quick = U.checkNowFile(G.program)				 
		U.echoLastAlive(G.program)

		tt= time.time()
		if tt - lastRead > 5.:	
			readParams()
			lastRead = tt
		if not quick:
			time.sleep(G.sensorLoopWait)
		
	except	Exception, e:
		U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
		time.sleep(5.)
sys.exit(0)

