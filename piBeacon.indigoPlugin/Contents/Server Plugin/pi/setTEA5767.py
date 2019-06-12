#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.7 

import subprocess
import time
import sys
import smbus
import json,  os, time, datetime
import copy
import io
import fcntl # used to access I2C parameters like addresses

sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G
G.program = "setTEA5767"


###########


def readParams():
    global frequency, defFreq, mute, mono, highCut, noiseCancel, bandLimit, DTCon, PLLREF, XTAL,i2cAddress, HLSI,devIdFound

    global fastFreq, fastMute,fastMono, inp
    global oldRaw, lastRead
    try:

        inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
        if inp == "": return 
        if lastRead2 == lastRead: return 
        lastRead   = lastRead2
        if inpRaw == oldRaw: return 
        oldRaw     = inpRaw

        U.getGlobalParams(inp)
        if u"debugRPI"          in inp:  G.debug=              int(inp["debugRPI"]["debugRPIOUTPUT"])


        device = "setTEA5767"
        if device in inp["output"]:
            for devId in inp["output"][device]:
                input= inp["output"][device][devId][0]
                if u"mute"              in input:  mute=                 int(input["mute"])
                if u"mono"              in input:  mono=                 int(input["mono"])
                if u"highCut"           in input:  highCut=              int(input["highCut"])
                if u"noiseCancel"       in input:  noiseCancel=          int(input["noiseCancel"])
                if u"bandLimit"         in input:  bandLimit=            int(input["bandLimit"])
                if u"DTCon"             in input:  DTCon=                int(input["DTCon"])
                if u"PLLREF"            in input:  PLLREF=               int(input["PLLREF"])
                if u"XTAL"              in input:  XTAL=                 int(input["XTAL"])
                if u"defFreq"           in input:  
                                                   defFreq=            float(input["defFreq"])
                                                   frequency=          float(input["defFreq"])
                if u"HLSI"              in input:  HLSI=                 int(input["HLSI"])
                if u"i2cAddress"        in input:  i2cAddress=           int(input["i2cAddress"])
                devIdFound = devId
                break

        else:
            U.toLog(-1, u"stopping FM radio, no device defined in parameters file")
            exit()
    except  Exception, e:
        U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
    U.toLog(-1,  "FM Radio Module new params  from parameter file;  frequency: " + str(defFreq)+"  mute: "+ str(mute)+"  mono: "+ str(mono)+"  highCut: "+ str(highCut) +"  noiseCancel: " + str(noiseCancel)+"  DTCon: "+ str(DTCon)+"  PLLREF: "+ str(PLLREF) +"  HLSI: "+ str(HLSI)+"  XTAL: "+ str(XTAL))
    return
         

def readNew():
    global fastFreq, fastMute,fastMono,fastScan,fastMinSignal, inp, inpRawOld, newCommand, restart
    global defFreq, mute, mono, highCut, noiseCancel, bandLimit, DTCon, PLLREF, XTAL, HLSI, devIdFound

    inpNew,inpRaw = U.doRead(inFile=G.homeDir+G.program+".set")
    if inpNew == "": return
    try:    
        newCommand = True
        updateF = False 
        updateM = False
        updateO = False
        restart = False
        if u"frequency"           in inpNew:  
            fastFreq   = float(inpNew["frequency"])
            updateF    = True
        if u"mute"                in inpNew:  
            fastMute   = int(inpNew["mute"])
            updateM    = True
        if u"mono"                in inpNew:  
            fastMono   = int(inpNew["mono"])
            updateO    = True
        if u"scan"                in inpNew:  
            fastScan   = int(inpNew["scan"])
        if u"minSignal"                in inpNew:  
            fastMinSignal   = int(inpNew["minSignal"])
        if u"restart"                in inpNew:  
            restart   = (inpNew["restart"] =="1")
        if len(unicode(inp))> 200 and (updateF or updateM or updateO) and fastScan !=1:
            device = "setTEA5767"
            if device in inp["output"]:
                for devId in inp["output"][device]:
                    if updateM:
                        inp["output"][device][devId][0]["mute"]     = inpNew["mute"]
                    if updateF:
                        inp["output"][device][devId][0]["defFreq"]  = inpNew["frequency"]
                    if updateO:
                        inp["output"][device][devId][0]["mono"]     = inpNew["mono"]
                    f=open(G.homeDir+"parameters","w")
                    f.write(json.dumps(inp,sort_keys=True, indent=2))
                    f.close()
                    break
        os.remove(G.homeDir+G.program+".set")
        if restart:
            U.toLog(0, u"restarting radio")
            time.sleep(0.1)
            os.system("/usr/bin/python "+G.homeDir+G.program+".py &")
    
    except  Exception, e:
        U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
    U.toLog(-1,  "FM Radio Module new params from menue/action; frequency: " + str(fastFreq)+"  mute: "+ str(fastMute)+"  mono: "+ str(fastMono)+" ////  highCut: "+ str(highCut) +"  noiseCancel: " + str(noiseCancel)+"  DTCon: "+ str(DTCon)+"  PLLREF: "+ str(PLLREF) +"  HLSI: "+ str(HLSI)+"  XTAL: "+ str(XTAL) )
   
