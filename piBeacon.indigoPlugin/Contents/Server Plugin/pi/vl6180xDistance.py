#!/usr/bin/python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.9 
##
# ST VL6180X ToF range finder program


import sys, os, time, json, datetime,subprocess,copy
import smbus

sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G
G.program = "vl6180xDistance"
G.debug = 0
import  displayDistance as DISP

# ===========================================================================
# read params
# ===========================================================================

#################################        
def readParams():
    global sensorList, sensors, logDir, sensor,  sensorRefreshSecs, dynamic, mode, deltaDist,displayEnable
    global output, sensorActive, timing, tof, distanceUnits, rawOld
    global actionDistanceOld, actionShortDistance, actionShortDistanceLimit, actionLongDistance, actionLongDistanceLimit
    global oldRaw, lastRead
    try:

        inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
        if inp == "": return
        if lastRead2 == lastRead: return
        lastRead   = lastRead2
        if inpRaw == oldRaw: return
        oldRaw     = inpRaw


        externalSensor=False
        sensorList=[]
        sensorsOld= copy.copy(sensors)

        
        U.getGlobalParams(inp)
          
        if "sensorList"         in inp:  sensorList=             (inp["sensorList"])
        if "sensors"            in inp:  sensors =               (inp["sensors"])
        if "debugRPI"           in inp:  G.debug=             int(inp["debugRPI"]["debugRPISENSOR"])
        if "distanceUnits"      in inp:  distanceUnits=          (inp["distanceUnits"])
        
        if "output"             in inp:  output=                 (inp["output"])
   
 
        if sensor not in sensors:
            U.toLog(-1, "vl6180xDistance is not in parameters = not enabled, stopping vl6180xDistance.py" )
            exit()
            
 
        sensorUp = doWeNeedToStartSensor(sensors,sensorsOld,sensor)


        if sensorUp != 0: # something has changed
            if os.path.isfile(G.homeDir+"temp/"+sensor+".dat"):
                os.remove(G.homeDir+"temp/"+sensor+".dat")
                
        dynamic = False
        deltaDist={}
        for devId in sensors[sensor]:
            deltaDist[devId]  = 0.1
            try:
                xx = sensors[sensor][devId]["sensorRefreshSecs"].split("#")
                sensorRefreshSecs = int(xx[0]) 
                if sensorRefreshSecs  < 0: dynamic=True
                if len(xx)==2: 
                    try: mode = int(xx[1])
                    except: mode =0
            except:
                sensorRefreshSecs = 100    
                mode =0

            try:
                if "displayEnable" in sensors[sensor][devId]: 
                    displayEnable = sensors[sensor][devId]["displayEnable"]
            except:
                display = False    

            try:
                if "deltaDist" in sensors[sensor][devId]: 
                    deltaDist[devId]= float(sensors[sensor][devId]["deltaDist"])/100.
            except:
                pass
            try:
                if "dUnits" in sensors[sensor][devId] and sensors[sensor][devId]["dUnits"] !="":
                    distanceUnits = sensors[sensor][devId]["dUnits"]
            except  Exception, e:
                pass

            try:
                if "actionShortDistance" in sensors[sensor][devId]:         actionShortDistance = (sensors[sensor][devId]["actionShortDistance"])
            except:                                                         actionShortDistance = ""

            try:
                if "actionMediumDistance" in sensors[sensor][devId]:        actionMediumDistance = (sensors[sensor][devId]["actionMediumDistance"])
            except:                                                         actionMediumDistance = ""

            try:
                if "actionLongDistance" in sensors[sensor][devId]:          actionLongDistance = (sensors[sensor][devId]["actionLongDistance"])
            except:                                                         actionLongDistance = ""

            try:
                if "actionShortDistanceLimit" in sensors[sensor][devId]:    actionShortDistanceLimit = float(sensors[sensor][devId]["actionShortDistanceLimit"])
            except:                                                         actionShortDistanceLimit = -1

            try:
                if "actionLongDistanceLimit" in sensors[sensor][devId]:     actionLongDistanceLimit = float(sensors[sensor][devId]["actionLongDistanceLimit"])
            except:                                                         actionLongDistanceLimit = -1

        if sensorUp == 1:
            if not sensorActive:
                if "i2cAddress" in sensors[sensor][devId]: i2cAddress= int(sensors[sensor][devId]["i2cAddress"])
                else: i2cAddress = 0x29
                tof = vl6180x(address=i2cAddress)
                U.toLog(-1,"==== Start ranging =====")
                #startSensor(0)

        if sensorUp == -1:
            U.toLog(-1, "==== stop  ranging =====")
            exit()


    except  Exception, e:
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))