class tea5767:
    ### tea flags
    ## write flags  #############
    TEA_1_MUTE                  = 0b10000000   # 1 = mute, 0 = output enabled 0b00000000 mute enabled after reset)
    TEA_1_SEARCHMODE            = 0b01000000   # 1 = Search mode enabled
    # nothing for byte 2
    TEA_3_SEARCHUPDOWN          = 0b10000000   # 1 = search up, 0 = search down
    TEA_3_SEARCHSTOPLEVEL1      = 0b01000000   # 10 = mid level 0b00000000 ADC = 7), 11 = high level 0b00000000 ADC = 10)
    TEA_3_SEARCHSTOPLEVEL0      = 0b00100000   # 01 = low level 0b00000000 ADC = 5) ,00 = invalid
    TEA_3_HLSI                  = 0b00010000   # 1 = high side LO injection, 0 = low side LO injection
    TEA_3_MONOTOSTEREO          = 0b00001000   # 1 = force mono, 0 = stereo on
    TEA_3_MUTERIGHT             = 0b00000100   # 1 = mute right audio, 0 = enabled
    TEA_3_MUTELEFT              = 0b00000010   # 1 = mute left audio, 0 = enabled

    TEA_4_STANDBY               = 0b01000000   # 1 = standby mode
    TEA_4_BANDLIMITS            = 0b00100000   # 1 = Japanese FM band, 0 = US/Europe
    TEA_4_XTAL                  = 0b00010000   #   Combined with PLLREF in byte 5 0b00000000 set to 1 for 32.768kHz crystal)
    TEA_4_SOFTMUTE              = 0b00001000   # 1 = soft mute enabled
    TEA_4_HIGHCUTCONTROL        = 0b00000100   # 1 = HCC enabled
    TEA_4_STEREONOISECANCEL     = 0b00000010   # 1 = stereo noise cancelling enabled

    TEA_5_PLLREF                = 0b10000000   # 1 = 6.5MHz PLL ref freq. enabled 0b00000000 set to 0 for 32.768kHz crystal)
    TEA_5_DEEMPHASISTIMECONST   = 0b01000000   # 1 = DTC is 75us, 0 = 50us

    ## read flags  ############
    TEA_1_READYFLAG             = 0b10000000   # 1 = station found or band-limit reached, 0 = no station found
    TEA_1_BANDLIMITFLAG         = 0b01000000   # 1 = band limit has been reached, 0 = band limit not reached
    # nothing for byte2 
    TEA_3_STEREOINDICATOR       = 0b10000000   # 1 = stereo reception, 0 = mono reception

    TEA_4_ADCLEVELOUTPUTMASK    = 0b11110000   # ADC output level
    TEA_4_CHIPIDMASK            = 0b00001111   # These bits must be set to 0!
    # nothing for byte 5


    long_timeout    = 1.5 # the timeout needed to query readings and calibrations
    short_timeout   = .3 # timeout for regular commands

    def __init__(self, i2cAddress = 0x60, bus = 1):
        self.bus  = smbus.SMBus(1)
        self.add  = i2cAddress# I2C address circuit 
        U.toLog(0, u"FM Radio Module TEA5767 init")
        print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+ " FM Radio Module TEA5767 init"

        # open two file streams, one for reading and one for writing
        # the specific I2C channel is selected with bus
        # it is usually 1, except for older revisions where its 0
        # wb and rb indicate binary read and write

        self.file_read  = io.open("/dev/i2c-"+str(bus), "rb", buffering = 0)
        #self.file_write = io.open("/dev/i2c-"+str(bus), "wb", buffering = 0)

        # initializes I2C to either a user specified or default address
        # set the I2C communications to the slave specified by the address
        # The commands for I2C dev using the ioctl functions are specified in
        # the i2c-dev.h file from i2c-tools
        I2C_SLAVE = 0x703  # given, do not change
        fcntl.ioctl(self.file_read,  I2C_SLAVE, self.add)
        #fcntl.ioctl(self.file_write, I2C_SLAVE, self.add)


    def close(self):
        self.file_read.close()
        #self.file_write.close()

    #script to get ready
    def init(self):
        self.bus.write_byte(self.add, 0x00)
        time.sleep(1)

    def writeToDevice(self,freq, mute=0,mono=0,highCut=1,noiseCancel=1,bandLimit=0,DTCon=1,PLLREF=0,XTAL=1,HLSI=1, scan=0,searchLevel=1):
        U.toLog(-1,  "FM Radio Module frequency: " + str(freq)+
         "  mute: "        + str(mute)    +
         "  mono: "        + str(mono)+
         "  highCut: "     + str(highCut) + 
         "  noiseCancel: " + str(noiseCancel)+
         "  DTCon: "       + str(DTCon)+
         "  PLLREF: "      + str(PLLREF)  + 
         "  HLSI: "        + str(HLSI)    + 
         "  XTAL: "        + str(XTAL)+
         "  scan: "        + str(scan)+
         "  searchLevel: " + str(searchLevel))
        # Frequency distribution for two bytes (according to the data sheet) 
        if HLSI==1:
            freq14bit = int (4 * (freq * 1000000 + 225000) / 32768)
        else:
            freq14bit = int (4 * (freq * 1000000 - 225000) / 32768)
        
        freqH = freq14bit >>8          # move to low byte
        freqH = freqH     & 0b00111111 # mask non freq bits 
        freqL = freq14bit & 0xFF       # clear upper byte

        data = [0 for i in range(4)]
        data[0]                             = freqL
        data[1]                             = 0b00000000  ## searchmode, stoplev1, stoplev2, highsideInjection, mono=1, muteRight=1,muteLeft=1, softwareIntf=0 
        data[2]                             = 0b00000000
        data[3]                             = 0b00000000
        #
        if(mute==1):        
                                freqH   = freqH  | tea5767.TEA_1_MUTE  
                                data[1] = data[1]| tea5767.TEA_3_MUTERIGHT  
                                data[1] = data[1]| tea5767.TEA_3_MUTERIGHT  
                                data[1] = data[1]| tea5767.TEA_3_MUTELEFT 
                            
        if scan ==1 :           
                                freqH   = freqH  | tea5767.TEA_1_SEARCHMODE  
                                data[1] = data[1]| tea5767.TEA_3_SEARCHUPDOWN  
        
        if scan ==1 :  
            if   searchLevel==1:data[1] = data[1]| tea5767.TEA_3_SEARCHSTOPLEVEL0  
            elif searchLevel==2:data[1] = data[1]| tea5767.TEA_3_SEARCHSTOPLEVEL1  
            elif searchLevel==3:data[1] = data[1]| tea5767.TEA_3_SEARCHSTOPLEVEL1  |  tea5767.TEA_3_SEARCHSTOPLEVEL0
            else:               data[1] = data[1]| tea5767.TEA_3_SEARCHSTOPLEVEL0  

        if(mono==1):            data[1] = data[1]| tea5767.TEA_3_MONOTOSTEREO

        if(HLSI==1):            data[1] = data[1]| tea5767.TEA_3_HLSI  


        if(noiseCancel==1):     data[2] = data[2]| tea5767.TEA_4_STEREONOISECANCEL #  switch on noise cancel

        if(highCut==1):         data[2] = data[2]| tea5767.TEA_4_HIGHCUTCONTROL #  switch on high cut

        if(bandLimit==1):       data[2] = data[2]| tea5767.TEA_4_BANDLIMITS #  for US and Europe, japan=0

        if(XTAL==1):            data[2] = data[2]| tea5767.TEA_4_XTAL #  fclock freq = pllref 0=; 1= clockf = 32768


        if(DTCon==1):           data[3] = data[3]| tea5767.TEA_5_DEEMPHASISTIMECONST #  

        if(PLLREF==1):          data[3] = data[3]| tea5767.TEA_5_PLLREF #  




        for ii in range(10):
            try:
                self.bus.write_i2c_block_data(self.add, freqH, data) # Setting a new frequency to the circuit 
                break
            except Exception , e:
                print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+" write error" , e

        if scan ==1 :  
            time.sleep(0.3)
            ret = self.file_read.read(5)
            data      = bytearray(ret)
            RF        = data[0]>> 7
            BLF       = (data[0]&   0b01000000) >> 6
            Stero     = data[2]>>7
            Signal    = data[3]>>4
            chip      = (data[3] & 0b00001110 ) >>1
            
            freqH = (data[0] & 0b00111111) <<8 
            freqT = freqH + data[1]
            if HLSI==1:
                freqR = ((32768/4)* freqT - 225000) /1000000.
            else:
                freqR = ((32768/4)* freqT + 225000) /1000000.
            freqR = round(freqR,1)
            res={}
            if Signal > 9:
                res = {"freq":freqR,"Signal":Signal,"Stero":Stero, "BLF":BLF}
            #print "scan data returned", [format(data[kk],'#010b') for kk in range(5)]
            #print "sca.. freq", freq, freqR, "RF", RF, "BLF" ,BLF,"Stero" ,Stero,"Signal" ,Signal,"chip" ,chip
            return res


    def off(self):
        self.init()


######### main ######
global defFreq, mute, mono, highCut, noiseCancel, bandLimit, DTCon, PLLREF, XTAL, i2cAddress, HLSI, devIdFound, newCommand
global fastFreq, fastMute, fastMono,fastMinSignal, inp, restart
global oldRaw,  lastRead
oldRaw                  = ""
lastRead                = 0

restart        = False
sensor         = "setTEA5767"
i2cAddress     = 0x60
defFreq        = 90.1
mute           = 0
mono           = 0
highCut        = 1
noiseCancel    = 1
bandLimit      = 0
DTCon          = 1
PLLREF         = 0
XTAL           = 1
frequency      = defFreq
HLSI           = 1
oldfrequency   = frequency
oldmute        = mute
oldmono        = mono
oldhighCut     = highCut
oldnoiseCancel = noiseCancel
oldbandLimit   = bandLimit
oldDTCon       = DTCon
oldPLLREF      = PLLREF
oldXTAL        = XTAL
oldHLSI        = HLSI

fastFreq       = ""
fastMute       = ""
fastMono       = ""
fastScan       = 0
fastMinSignal  = 10
minSignal      = fastMinSignal 
devIdFound     = "0"
newCommand     = False

myPID          = str(os.getpid())
readParams()
U.toLog(0, G.program+"  command :" + unicode(sys.argv))