#################################
def doWeNeedToStartSensor(sensors,sensorsOld,selectedSensor):
    if selectedSensor not in sensors:    return -1
    if selectedSensor not in sensorsOld: return 1

    for devId in sensors[selectedSensor] :
            if devId not in sensorsOld[selectedSensor] :            return 1
            for prop in sensors[sensor][devId] :
                if prop not in sensorsOld[selectedSensor][devId] :  return 1
                if sensors[selectedSensor][devId][prop] != sensorsOld[selectedSensor][devId][prop]:
                    return 1
   
    for devId in sensorsOld[selectedSensor]:
            if devId not in sensors[selectedSensor] :               return 1
            for prop in sensorsOld[selectedSensor][devId] :
                if prop not in sensors[selectedSensor][devId] :     return 1

    return 0



# ===========================================================================
# ST_VL6180x ToF ranger Class
#
# Originally written by A. Weber
# References Arduino library by Casey Kuhns of SparkFun:
# https://github.com/sparkfun/ToF_Range_Finder-VL6180_Library\
# ===========================================================================


class vl6180x:
    i2c = None

    __VL6180X_IDENTIFICATION_MODEL_ID               = 0x0000
    __VL6180X_IDENTIFICATION_MODEL_REV_MAJOR        = 0x0001
    __VL6180X_IDENTIFICATION_MODEL_REV_MINOR        = 0x0002
    __VL6180X_IDENTIFICATION_MODULE_REV_MAJOR       = 0x0003
    __VL6180X_IDENTIFICATION_MODULE_REV_MINOR       = 0x0004
    __VL6180X_IDENTIFICATION_DATE                   = 0x0006    # 16bit value
    __VL6180X_IDENTIFICATION_TIME                   = 0x0008    # 16bit value

    __VL6180X_SYSTEM_MODE_GPIO0                     = 0x0010
    __VL6180X_SYSTEM_MODE_GPIO1                     = 0x0011
    __VL6180X_SYSTEM_HISTORY_CTRL                   = 0x0012
    __VL6180X_SYSTEM_INTERRUPT_CONFIG_GPIO          = 0x0014
    __VL6180X_SYSTEM_INTERRUPT_CLEAR                = 0x0015
    __VL6180X_SYSTEM_FRESH_OUT_OF_RESET             = 0x0016
    __VL6180X_SYSTEM_GROUPED_PARAMETER_HOLD         = 0x0017

    __VL6180X_SYSRANGE_START                        = 0x0018
    __VL6180X_SYSRANGE_THRESH_HIGH                  = 0x0019
    __VL6180X_SYSRANGE_THRESH_LOW                   = 0x001A
    __VL6180X_SYSRANGE_INTERMEASUREMENT_PERIOD      = 0x001B
    __VL6180X_SYSRANGE_MAX_CONVERGENCE_TIME         = 0x001C
    __VL6180X_SYSRANGE_CROSSTALK_COMPENSATION_RATE  = 0x001E
    __VL6180X_SYSRANGE_CROSSTALK_VALID_HEIGHT       = 0x0021
    __VL6180X_SYSRANGE_EARLY_CONVERGENCE_ESTIMATE   = 0x0022
    __VL6180X_SYSRANGE_PART_TO_PART_RANGE_OFFSET    = 0x0024
    __VL6180X_SYSRANGE_RANGE_IGNORE_VALID_HEIGHT    = 0x0025
    __VL6180X_SYSRANGE_RANGE_IGNORE_THRESHOLD       = 0x0026
    __VL6180X_SYSRANGE_MAX_AMBIENT_LEVEL_MULT       = 0x002C
    __VL6180X_SYSRANGE_RANGE_CHECK_ENABLES          = 0x002D
    __VL6180X_SYSRANGE_VHV_RECALIBRATE              = 0x002E
    __VL6180X_SYSRANGE_VHV_REPEAT_RATE              = 0x0031

    __VL6180X_SYSALS_START                          = 0x0038
    __VL6180X_SYSALS_THRESH_HIGH                    = 0x003A
    __VL6180X_SYSALS_THRESH_LOW                     = 0x003C
    __VL6180X_SYSALS_INTERMEASUREMENT_PERIOD        = 0x003E
    __VL6180X_SYSALS_ANALOGUE_GAIN                  = 0x003F
    __VL6180X_SYSALS_INTEGRATION_PERIOD             = 0x0040

    __VL6180X_RESULT_RANGE_STATUS                   = 0x004D
    __VL6180X_RESULT_ALS_STATUS                     = 0x004E
    __VL6180X_RESULT_INTERRUPT_STATUS_GPIO          = 0x004F
    __VL6180X_RESULT_ALS_VAL                        = 0x0050
    __VL6180X_RESULT_HISTORY_BUFFER                 = 0x0052
    __VL6180X_RESULT_RANGE_VAL                      = 0x0062
    __VL6180X_RESULT_RANGE_RAW                      = 0x0064
    __VL6180X_RESULT_RANGE_RETURN_RATE              = 0x0066
    __VL6180X_RESULT_RANGE_REFERENCE_RATE           = 0x0068
    __VL6180X_RESULT_RANGE_RETURN_SIGNAL_COUNT      = 0x006C
    __VL6180X_RESULT_RANGE_REFERENCE_SIGNAL_COUNT   = 0x0070
    __VL6180X_RESULT_RANGE_RETURN_AMB_COUNT         = 0x0074
    __VL6180X_RESULT_RANGE_REFERENCE_AMB_COUNT      = 0x0078
    __VL6180X_RESULT_RANGE_RETURN_CONV_TIME         = 0x007C
    __VL6180X_RESULT_RANGE_REFERENCE_CONV_TIME      = 0x0080

    __VL6180X_READOUT_AVERAGING_SAMPLE_PERIOD       = 0x010A
    __VL6180X_FIRMWARE_BOOTUP                       = 0x0119
    __VL6180X_FIRMWARE_RESULT_SCALER                = 0x0120
    __VL6180X_I2C_SLAVE_DEVICE_ADDRESS              = 0x0212
    __VL6180X_INTERLEAVED_MODE_ENABLE               = 0x02A3

    __ALS_GAIN_1    = 0x06
    __ALS_GAIN_1_25 = 0x05
    __ALS_GAIN_1_67 = 0x04
    __ALS_GAIN_2_5  = 0x03
    __ALS_GAIN_5    = 0x02
    __ALS_GAIN_10   = 0x01
    __ALS_GAIN_20   = 0x00
    __ALS_GAIN_40   = 0x07

    # Dictionaries with the valid ALS gain values
    # These simplify and clean the code (avoid abuse of if/elif/else clauses)
    ALS_GAIN_REG = {
        1:      __ALS_GAIN_1,
        1.25:   __ALS_GAIN_1_25,
        1.67:   __ALS_GAIN_1_67,
        2.5:    __ALS_GAIN_2_5,
        5:      __ALS_GAIN_5,
        10:     __ALS_GAIN_10,
        20:     __ALS_GAIN_20,
        40:     __ALS_GAIN_40
    }
    ALS_GAIN_ACTUAL = {    # Data sheet shows gain values as binary list
        1:      1.01,      # Nominal gain 1;    actual gain 1.01
        1.25:   1.28,      # Nominal gain 1.25; actual gain 1.28
        1.67:   1.72,      # Nominal gain 1.67; actual gain 1.72
        2.5:    2.60,      # Nominal gain 2.5;  actual gain 2.60
        5:      5.21,      # Nominal gain 5;    actual gain 5.21
        10:     10.32,     # Nominal gain 10;   actual gain 10.32
        20:     20.00,     # Nominal gain 20;   actual gain 20
        40:     40.00,     # Nominal gain 40;   actual gain 40
    }
    gainList = [1.,1.25,1.67,2.5,5,10,20,40]
    
    def __init__(self, address=0x29):
        # Depending on if you have an old or a new Raspberry Pi, you
        # may need to change the I2C bus.  Older Pis use SMBus 0,
        # whereas new Pis use SMBus 1.  If you see an error like:
        # 'Error accessing 0x29: Check your I2C address '
        # change the SMBus number in the initializer below!

        # setup i2c bus and SFR address
        self.i2c                = smbus.SMBus(1)
        self.address            = address

        # Module identification
        self.idModel            = 0x00
        self.idModelRevMajor    = 0x00
        self.idModelRevMinor    = 0x00
        self.idModuleRevMajor   = 0x00
        self.idModuleRevMinor   = 0x00
        self.idDate             = 0x00
        self.idTime             = 0x00



        if self.get_register(self.__VL6180X_SYSTEM_FRESH_OUT_OF_RESET) == 1:
            U.toLog(0,"ToF sensor is ready.")
            self.ready = True
        else:
            U.toLog(-1,"ToF sensor reset failure.")
            self.ready = False

        # Required by datasheet
        # http://www.st.com/st-web-ui/static/active/en/resource/technical/document/application_note/DM00122600.pdf
        self.set_register(0x0207, 0x01)
        self.set_register(0x0208, 0x01)
        self.set_register(0x0096, 0x00)
        self.set_register(0x0097, 0xfd)
        self.set_register(0x00e3, 0x00)
        self.set_register(0x00e4, 0x04)
        self.set_register(0x00e5, 0x02)
        self.set_register(0x00e6, 0x01)
        self.set_register(0x00e7, 0x03)
        self.set_register(0x00f5, 0x02)
        self.set_register(0x00d9, 0x05)
        self.set_register(0x00db, 0xce)
        self.set_register(0x00dc, 0x03)
        self.set_register(0x00dd, 0xf8)
        self.set_register(0x009f, 0x00)
        self.set_register(0x00a3, 0x3c)
        self.set_register(0x00b7, 0x00)
        self.set_register(0x00bb, 0x3c)
        self.set_register(0x00b2, 0x09)
        self.set_register(0x00ca, 0x09)
        self.set_register(0x0198, 0x01)
        self.set_register(0x01b0, 0x17)
        self.set_register(0x01ad, 0x00)
        self.set_register(0x00ff, 0x05)
        self.set_register(0x0100, 0x05)
        self.set_register(0x0199, 0x05)
        self.set_register(0x01a6, 0x1b)
        self.set_register(0x01ac, 0x3e)
        self.set_register(0x01a7, 0x1f)
        self.set_register(0x0030, 0x00)
        U.toLog(2,"Register settings:")
        U.toLog(2,"0x0207 - %x" % self.get_register(0x0207))
        U.toLog(2,"0x0208 - %x" % self.get_register(0x0208))
        U.toLog(2,"0x0096 - %x" % self.get_register(0x0096))
        U.toLog(2,"0x0097 - %x" % self.get_register(0x0097))
        U.toLog(2,"0x00e3 - %x" % self.get_register(0x00e3))
        U.toLog(2,"0x00e4 - %x" % self.get_register(0x00e4))
        U.toLog(2,"0x00e5 - %x" % self.get_register(0x00e5))
        U.toLog(2,"0x00e6 - %x" % self.get_register(0x00e6))
        U.toLog(2,"0x00e7 - %x" % self.get_register(0x00e7))
        U.toLog(2,"0x00f5 - %x" % self.get_register(0x00f5))
        U.toLog(2,"0x00d9 - %x" % self.get_register(0x00d9))
        U.toLog(2,"0x00db - %x" % self.get_register(0x00db))
        U.toLog(2,"0x00dc - %x" % self.get_register(0x00dc))
        U.toLog(2,"0x00dd - %x" % self.get_register(0x00dd))
        U.toLog(2,"0x009f - %x" % self.get_register(0x009f))
        U.toLog(2,"0x00a3 - %x" % self.get_register(0x00a3))
        U.toLog(2,"0x00b7 - %x" % self.get_register(0x00b7))
        U.toLog(2,"0x00bb - %x" % self.get_register(0x00bb))
        U.toLog(2,"0x00b2 - %x" % self.get_register(0x00b2))
        U.toLog(2,"0x00ca - %x" % self.get_register(0x00ca))
        U.toLog(2,"0x0198 - %x" % self.get_register(0x0198))
        U.toLog(2,"0x01b0 - %x" % self.get_register(0x01b0))
        U.toLog(2,"0x01ad - %x" % self.get_register(0x01ad))
        U.toLog(2,"0x00ff - %x" % self.get_register(0x00ff))
        U.toLog(2,"0x0100 - %x" % self.get_register(0x0100))
        U.toLog(2,"0x0199 - %x" % self.get_register(0x0199))
        U.toLog(2,"0x01a6 - %x" % self.get_register(0x01a6))
        U.toLog(2,"0x01ac - %x" % self.get_register(0x01ac))
        U.toLog(2,"0x01a7 - %x" % self.get_register(0x01a7))
        U.toLog(2,"0x0030 - %x" % self.get_register(0x0030))

    def default_settings(self):
        # Recommended settings from datasheet
        # http://www.st.com/st-web-ui/static/active/en/resource/technical/document/application_note/DM00122600.pdf
        # Set GPIO1 high when sample complete
        self.set_register(self.__VL6180X_SYSTEM_MODE_GPIO1, 0x10)
        # Set Avg sample period
        self.set_register(self.__VL6180X_READOUT_AVERAGING_SAMPLE_PERIOD, 0x30)
        # Set the ALS gain   0: ALS Gain = 20
        #                    1: ALS Gain = 10
        #                    2: ALS Gain = 5.0
        #                    3: ALS Gain = 2.5
        #                    4: ALS Gain = 1.67
        #                    5: ALS Gain = 1.25
        #                    6: ALS Gain = 1.0
        #                    7: ALS Gain = 40
        self.set_register(self.__VL6180X_SYSALS_ANALOGUE_GAIN, 0b10000000)  ##set to 10
        # Set auto calibration period (Max = 255)/(OFF = 0)
        self.set_register(self.__VL6180X_SYSRANGE_VHV_REPEAT_RATE, 0xFF)
        # Set ALS integration time to 100ms
        ## 0=1ms   63 = 100 msec
        self.set_register(self.__VL6180X_SYSALS_INTEGRATION_PERIOD, 0x63)
        # perform a single temperature calibration
        self.set_register(self.__VL6180X_SYSRANGE_VHV_RECALIBRATE, 0x01)

        # Optional settings from datasheet
        # http://www.st.com/st-web-ui/static/active/en/resource/technical/document/application_note/DM00122600.pdf
        # Set default ranging inter-measurement period to 100ms
        self.set_register(self.__VL6180X_SYSRANGE_INTERMEASUREMENT_PERIOD, 0x09)
        # Set default ALS inter-measurement period to 100ms
        self.set_register(self.__VL6180X_SYSALS_INTERMEASUREMENT_PERIOD, 0x09)
        # Configures interrupt on 'New Sample Ready threshold event' 
        self.set_register(self.__VL6180X_SYSTEM_INTERRUPT_CONFIG_GPIO,0x00)# 0x24)

        # Additional settings defaults from community
        self.set_register(      self.__VL6180X_SYSRANGE_MAX_CONVERGENCE_TIME, 0x32)
        self.set_register(      self.__VL6180X_SYSRANGE_RANGE_CHECK_ENABLES, 0x10 | 0x01)
        #self.set_register_16bit(self.__VL6180X_SYSRANGE_EARLY_CONVERGENCE_ESTIMATE, 0x7B)
        #self.set_register_16bit(self.__VL6180X_SYSALS_INTEGRATION_PERIOD, 0x64)
        self.set_register(      self.__VL6180X_SYSALS_ANALOGUE_GAIN, 0x40)
        self.set_register(      self.__VL6180X_FIRMWARE_RESULT_SCALER, 0x01)

        U.toLog(2,"Default settings:")
        U.toLog(2,"SYSTEM_MODE_GPIO1 - %x" %                   self.get_register(      self.__VL6180X_SYSTEM_MODE_GPIO1))
        U.toLog(2,"READOUT_AVERAGING_SAMPLE_PERIOD - %x" %     self.get_register(      self.__VL6180X_READOUT_AVERAGING_SAMPLE_PERIOD))
        U.toLog(2,"SYSALS_ANALOGUE_GAIN - %x" %                self.get_register(      self.__VL6180X_SYSALS_ANALOGUE_GAIN))
        U.toLog(2,"SYSRANGE_VHV_REPEAT_RATE - %x" %            self.get_register(      self.__VL6180X_SYSRANGE_VHV_REPEAT_RATE))
        U.toLog(2,"SYSALS_INTEGRATION_PERIOD - %x" %           self.get_register(      self.__VL6180X_SYSALS_INTEGRATION_PERIOD))
        U.toLog(2,"SYSRANGE_VHV_RECALIBRATE - %x" %            self.get_register      (self.__VL6180X_SYSRANGE_VHV_RECALIBRATE))
        U.toLog(2,"SYSRANGE_INTERMEASUREMENT_PERIOD - %x" %    self.get_register(      self.__VL6180X_SYSRANGE_INTERMEASUREMENT_PERIOD))
        U.toLog(2,"SYSALS_INTERMEASUREMENT_PERIOD - %x" %      self.get_register(      self.__VL6180X_SYSALS_INTERMEASUREMENT_PERIOD))
        U.toLog(2,"SYSTEM_INTERRUPT_CONFIG_GPIO - %x" %        self.get_register(      self.__VL6180X_SYSTEM_INTERRUPT_CONFIG_GPIO))
        U.toLog(2,"SYSRANGE_MAX_CONVERGENCE_TIME - %x" %       self.get_register(      self.__VL6180X_SYSRANGE_MAX_CONVERGENCE_TIME))
        U.toLog(2,"SYSRANGE_RANGE_CHECK_ENABLES - %x" %        self.get_register(      self.__VL6180X_SYSRANGE_RANGE_CHECK_ENABLES))
        #U.toLog(2,"SYSRANGE_EARLY_CONVERGENCE_ESTIMATE - %x" % self.get_register_16bit(self.__VL6180X_SYSRANGE_EARLY_CONVERGENCE_ESTIMATE))
        #U.toLog(2,"SYSALS_INTEGRATION_PERIOD - %x" %           self.get_register_16bit(self.__VL6180X_SYSALS_INTEGRATION_PERIOD))
        U.toLog(2,"SYSALS_ANALOGUE_GAIN - %x" %                self.get_register(      self.__VL6180X_SYSALS_ANALOGUE_GAIN))
        U.toLog(2,"FIRMWARE_RESULT_SCALER - %x" %              self.get_register(      self.__VL6180X_FIRMWARE_RESULT_SCALER))

    def get_identification(self):

        self.idModel          = self.get_register(self.__VL6180X_IDENTIFICATION_MODEL_ID)
        self.idModelRevMajor  = self.get_register(self.__VL6180X_IDENTIFICATION_MODEL_REV_MAJOR)
        self.idModelRevMinor  = self.get_register(self.__VL6180X_IDENTIFICATION_MODEL_REV_MINOR)
        self.idModuleRevMajor = self.get_register(self.__VL6180X_IDENTIFICATION_MODULE_REV_MAJOR)
        self.idModuleRevMinor = self.get_register(self.__VL6180X_IDENTIFICATION_MODULE_REV_MINOR)

        self.idDate           = self.get_register_16bit(self.__VL6180X_IDENTIFICATION_DATE)
        self.idTime           = self.get_register_16bit(self.__VL6180X_IDENTIFICATION_TIME)

    def change_address(self, old_address, new_address):
        # NOTICE:  IT APPEARS THAT CHANGING THE ADDRESS IS NOT STORED IN NON-
        # VOLATILE MEMORY POWER CYCLING THE DEVICE REVERTS ADDRESS BACK TO 0X29

        if old_address == new_address:
            return old_address
        if new_address > 127:
            return old_address

        self.set_register(self.__VL6180X_I2C_SLAVE_DEVICE_ADDRESS, new_address)
        return self.get_register(self.__VL6180X_I2C_SLAVE_DEVICE_ADDRESS)

    def get_distance(self):
        # Start Single shot mode
        try: 
            self.set_register(self.__VL6180X_SYSRANGE_START, 0x01)
            time.sleep(0.05)
            distance = self.get_register(self.__VL6180X_RESULT_RANGE_VAL)
            U.toLog(2, "Range status: " +unicode(self.get_register(self.__VL6180X_RESULT_RANGE_STATUS) & 0xF1)+";  distance="  +unicode(distance)+" mm")
            self.set_register(self.__VL6180X_SYSTEM_INTERRUPT_CLEAR, 0x07)
            return distance
        except  Exception, e:
            U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        return -1

    def get_ambient_light(self, lastGain):

        try:
            # First load in Gain we are using, do it every time in case someone
            # changes it on us.
            # Note: Upper nibble should be set to 0x4 i.e. for ALS gain
            # of 1.0 write 0x46

            # Set the ALS gain, defaults to 20.
            # If gain is in the dictionary (defined in init()) it returns the value
            # of the constant otherwise it returns the value for gain 20.
            # This saves a lot of if/elif/else code!
            gL  = lastGain[0]
            als_calculated =0
            iPeriod = lastGain[1]

            maxItterations =0
            while True:     
                    if maxItterations > 5: break
                    maxItterations +=1
                    newG = self.gainList[gL]
                    self.set_register(self.__VL6180X_SYSALS_INTEGRATION_PERIOD, iPeriod &0xff)
                    if newG not in self.ALS_GAIN_ACTUAL:
                       U.toLog(-1,"Invalid gain setting:"+unicode(newG)+"  Setting to 20.  " , unicode( self.ALS_GAIN_ACTUAL))
                    als_gain_actual = self.ALS_GAIN_ACTUAL.setdefault(newG, 20)

                    reg = self.ALS_GAIN_REG.setdefault(newG, self.__ALS_GAIN_20)
                    self.set_register(self.__VL6180X_SYSALS_ANALOGUE_GAIN,(0x40 | self.ALS_GAIN_REG.setdefault(newG, 20)))

                    # Start ALS Measurement
                    self.set_register(self.__VL6180X_SYSALS_START, 0x01) # single shot


                    # Retrieve the Raw ALS value from the sensor
                    if iPeriod == 63: nn=20
                    else:             nn=3
                    wTime=0
                    for ii in range(nn):
                        time.sleep(0.05)
                        wTime+=0.05
                        convReady = self.get_register(self.__VL6180X_RESULT_ALS_STATUS)
                        if convReady & 0xF1 ==1:
                            U.toLog(2, "ALS status:  ok")
                            break
                        else:
                            U.toLog(3, "ALS status:  busy: "+ unicode(convReady))
                    # read ALS
                    als_raw = self.get_register_16bit(self.__VL6180X_RESULT_ALS_VAL)  ## is 0x0050
                    # clear ineterrupts
                    self.set_register(self.__VL6180X_SYSTEM_INTERRUPT_CLEAR, 0x07)

                    # Get Integration Period for calculation, we do this every time in case
                    # someone changes it on us.
                    als_integration_period_raw = self.get_register(self.__VL6180X_SYSALS_INTEGRATION_PERIOD)
                    if als_integration_period_raw ==0: als_integration_period = 1.
                    else:                              als_integration_period = 100.0 

                    # Calculate actual LUX from application note
                    als_calculated         = 100*0.32 * als_raw / (als_gain_actual * als_integration_period)
                    #print "convReady",convReady,"als_gain_actual",als_gain_actual,"newG",newG ,"wTime",wTime, "reg",reg, "als_integration_period_raw",als_integration_period_raw,"int",iPeriod, "als_raw",als_raw, "als_calculated",als_calculated
                    if als_raw > 1024 and als_raw  < 65000: break # enough bits

                    if als_raw  >= 65000: # overflow
                        if iPeriod == 1 and gL == 0: break
                        if iPeriod == 63:
                            iPeriod = 1
                            gL = 4
                        elif gL > 0: 
                            gL=0
                        else:
                            break # its just overflow
                    else:
                        if iPeriod ==63 and gL == 7: break
                        
                        if iPeriod == 1:
                            if als_raw < 400:
                                iPeriod =63
                                if als_raw < 50:
                                    gL = min(7,gL+2)
                            elif gL > 5:
                                iPeriod =63
                                gL = 0
                            else:
                                gL = 7
                        else:
                            gL=7
                    if gL == lastGain[0] and iPeriod == lastGain[1]:
                        break
                    lastGain=[gL,iPeriod]
            lastGain =[gL,iPeriod]
            #print " ret:",als_calculated,als_raw, lastGain
            return als_calculated,  lastGain
        except  Exception, e:
            U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        return 0,0
        
    def get_register(self, register_address):
        a1 = (register_address >> 8) & 0xFF
        a0 = register_address & 0xFF
        self.i2c.write_i2c_block_data(self.address, a1, [a0])
        data = self.i2c.read_byte(self.address)
        return data

    def get_register_16bit(self, register_address):
        a1 = (register_address >> 8) & 0xFF
        a0 = register_address & 0xFF
        self.i2c.write_i2c_block_data(self.address, a1, [a0])
        data0 = self.i2c.read_byte(self.address)
        data1 = self.i2c.read_byte(self.address)
        return (data0 << 8) | (data1 & 0xFF)

    def set_register(self, register_address, data):
        a1 = (register_address >> 8) & 0xFF
        a0 = register_address & 0xFF
        self.i2c.write_i2c_block_data(self.address, a1, [a0, (data & 0xFF)])

    def set_register_16bit(self, register_address, data):
        a1 = (register_address >> 8) & 0xFF
        a0 = register_address & 0xFF
        d1 = (data >> 8) & 0xFF
        d0 = data & 0xFF
        self.i2c.write_i2c_block_data(self.address, a1, [a0, d1, d0])