command =""
try:
    if len(sys.argv) >1:
        command = json.loads(sys.argv[1])
except:
    pass

lastAlive      = time.time()
os.system("echo "+str(time.time())+" > "+ G.homeDir+"temp/alive."+sensor)

frequency       =  defFreq
if "frequency" in command:
    fastFreq    = float(command["frequency"])
if "mute" in command:
    fastMute    = float(command["mute"])

U.killOldPgm(myPID,G.program+".py")# del old instances of myself if they are still running
   
if "startAtDateTime" in command:
    try:
        delayStart = max(0,U.calcStartTime(command,"startAtDateTime")-time.time())
        if delayStart > 0:
            U.toLog(2, "delayStart delayed by: "+ str(delayStart))
            time.sleep(delayStart)
    except:
        pass

lastAlive      = time.time()
U.echoLastAlive(G.program)

radio = tea5767(i2cAddress = i2cAddress)
if restart: radio.init()

radio.writeToDevice(frequency, mute=mute,mono=mono,highCut=highCut,noiseCancel=noiseCancel,bandLimit=bandLimit,DTCon=DTCon,PLLREF=PLLREF,XTAL=XTAL,HLSI=HLSI)
oldfrequency   = frequency
oldmute        = mute
oldmono        = mono
oldhighCut     = highCut
oldnoiseCancel = noiseCancel
oldbandLimit   = bandLimit
oldDTCon       = DTCon
oldPLLREF      = PLLREF
oldXTAL        = XTAL
oldHLSI        = HLSI

print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+ " FM Radio Module TEA5767 radio v 4.2"

lastParams     = time.time()
while (True):
    try:
        tt = time.time()
        if fastMute !="": mute      = fastMute
        if fastFreq !="": frequency = fastFreq
        if fastMono !="": mono      = fastMono


    
        if (newCommand or frequency!=oldfrequency or mute!=oldmute or mono!=oldmono or highCut!=oldhighCut or noiseCancel!=oldnoiseCancel or bandLimit!=oldbandLimit or DTCon!=oldDTCon or PLLREF!=oldPLLREF or XTAL!=oldXTAL or oldHLSI != HLSI):
            if frequency!=oldfrequency:
                radio.writeToDevice(oldfrequency, mute=1,mono=mono,highCut=highCut,noiseCancel=noiseCancel,bandLimit=bandLimit,DTCon=DTCon,PLLREF=PLLREF,XTAL=XTAL,HLSI=HLSI)
                radio.writeToDevice(frequency,    mute=1,mono=mono,highCut=highCut,noiseCancel=noiseCancel,bandLimit=bandLimit,DTCon=DTCon,PLLREF=PLLREF,XTAL=XTAL,HLSI=HLSI)
                time.sleep(0.3)
            radio.writeToDevice(frequency, mute=mute,mono=mono,highCut=highCut,noiseCancel=noiseCancel,bandLimit=bandLimit,DTCon=DTCon,PLLREF=PLLREF,XTAL=XTAL,HLSI=HLSI)
            if fastScan !=1: 
                oldfrequency   = frequency
            oldmute        = mute
            oldmono        = mono
            oldhighCut     = highCut
            oldnoiseCancel = noiseCancel
            oldbandLimit   = bandLimit
            oldDTCon       = DTCon
            oldPLLREF      = PLLREF
            oldXTAL        = XTAL
            oldHLSI        = HLSI
            newCommand     = False
        if (fastScan ==1):
            fastScan       = 0
            if fastMinSignal > 0:
                minSignal = fastMinSignal
            fastMinSignal  = 0
            f= frequency
            okFrequencies= []
            maxSignal = 0
            maxFreq   = 90.1
            endFreq   = 107.0
            for iii in range(200):
                res = radio.writeToDevice(f, mute=1,bandLimit=bandLimit,scan=1,searchLevel=3)
                if res!={}:
                    if res["Signal"] > 9:
                        f  = res["freq"] +0.1
                        if res["Signal"] >= minSignal:
                            if res["Signal"] > maxSignal:
                                maxSignal = res["Signal"]
                                maxFreq   = res["freq"]
                            okFrequencies.append(res)
                    if res["BLF"] & 0b00000001:     
                        break
                else:
                    f +=0.1
                if f > endFreq: break
                time.sleep(0.1)
            frequency = oldfrequency 
            radio.writeToDevice(frequency, mute=mute,mono=mono,highCut=highCut,noiseCancel=noiseCancel,bandLimit=bandLimit,DTCon=DTCon,PLLREF=PLLREF,XTAL=XTAL,HLSI=HLSI)
            oldmute        = mute
            oldmono        = mono
            oldhighCut     = highCut
            oldnoiseCancel = noiseCancel
            oldbandLimit   = bandLimit
            oldDTCon       = DTCon
            oldPLLREF      = PLLREF
            oldXTAL        = XTAL
            oldHLSI        = HLSI
            if len(okFrequencies) > 0:
                #for ii in range(len(okFrequencies)):
                #    print ii, okFrequencies[ii]
                data={}
                data["setTEA5767"]={}
                data["setTEA5767"][devIdFound] = {"channels":okFrequencies}
                U.sendURL({"sensors":data})
        fastMute =""
        fastFreq =""
        fastMono =""

        
        time.sleep(1)
        readNew()
        if tt- lastParams > 5:
            readParams()
            lastParams= tt
            U.echoLastAlive(G.program)

    except  Exception, e:
        U.toLog(-1, u"in Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
    
    