#################################
def getDistance():
    global sensor, sensors,  tof, badSensor
    global actionDistanceOld, actionShortDistance, actionShortDistanceLimit, actionMediumDistance, actionMediumDistanceLimit, actionLongDistance, actionLongDistanceLimit

    try:
        for ii in range(2):
            distance = tof.get_distance()
            if (distance > 0):
                    distance  = min(distance,200.)/10. # = 20cm  = 200 mm 
                    badSensor = 0
                    #print " bf action test ", actionShortDistance, actionMediumDistance, actionLongDistance
                    if actionShortDistance !="":
                        if actionDistanceOld !="short"  and distance <= actionShortDistanceLimit:
                            if actionDistanceOld != "short":
                                os.system(actionShortDistance)
                                actionDistanceOld ="short"

                    if actionMediumDistance !="":
                        if actionDistanceOld !="medium"  and distance >  actionShortDistanceLimit and distance < actionLongDistanceLimit:
                            if actionDistanceOld != "medium":
                                os.system(actionMediumDistance)
                                actionDistanceOld ="medium"
                            
                    if actionLongDistance !="":
                        if actionDistanceOld !="long"    and distance >=  actionLongDistanceLimit:
                            if actionDistanceOld != "long":
                                os.system(actionLongDistance)
                                actionDistanceOld ="long"
                    return  ("%7.1f"%(distance)).strip() #  return in cm/lux

        if badSensor >3: return "badSensor"
    except  Exception, e:
            U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
            U.toLog(-1, u"distance>>" + unicode(distance)+"<<")
    return ""        



#################################
def getLight():
    global tof, badSensor, gain

    try:
        for ii in range(2):
            lux, gain      = tof.get_ambient_light(gain)
            
            if (lux > 0):
                    badSensor = 0
                    #print " bf action test ", actionShortDistance, actionMediumDistance, actionLongDistance
                    return  ("%10d"%(lux)).strip() #  return in cm/lux

        if badSensor >3: return "badSensor"
    except  Exception, e:
            U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
            U.toLog(-1, u"lux>>" + unicode(lux)+"<<")
    return ""        




############################################
global gain
global sensor, sensors, first, tof, badSensor
global actionDistanceOld, actionShortDistance, actionShortDistanceLimit, actionMediumDistance, actionMediumDistanceLimit, actionLongDistance, actionLongDistanceLimit
global oldRaw,  lastRead
oldRaw                  = ""
lastRead                = 0


actionShortDistance         = ""
actionShortDistanceLimit    = 5.
actionMediumDistance        = ""
actionMediumDistanceLimit   = 10
actionLongDistance          = ""
actionLongDistanceLimit     = 20.
actionDistanceOld           = 0
distanceUnits               = "1.0"
gain                        = 20
G.debug                     = 5
first                       = False
loopCount                   = 0
sensorRefreshSecs           = 60
NSleep                      = 100
sensorList                  = []
sensors                     = {}
sensor                      = G.program
quick                       = False
dynamic                     = False
mode                        = 0
display                     = "0"
output                      = {}
badSensor                   = 0
sensorActive                = False
loopSleep                   = 0.1
gain                        = [5,1]

myPID       = str(os.getpid())
U.killOldPgm(myPID,G.program+".py")# kill old instances of myself if they are still running


if U.getIPNumber() > 0:
    time.sleep(10)
    exit()

readParams()

time.sleep(1)

lastRead = time.time()

U.echoLastAlive(G.program)

lastDist            = {}
lastData            = {}
lastTime            = {}
maxDeltaSpeed       = 40. # = mm/sec
lastSend            = 0
lastDisplay         = 0
lastRead            = time.time()
G.lastAliveSend     = time.time() -1000
lastLux   = -999999
lastLux2  = 0
distLast = -100
while True:
    try:
        tt = time.time()
        data={}
        data["sensors"]     = {}
        speed = 0
        distance = 0
        if sensor in sensors:
            for devId in sensors[sensor]:
                if devId not in lastDist: 
                    lastDist[devId] =-500.
                    lastTime[devId] =0.
                distance =getDistance()
                data["sensors"] = {sensor:{}}
                data["sensors"][sensor] = {devId:{}}
                if distance =="badSensor":
                    first=True
                    U.toLog(-1," bad sensor")
                    data["sensors"][sensor][devId]["distance"]="badSensor"
                    U.sendURL(data)
                    lastDist[devId] =-100.
                    continue
                elif distance !="" :
                    data["sensors"][sensor][devId]["distance"] = distance
                    dist   = float(distance)
                    delta  = dist-lastDist[devId]
                    deltaN  = abs(delta) / max (0.5,(dist+lastDist[devId])/2.)
                    if loopCount %20 == 0 or deltaN > 0.1:
                        lux = getLight()
                        if lux !="": 
                                data["sensors"][sensor][devId]["lux"] =lux
                                lastLux  = float(lux)
                    else:
                                data["sensors"][sensor][devId]["lux"] =lastLux
                    distLast = distance
                    deltaT =  max(tt   - lastTime[devId],0.01)
                    speed  =  delta / deltaT
                else:
                    continue

                if (  ( deltaN > deltaDist[devId] ) or 
                      (  (tt - abs(sensorRefreshSecs)) > G.lastAliveSend  or quick ) or 
                      ( speed > maxDeltaSpeed )  or 
                      ( abs(lastLux2 - lastLux)/ max(lastLux2 + lastLux,0.1) > 0.05 )  ): # 10%
                        lastLux2 = lastLux
                        data["sensors"][sensor][devId]["speed"]    = speed
                        U.sendURL(data)
                lastDist[devId]  = dist
                lastTime[devId]  = tt

                if displayEnable =="1" and  ( (deltaN > 0.05  and  tt - lastDisplay >1.)   or  tt - lastDisplay >10. or  quick):
                    lastDisplay = tt
                    DISP.displayDistance(dist, sensor, sensors, output, distanceUnits)
                    U.toLog(1, unicode(dist)+"  "+unicode(deltaDist) )   
                    #print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S"),sensor, dist , deltaDist   
        loopCount +=1

        U.makeDATfile(G.program, data)
        quick = U.checkNowFile(G.program)                
        U.echoLastAlive(G.program)

        if loopCount %40 ==0 and not quick:
            tt= time.time()
            if tt - lastRead > 5.:  
                readParams()
                lastRead = tt
        if not quick:
            time.sleep(loopSleep)
        
    except  Exception, e:
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        time.sleep(5.)
sys.exit(0)
