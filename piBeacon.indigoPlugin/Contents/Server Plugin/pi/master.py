#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.7
##
##  1. start beaconloop.py
##  2. loop and check if beaconloop is still alive , if not reboot
##  3. check if we can ping the server, if not  reboot 
##
##

import sys, os, subprocess, copy
import time,datetime
import json
import RPi.GPIO as GPIO

sys.path.append(os.getcwd())
import  piBeaconGlobals as G
import  piBeaconUtils   as U
G.program = "master"




################################


def sendi2cToPlugin():
    global lastI2C
    try:
        i2c= U.geti2c()
        ret = subprocess.Popen("/opt/vc/bin/vcgencmd measure_temp" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
        try:    temp = ret.split("=")[1].split("'")[0]
        except: temp = 0
        U.sendURL(data={"i2c":i2c,"temp":temp},sendAlive="alive")
    except  Exception, e :
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),doPrint=True)
    return 



def cleanupOldFiles():


    os.system("rm -r "+G.homeDir+"logs                  >/dev/null 2>&1")
    os.system("rm    "+G.homeDir+"iPhoneBLE.py          >/dev/null 2>&1")
    os.system("rm    "+G.homeDir+"rejects.*             >/dev/null 2>&1")
    os.system("rm    "+G.homeDir+"logfile               >/dev/null 2>&1")
    os.system("rm    "+G.homeDir+"logfile-1             >/dev/null 2>&1")
    os.system("rm    "+G.homeDir+"call-log              >/dev/null 2>&1")
    os.system("rm    "+G.homeDir+"alive                 >/dev/null 2>&1")
    os.system("rm    "+G.homeDir+"master.log            >/dev/null 2>&1")
    os.system("rm    "+G.homeDir+"interface             >/dev/null 2>&1")
    os.system("rm    "+G.homeDir+"logfile               >/dev/null 2>&1")
    os.system("rm    "+G.homeDir+"beaconloop            >/dev/null 2>&1")
    os.system("rm    "+G.homeDir+"DHT.dat               >/dev/null 2>&1")
    os.system("rm    "+G.homeDir+"DHT.py                >/dev/null 2>&1")
    os.system("rm    "+G.homeDir+"wire18B20.py          >/dev/null 2>&1")
    os.system("rm    "+G.homeDir+"wire18B20.dat         >/dev/null 2>&1")
    os.system("rm    "+G.homeDir+"errlog                >/dev/null 2>&1")

    restart=False
    for ff in G.parameterFileList:
        if "beacon_" in ff and "parameters" not in ff:
            rmFile= ff.split("_")[1]
            if os.path.isfile(G.homeDir+rmFile):
                restart = True
                os.system("rm    "+G.homeDir+rmFile+" >/dev/null 2>&1")
    return restart




    
def readNewParams(force=False):
        global enableRebootCheck,  restart,sensorList,rPiCommandPORT, firstRead
        global sensorEnabled, enableiBeacons, beforeLoop, cAddress,rebootHour,rebooted,BLEserial,BLEserialOLD,sensors,enableShutDownSwitch, rebootWatchDogTime
        global shutDownPinInput, shutDownPinOutput,sensorAlive,useRamDiskForLogfiles, displayActive
        global actions, output
        global lastAlive, neopixelActive, neopixelClockActive, tea5767Active, getSensorsActive
        global activePGMdict, bluetoothONoff
        global oldRaw,  lastRead

        
        BLEserialOLD= BLEserial

        inp,inpRaw,lastRead2 = U.doRead(lastTimeStamp=lastRead)
        if not force:
            if inp == "": return
            if lastRead2 == lastRead: return
            lastRead  = lastRead2
            if inpRaw == oldRaw: return
        lastRead   = lastRead2
        oldRaw     = inpRaw

        sensorsOld    = copy.copy(sensors)
        oldSensorList = copy.copy(sensorList)
        rPiRestartCommand =""
            
        U.getGlobalParams(inp)
        if "debugRPI"               in inp:  G.debug=             int(inp["debugRPI"]["debugRPICALL"])
        if u"BLEserial"             in inp:  BLEserial =             (inp["BLEserial"])
        if u"enableRebootCheck"     in inp:  enableRebootCheck=      (inp["enableRebootCheck"])
        if u"enableiBeacons"        in inp:  enableiBeacons=         (inp["enableiBeacons"])
        if u"cAddress"              in inp:  cAddress=                inp["cAddress"]
        if u"rebootHour"            in inp:  rebootHour=          int(inp["rebootHour"])
        if u"sensors"               in inp:  sensors =               (inp["sensors"])
        if u"useRamDiskForLogfiles" in inp:  useRamDiskForLogfiles =  inp["useRamDiskForLogfiles"]
        if u"actions"               in inp:  actions               =  inp["actions"]
        if u"useRTC"                in inp:  U.setUpRTC(inp["useRTC"])
        

        if u"bluetoothONoff"             in inp:
            if bluetoothONoff != inp["bluetoothONoff"]:
                if inp["bluetoothONoff"].lower() =="on":
                    os.system("rfkill unblock bluetooth")
                    os.system("systemctl enable hciuart")
                    time.sleep(20)
                    U.sendRebootHTML("switch bluetooth back on ",reboot=True)
                else:
                    if U.pgmStillRunning("/usr/lib/bluetooth/bluetoothd"):
                        U.toLog(-1,"switching blue tooth stack off ")
                        os.system("rfkill block bluetooth")
                        os.system("systemctl disable hciuart")
                        U.killOldPgm(myPID,"/usr/lib/bluetooth/bluetoothd")
                bluetoothONoff = inp["bluetoothONoff"]

        sensorList =""
        for sensor in sensors:
            sensorList+=sensor+","
        
        displayActive  = False
        neopixelActive = False
        neopixelClockActive = False
        if "output"             in inp:  
            output=               (inp["output"])
            
            if "display" in output:
                for devid in output["display"]:
                    ddd = output["display"][devid][0]
                    #print ddd
                    if "i2cAddress" not in ddd: continue
                    if "devType"    not in ddd: continue
                    displayActive =True
                    break
                    
            if "neopixel" in output:
                for devid in output["neopixel"]:
                    ddd = output["neopixel"][devid][0]
                    #print ddd
                    if "signalPin"  not in ddd: continue
                    if "devType"    not in ddd: continue
                    if not neopixelActive:
                        neopixelActive =True
                        checkIfNeopixelIsRunning(pgm= "neopixel")
                    U.toLog(1, "setting neopixel = true") 
                    break
                    
            if "neopixelClock" in output:
                for devid in output["neopixelClock"]:
                    ddd = output["neopixelClock"][devid][0]
                    #print ddd
                    if "signalPin"  not in ddd: continue
                    if "devType"    not in ddd: continue
                    if not neopixelClockActive:
                        neopixelClockActive =True
                        checkIfNeopixelIsRunning(pgm= "neopixelClock")
                    U.toLog(1, "setting neopixelClock = true") 
                    break
            if "setTEA5767" in output:
                    U.toLog(1, "setting setTEA5767 ON") 
                    if not tea5767Active:
                        startProgam("setTEA5767.py", params="", reason="restarting setTEA5767..not running")
                    tea5767Active =True
            else:
                tea5767Active = False
                U.killOldPgm(-1, "setTEA5767.py")




        ## check if socket port has changed, if yes do a reboot 
        pppp = 0
        if u"rPiCommandPORT"        in inp:  pppp=       (inp["rPiCommandPORT"])
        if str(rPiCommandPORT) !="0":
            if str(pppp) != str(rPiCommandPORT):
                time.sleep(10)
                U.sendRebootHTML("change_in_port")
        rPiCommandPORT = int(pppp)
                

        ### for shutdown pins changes  we need to restart this program
        if u"shutDownPinOutput"   in inp:  
            xxx=                   inp["shutDownPinOutput"]
            if shutDownPinOutput !=-1 and xxx != shutDownPinOutput: # is a change, not just switch on 
                U.toLog(-1, "restart master for new shutdown input pin",doPrint=True)
                os.system("/usr/bin/python "+G.homeDir+"master.py &" )
            if shutDownPinOutput != xxx:
                shutDownPinOutput=     xxx
                GPIO.setmode(GPIO.BCM)
                if shutDownPinInput ==15 or shutDownPinInput==14:
                    os.system("systemctl disable hciuart")
                    time.sleep(1)

        if u"shutDownPinInput"   in inp:  
            xxx=                   inp["shutDownPinInput"]
            if shutDownPinInput !=-1 and xxx != shutDownPinInput:  # is a change, not just switch on 
                U.toLog(-1, "restart master for new shutdown output pin",doPrint=True)
                os.system("/usr/bin/python "+G.homeDir+"master.py &" )
            if shutDownPinInput != xxx:
                shutDownPinInput=     xxx
                GPIO.setmode(GPIO.BCM)
                if shutDownPinInput ==15 or shutDownPinInput==14:
                    os.system("systemctl disable hciuart")
                    time.sleep(1)


        if u"rebootWatchDogTime" in inp :
            xxx   =int(inp["rebootWatchDogTime"])
            if U.pgmStillRunning("shutdownd"):
                if xxx <=0: os.system("shutdown -c >/dev/null 2>&1") 
            elif xxx != rebootWatchDogTime:
                rebootWatchDog()
            rebootWatchDogTime= xxx


        if "rPiRestartCommand"  in inp:  rPiRestartCommand=    (inp["rPiRestartCommand"])
        if inp["rPiRestartCommand"] !="":
            inp["rPiRestartCommand"] =""
            f=open(G.homeDir+"parameters","w")
            f.write(json.dumps(inp, sort_keys=True, indent=2))
            f.close()
            #os.system("/usr/bin/python "+G.homeDir+ "copyToTemp.py")



        if  rPiRestartCommand.find("restartRPI") >-1:
            os.system("rm "+G.homeDir+"installLibs.done")
            U.sendURL(sendAlive="reboot")
            U.doReboot(10.,"re-loading everything due to request from parameter file")


        if  rPiRestartCommand.find("reboot") > -1:
            U.sendURL(sendAlive="reboot")
            U.doReboot(10.,"rebooting due to request from parameter file")


        if  rPiRestartCommand.find("master") > -1:
            U.toLog(-1,"restart due to new input " + rPiRestartCommand,doPrint=True)
            os.system("/usr/bin/python "+G.homeDir+"master.py &" )
            sys.exit()

        time.sleep(1)

        setACTIVEorKILL("INPUTgpio","INPUTgpio.py","")
        setACTIVEorKILL("INPUTtouch","INPUTtouch.py","INPUTtouch")
        setACTIVEorKILL("INPUTtouch16","INPUTtouch16.py","INPUTtouch16")

        if unicode(sensorList).find("spi")>-1 or unicode(sensorList).find("i2c")>-1 or unicode(sensorList).find("Wire")>-1 or unicode(sensorList).find("DHT")>-1:
            if getSensorsActive !=1:
                startProgam("getsensorvalues.py", params="", reason=" at startup ")
            getSensorsActive  = 1
        else: 
            if getSensorsActive !=-1:
                U.killOldPgm(-1,"getsensorvalues.py")
            getSensorsActive  = -1
            

        setACTIVEorKILL("myprogram","myprogram.py","")
        setACTIVEorKILL("mysensors","mysensors.py","")

                
        #print " sensors:", sensors
        U.toLog(0, "sensors       : " +  sensorList)

        for ss in G.theSpecialSensorList:
            if  ss in sensors: 
                checkifActive(ss,         ss+".py",         True)
        
        if  (rPiRestartCommand.find("rPiCommandPORT") >-1) and G.wifiType =="normal" and G.networkType !="clockMANUAL" and rPiCommandPORT >0:
                startProgam("receiveGPIOcommands.py", params=str(rPiCommandPORT), reason=" restart requested from plugin")

        if  not beforeLoop:
            if rPiRestartCommand.find("beacons") >-1 :
                    U.killOldPgm(-1,"beaconloop.py")
                    checkIfAliveFileOK("beaconloop",force="set")
                    startProgam("beaconloop.py", params="", reason=" at startup ")

        sensorEnabled =copy.copy(sensorList)
        firstRead = False
        return 

def setACTIVEorKILL(tag,pgm,check,force=0):
    global sensors, activePGMdict
    #print tag, sensorList
    try:
        theList=""
        for sensor in sensors:
            theList+=sensor.split("-")[0]+","
        if  (tag in theList and tag not in activePGMdict) or force==1:
            activePGMdict[tag]=[pgm,check]
            startProgam(pgm, params="", reason=" at startup ")
            checkifActive(tag,  pgm, True)
        elif ( tag not in theList and tag in  activePGMdict) or force==-1:
            U.killOldPgm(-1,pgm)
            U.toLog(-1,"stopping sensor as no "+tag+" enabled",doPrint=True)
            if tag  in activePGMdict: del activePGMdict[tag] 
        elif tag  in activePGMdict and force ==0:
            del activePGMdict[tag] 
    except  Exception, e:
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))





def doWeNeedToStartTouch(sensors,sensorsOld):
    try:
        for sensor in sensors:
            for n in range(30):
                sensor="INPUTtouch12-"+str(n)
                if sensor not in sensors: continue
                if sensor not in sensorsOld: return 1
                for devId  in sensors[sensor]:
                    if "gpio" not in sensors[sensor][devId]: continue
                    if devId not in sensorsOld[sensor]: return 1
                    ss = sensors[sensor][devId]["gpio"]
                    if ss not in sensorsOld[sensor][devId]: return 1
                    for nn in range(len(ss)):
                        if "gpio" not in ss[nn]: return 1
                U.toLog(1, "enabled sensor " +sensor)
        return 0
    except  Exception, e:
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        U.toLog(-1,"start INPUTtouch12: "+ unicode(sensors))
    return 0



def checkifActive(sensorName, pyName, active):
        if active:
            checkIfPGMisRunning(pyName,force=True, checkAliveFile=sensorName )
            checkIfAliveFileOK(sensorName)
        else:
            U.killOldPgm(1,pyName)
        return 



#########  start pgms  
def installLibs():
        if U.pgmStillRunning("installLibs.py"): return
        os.system("/usr/bin/python "+G.homeDir+"installLibs.py ") # wait until finished

    
def startProgam(pgm, params="", reason=""):
        U.toLog(1, ">>>> starting "+pgm+" "+reason    )
        os.system("/usr/bin/python "+G.homeDir+pgm+" "+params+" &")


def startBLEconnect():
    global sensors, BLEserial, BLEserialOLD
    try:
        ##print BLEserial, BLEserialOLD
        if "BLEconnect" not in sensors:
            U.killOldPgm(-1, "BLEconnect.py")
            return

        if BLEserial !=  BLEserialOLD:
            BLEserialOLD = BLEserial
            U.killOldPgm(-1, "BLEconnect.py")

        if BLEserial == "sequential":
            if not U.pgmStillRunning("BLEconnect.py") :
                startProgam("BLEconnect.py", params="", reason="..starting in serial mode ")
            return

        if BLEserial == "parallel":
            for  dev in sensors["BLEconnect"]:
                mac=sensors["BLEconnect"][dev]["macAddress"]
                ##print "mac", mac
                if len(mac) < 5: continue
                if not U.pgmStillRunning("BLEconnect.py "+mac):
                    startProgam("BLEconnect.py", params=mac, reason="..starting in parallel mode ")
    except  Exception, e :
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),doPrint=True)
    return


def startBLEsensor():
    global sensors
    try:
        if "BLEsensor" not in sensors:
            U.killOldPgm(-1, "BLEsensor.py")
            return
        if not U.pgmStillRunning("BLEsensor.py"):
            startProgam("BLEsensor.py", params="", reason="")
    except  Exception, e :
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),doPrint=True)
    return

    
########## check if programs are running     
    


def checkIfDisplayIsRunning():
    tt = time.time()
    if tt-G.tStart< 15: return
    
    try:
        if not U.pgmStillRunning("display.py"):
            startProgam("display.py", params="", reason="..not running ")
            checkIfAliveFileOK("display",force="set")
            return
        if not checkIfAliveFileOK("display"):
            startProgam("display.py", params="", reason="..not sending alive signal")
            checkIfAliveFileOK("display",force="set")
            return
        if os.path.isfile(G.homeDir+"temp/display.inp") and os.path.getsize(G.homeDir+"temp/display.inp") > 50000:
            startProgam("display.py", params="", reason=" ..display.inp file too big")
            checkIfAliveFileOK("display",force="set")
            return
    except  Exception, e :
        U.toLog (-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        return
    return




def checkIfNeopixelIsRunning(pgm= "neopixel"):
    global lastcheckIfNeopixelIsRunning
    tt = time.time()
    if tt-G.tStart< 5: return
    try: ii = lastcheckIfNeopixelIsRunning
    except: lastcheckIfNeopixelIsRunning = 0
    if tt - lastcheckIfNeopixelIsRunning < 30: return 
    lastcheckIfNeopixelIsRunning = tt
    try:
        U.toLog (1, u"checking if "+pgm+" running")
        if not U.pgmStillRunning(pgm+".py"):
            U.toLog (1, u"restarting  "+pgm)
            startProgam(pgm+".py", params="", reason="..not running ")
            checkIfAliveFileOK(pgm,force="set")
            return
        if not checkIfAliveFileOK("neopixel"):
            startProgam(pgm+".py", params="", reason="..not sending alive signal")
            checkIfAliveFileOK("neopixel",force="set")
            return
        if os.path.isfile(G.homeDir+"temp/neopixel.inp") and os.path.getsize(G.homeDir+"temp/neopixel.inp") > 50000:
            startProgam("neopixel.py", params="", reason=" ..neopixel.inp file too big")
            checkIfAliveFileOK("neopixel",force="set")
            return
    except  Exception, e :
        U.toLog (-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        return
    return



def checkIfPGMisRunning(pgmToStart,force=False,checkAliveFile="", parameters=""):
    tt = time.time()
    if tt-G.tStart< 15 and not force: return
    try:
        if not U.pgmStillRunning(pgmToStart):
            startProgam(pgmToStart, params=parameters, reason="restarting "+pgmToStart+"..not running")
            return
        if checkAliveFile !="":
            alive = checkIfAliveFileOK(checkAliveFile)
            #print "pgm to start", pgmToStart, checkAliveFile, alive
            if not alive:
                startProgam(pgmToStart, params="", reason="restarting "+pgmToStart+"..not running .. no alive file")
                return

    except  Exception, e :
        U.toLog (-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
    return


def checkIfbeaconLoopIsRunning():
    global  sensorList, enableRebootCheck, enableiBeacons, sensorAlive, sensors, lastAlive
    try:
        #print "checking beaconloop running start of pgm"
        tt = time.time()
        if tt-G.tStart< 10: return
        
        if U.pgmStillRunning("installLibs.py"): return


        #print "checking beaconloop running 0"
        if enableRebootCheck.find("restartLoop")>-1  or enableRebootCheck.find("rebootLoop") >-1:
            #print "checking beaconloop running 1"
            if  not checkIfAliveFileOK("beaconloop"):
                #print "checking beaconloop running 2"
            
                if  enableRebootCheck.find("rebootLoop") >-1:
                    U.sendURL(sendAlive="reboot")
                    U.doReboot(10.," Seconds since change in alive file :"+ str(tt- lastAlive["beaconloop"]) +" -- rebooting ")

                #print "checking beaconloop running 3"
                U.killOldPgm(-1,"beaconloop.py")
                checkIfAliveFileOK("beaconloop",force="set")
                startProgam("beaconloop.py", params="", reason=" restart requested by plugin ")
            return

        #print "checking beaconloop running 4"
        if not checkIfAliveFileOK("beaconloop"):
                    #print "checking beaconloop running  alive file not ok"
                    U.killOldPgm(-1,"beaconloop.py")
                    checkIfAliveFileOK("beaconloop",force="set")
                    #print "checking if beaconloop running: are starting beaconlooop"
                    startProgam("beaconloop.py", params="", reason=" alive file is old ")

    except  Exception, e:
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),doPrint=True)
    return



def checkIfAliveFileOK(sensor,force=""):
    global sensorAlive
    alive = True 
    tt = time.time()    
    if  tt - G.tStart < 20 and force =="": return alive
    if force =="set":
        sensorAlive[sensor]=time.time()
        return alive
        
    data =0
    try:
        if sensor not in sensorAlive: sensorAlive[sensor]=0
        
        try:
            data =""
            try:
                f = open(G.homeDir+"temp/alive."+sensor,"r")
                data =f.read()
                data =data.strip("\n")
                lastUpdate=float(data)
                f.close()
                #print "alive test 1 for " , sensor,  lastUpdate
            except  Exception, e:
                #print " exception ",sys.exc_traceback.tb_lineno, e
                time.sleep(0.2)
                if os.path.isfile(G.homeDir+"temp/alive."+sensor):
                        f = open(G.homeDir+"temp/alive."+sensor,"r")
                        data =f.read()
                        data =data.strip("\n")
                        lastUpdate=float(data)
                        f.close()
                else:
                    #print " alive file for ", sensor, " not found"
                    ##os.system("ls -l "+G.homeDir+"temp/")
                    lastUpdate=0
                    try:f.close()
                    except: pass

        except  Exception, e:
            U.toLog(-1, u"(2) in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),doPrint=True)
            lastUpdate=0
        #print "alive test 2 for " , sensor, data
            
       # dont do anything directly after midnight
        dd = datetime.datetime.now()
        if dd.hour == 0 and dd.minute < 10: return alive
 

        #print " alive test 2  delta T",tt - lastUpdate 
        if tt - lastUpdate > 240:  ## nothing for 4 min signal: no alive
            alive = False
        sensorAlive[sensor] = lastUpdate
    except  Exception, e:
        U.toLog(-1, u"(3) in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),doPrint=True)
    return alive    






def checkDiskSpace(maxUsedPercent=90,kbytesLeft=500000): # check if enough disk space  left (min 10% or 500Mbyte)
    try:
        ret=subprocess.Popen("df" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
        lines = ret.split("\n")
        retCode=0
        for line in lines:
            if line.find("/dev/root") > -1:
                items = line.split()
                try:
                    kbytesAvailable = int(items[3])
                    usedPercent=int(items[4].strip("%"))
                    if  usedPercent > maxUsedPercent and kbytesAvailable < kbytesLeft : retCode= 1
                except:
                    return 0
            if line.find("/var/log") > -1: # for temp disks
                items = line.split()
                try:
                    bytesAvailable = int(items[3])
                    usedPercent=int(items[4].strip("%"))
                    if  usedPercent > 90 or bytesAvailable < 4000 : retCode= 2 ## 90% or 4 Mbyte
                except:
                    return 0
            if line.find("/run/user/") > -1: # for temp disks
                items = line.split()
                try:
                    bytesAvailable = int(items[3])
                    usedPercent=int(items[4].strip("%"))
                    if  usedPercent > 90 or bytesAvailable < 4000 : retCode= 2 ## 90% or 4 Mbyte
                except:
                    return 0

        return retCode
    except  Exception, e :
        U.toLog (-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


def rebootWatchDog():
    global rebootWatchDogTime, shutDownPinOutput
    try:

        if rebootWatchDogTime <=0:
            if U.pgmStillRunning("shutdownd"):
                os.system("shutdown -c >/dev/null 2>&1")
            return


        if U.pgmStillRunning("shutdownd"):
            os.system("shutdown -c >/dev/null 2>&1")
            time.sleep(0.1)
            os.system("shutdown +"+str(rebootWatchDogTime)+" >/dev/null 2>&1")



    except  Exception, e :
        U.toLog (-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


def checkIfRebootRequest():
    global shutDownPinOutput
    ###print "into checkIfRebootRequest"
    if  os.path.isfile(G.homeDir+"temp/rebootNeeded"):
        f=open(G.homeDir+"temp/rebootNeeded") 
        reason = f.read()
        f.close()
        os.remove(G.homeDir+"temp/rebootNeeded")
        if reason.find("noreboot")>-1:
            U.toLog(-1, " sending message to plugin re:" + reason ,doPrint=False)
            U.sendURL(sendAlive="alive",text=reason)
        else:
            U.toLog(-1, " rebooting due to request:" + reason ,doPrint=True)
            time.sleep(50)
            U.sendRebootHTML(reason)

        U.doRebootThroughRUNpinReset()


    #print "into checkIfRebootRequest restartNeeded" , os.path.isfile(G.homeDir+"temp/restartNeeded")
    if  os.path.isfile(G.homeDir+"temp/restartNeeded"):
        #print "into checkIfRebootRequest restartNeeded" , os.path.isfile(G.homeDir+"temp/restartNeeded")
        f=open(G.homeDir+"temp/restartNeeded","r") 
        reason = f.read()
        f.close()
        os.remove(G.homeDir+"temp/restartNeeded")
        if reason.find("bluetooth_startup")>-1:
            count = 0
            if  os.path.isfile(G.homeDir+"restartCount"):
                try:
                    f=open(G.homeDir+"restartCount","r") 
                    count = int(f.read())
                    f.close()
                    if count > 5: 
                        os.remove(G.homeDir+"restartCount")
                        U.toLog(-1, " rebooting due to repeated request:" + reason ,doPrint=True)
                        U.doReboot(2.," rebooting due to repeated request:" + reason)
                except: pass
                
            f=open(G.homeDir+"restartCount","w") 
            f.write(str(count+1))
            f.close()
            U.toLog(-1, " starting master due to request:" + reason ,doPrint=True)
            U.restartMyself()
            

def checkIfNightReboot():
    global rebootHour,rebooted, shutDownPinOutput


    #print "rebootHour", rebootHour, "rebooted", rebooted,  " hour=",datetime.datetime.now().hour, "true? ",datetime.datetime.now().hour == rebootHour
    if rebootHour < 0:                       return
    if rebooted:                             return
    nn = datetime.datetime.now()
    if nn.hour    != rebootHour:             return
    # time window for reboot 2 minutes with some ramdom # added(pi# =0...19)
    #print "rebootHour", nn.minute,  int(G.myPiNumber)*2,  int(G.myPiNumber)*2+1
    if nn.minute  <  int(G.myPiNumber)*2:    return 
    if nn.minute  >  int(G.myPiNumber)*2+1 : return 
    print "re booting"

    rebooted = True
    time.sleep(30)
    U.sendRebootHTML("regular_reboot_at_" +str(rebootHour) +"_hours_requested ")
 
    U.doRebootThroughRUNpinReset()



def checkIfShutDownSwitch():
    global shutDownPinInput, lastBootTest, shutDownPinOutput
    
    try:
        ii=lastBootTest
        #print "checkIfShutDownSwitch initialized "
    except:
        lastBootTest="initialized"
        try:
            #print "checkIfShutDownSwitch initializing  "
            GPIO.setmode(GPIO.BCM)
            if shutDownPinInput != -1:
                #print  "setting shutDownPin to GPIO: " + str(shutDownPinInput) 
                U.toLog(-1, "setting shutDownPin to GPIO: " + str(shutDownPinInput) )
                GPIO.setup(int(shutDownPinInput), GPIO.IN, pull_up_down = GPIO.PUD_UP)  # use pin shutDownPin  to input reset
        except  Exception, e :
            U.toLog (-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
            
    try:
        for ii in range(3):
            if GPIO.input(int(shutDownPinInput)) == 1: return
            time.sleep(0.1)
    except  Exception, e :
            U.toLog (-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
            return
    U.sendRebootHTML("shutdownswitch", reboot=False)

    U.doRebootThroughRUNpinReset()

def checkLogfiles():
        global useRamDiskForLogfiles
        try:
            if os.path.isfile(G.homeDir+"permanentLog.log") and  os.path.getsize(G.homeDir+"permanentLog.log") > 20000:
                os.system("rm "+G.homeDir+"permanentLog.log")    
        except: pass
        if checkDiskSpace(maxUsedPercent=80,kbytesLeft=500000) == 0: return  # (need 500Mbyte free or 80%
        U.toLog(-1, "delete logfiles  due to  limited disk space ",doPrint=True)
        os.system("rm /var/log/*")
        os.system("rm "+G.logDir+"*")
        if checkDiskSpace(maxUsedPercent=80,kbytesLeft=500000) == 0: return  # (need 500Mbyte free or 80%
        U.doRebootThroughRUNpinReset()

def checkRamDisk():
        global useRamDiskForLogfiles
        ret=subprocess.Popen("df" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
        lines = ret.split("\n")
      
        ramDiskActive = False
        for line in lines:
            if line.find("/var/log") == -1:continue
            ramDiskActive = True
            break
            
        if useRamDiskForLogfiles=="1" and not ramDiskActive: 
            if  U.checkIfInFile(["tmpfs","/var/log"],"/etc/fstab") ==1:
                U.uncommentOrAdd("tmpfs   /var/log    tmpfs    defaults,noatime,nosuid,mode=0755,size=60m    0 0","/etc/fstab")
                U.toLog(-1," master need to reboot, added ram disk for /var/log ",doPrint=True)
                return True
        if useRamDiskForLogfiles=="0" and ramDiskActive: 
            if  U.checkIfInFile(["tmpfs","/var/log"],"/etc/fstab") ==1:
                U.removefromFile("tmpfs /var/log","/etc/fstab")
                U.toLog(-1," master need to reboot, removed ram disk for /var/log ",doPrint=True)
                return True
        return False



def checkIfAliveNeedsToBeSend():
        tt = time.time()
        lastSend = 0
        if os.path.isfile(G.homeDir+"temp/messageSend"):
            try:
                lastSend = os.path.getmtime(G.homeDir+"temp/messageSend")
            except:
                pass
        if tt - lastSend > 85.:  # do we have to send alive signal to plugin?
            sendi2cToPlugin()
        return


def delayAndWatchDog():
    global shutDownPinInput, rebootWatchDogTime,lastrebootWatchDogTime
    try:
        for xx in range(40): # thats 20 seconds
            time.sleep(0.25)

            if shutDownPinInput !=-1 and  time.time() - G.tStart > 40:
                checkIfShutDownSwitch()

            if xx%15 ==1 and False:
                if  os.path.isfile("/run/nologin"):
                    os.system("rm /run/nologin &")

                if  rebootWatchDogTime > 0 and time.time() - lastrebootWatchDogTime > (rebootWatchDogTime*60 -20.): # rebootWatchDogTime is in minutes
                    lastrebootWatchDogTime = time.time()
                    rebootWatchDog()
                    
    except  Exception, e :
        U.toLog (-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))



def checkSystemLOG():
    global lastcheckSystemLOG, rememberLineSystemLOG
    try: 
        xx = lastcheckSystemLOG
    except: 
        lastcheckSystemLOG=0
        rememberLineSystemLOG =[]
    
    tt = int(time.time())
    if (tt - lastcheckSystemLOG) < 25:
        return
    lastcheckSystemLOG = tt
    try:
        out = subprocess.Popen("tail -300 /var/log/syslog " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
        if out[1].find("tail: cannot open ") >-1 :
            out = subprocess.Popen("logread | tail -100 " ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
            if out[1] !="": return 
        out= out[0]
        if out.find("REGISTER DUMP") > -1:
            lines = out.split("\n")
            for line in lines:
                if len(line) < 53: continue
                if line.find(" DUMP ") > -1:
                    if line[0:50] in rememberLineSystemLOG: continue
                    rememberLineSystemLOG.append(line[0:50])
                    if len(rememberLineSystemLOG) ==1: # do not send  the first occurence
                        continue 
                    if len(rememberLineSystemLOG) > 5: # only remember the first 5 
                        rememberLineSystemLOG.pop(0)
                    U.toLog(1, "sending message to plugin re:" + line ,doPrint=False)
                    U.sendURL(sendAlive="alive",text="checkSystemLOG_register_dump_occured_noreboot_"+line)
            
    except  Exception, e :
        U.toLog (-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))


def cycleWifi():
    eth0IP, wifi0IP, G.eth0Enabled, G.wifiEnabled = U.getIPCONFIG()
    #print "master:  is wifi enabled : "+str(G.wifiEnabled)
    if G.wifiEnabled:
        if U.getIPNumberMaster()> 0:
            #print "master:  cycle wlan0"
            os.system("sudo /sbin/ifconfig wlan0 down; sudo /sbin/ifconfig wlan0 up")  # cycle wlan
    return


#
####################  main #########################

global enableRebootCheck,myPID,restart,sensorList,rPiCommandPORT,firstRead
global rebootWatchDogTime, lastrebootWatchDogTime
global sensorEnabled,  restart, enableiBeacons, beforeLoop,iPhoneMACList,rebootHour,rebooted,BLEserial,BLEserialOLD
global lastAliveultrasoundDistance, sensorAlive,useRamDiskForLogfiles,lastAlive

global shutDownPinInput, shutDownPinOutput
global displayActive, tea5767Active, getSensorsActive, neopixelActive, neopixelClockActive
global actions, output, sensors, sensorList
global activePGMdict, bluetoothONoff
global lastI2C
global oldRaw,  lastRead
oldRaw                  = ""
lastRead                = 0
bluetoothONoff          = "on"
lastI2C                 = ""
getSensorsActive        = 0
G.debug                 = 5
tea5767Active           = False
displayActive           = False 
neopixelActive          = False
neopixelClockActive     = False
rebootHour              = -1  # defualt : do  not reboot
rebooted                = True
useRamDiskForLogfiles   = "0"
enableiBeacons          = "1"
beforeLoop              = True
myPID                   = str(os.getpid())
enableRebootCheck       = ""
restart                 = ""
sensorEnabled           = []
sensorList              = []
sensors                 = {}
enableSensor            = "0"
rPiCommandPORT          = 0
ipConnection            = time.time() +100
G.lastAliveSend2        = time.time()
lastAlive               = []
lastAliveultrasoundDistance =0
loopCount               = 0
iPhoneMACListOLD        = ""
shutDownPinInput        = -1
shutDownPinOutput       = -1
BLEserial               = "serial"
rebootWatchDogTime      = -1
sensorAlive             = {}
actions                 = []
firstRead               = True
activePGMdict           = {}


# remove precompiled py programs in case .py was updated
os.system("rm "+G.homeDir+"*.pyc  > /dev/null 2>&1")

# make dir for our logfiles if they do not exist
os.system("mkdir "+G.logDir +"  > /dev/null 2>&1")


if  os.path.isdir(G.homeDir+"temp"):
    os.system("rm  "+G.homeDir+"temp/* > /dev/null 2>&1")
else:
    os.system("mkdir  "+G.homeDir+"temp")
os.system("mount -t tmpfs -o size=2m tmpfs "+G.homeDir+"temp")


if cleanupOldFiles():
    startProgam("master.py", params="", reason="..cleanedup old files")


G.tStart      = time.time()

# kill old programs
if "neopixelClock" in G.programFiles: neoClock = True
else:                                 neoClock = False


for ff in G.programFiles:
    if ff =="neopixel" and neoClock: continue # do not kill neopixel if in clock mode. neopixelClock does that , less interruption.
    if ff == G.program:
        U.killOldPgm(myPID,G.program+".py")
    else:
        U.killOldPgm(-1, ff+".py")


os.system("/usr/bin/python "+G.homeDir+"copyToTemp.py")

U.whichWifi() 


os.system("cp  "+G.homeDir+"callbeacon.py  "+G.homeDir0+"callbeacon.py")
readNewParams()

U.clearNetwork()

if G.networkType  in G.useNetwork and G.wifiType =="normal":
    for ii in range(100):
        if ii > 5:
            U.toLog (-1, " master no ip number working, giving up")
            G.networkType="clockMANUAL"
            break
    
        ipx, changed = U.getIPNumberMaster()
        if ipx > 1 or G.ipAddress =="":
            U.setNetwork("off")
            time.sleep(5)
            U.toLog (-1, " master no ip number working, trying again, retcode="+ str(ipx))
        else:
            U.clearNetwork()
            break
            
    
readNewParams()


if  G.wifiType =="normal" and G.networkType !="clockMANUAL" and  rPiCommandPORT >0:
        startProgam("receiveGPIOcommands.py", params=str(rPiCommandPORT), reason=" restart requested from plugin")


if G.wifiType !="normal":
    #os.system('systemctl start vncserver-x11-serviced.service &')
    pass
#    time.sleep(1)
#    os.system('startx &')


if G.networkType  in G.useNetwork and G.wifiType =="normal":
    for ii in range(100):
        if G.userIdOfServer  == "xxstartxx":
            U.toLog (-1, " master not configured yet, lets wait for new config files")
            if ii > 100:
                startProgam("master.py", params="", reason="..not configured yet")
                exit(0)
            time.sleep(30)
            readNewParams()
        else:
            break



os.system("sudo mkdir "+G.logDir+" &")
os.system("sudo chown -R  pi:pi  /run/user/1000/pibeacon")



if G.networkType  in G.useNetwork and G.wifiType =="normal":
    for ii in range(100):
        if ii > 100:
            U.toLog(-1, " master no connection to indigo server at ip:>>"+ G.ipOfServer+"<<",doPrint=True)
            time.sleep(20)
            startProgam("master.py", params="", reason=".. failed to connect to indigo server")
            exit(0)
        if U.testPing() >0:
            if time.time() - G.ipConnection > 600.: # after 10 minutes 
                if enableRebootCheck.find("rebootPing") >-1:
                    U.sendURL(sendAlive="reboot")
                    U.doReboot(30.," reboot due to no  PING reply from MAC for 10 minutes ")                

            readNewParams()
        else: 
            U.toLog(-1, " master can ping indigo server at ip:>>"+ G.ipOfServer+"<<",doPrint=True)
            break
        time.sleep(10)




# make directory for sound files
if not os.path.isdir(G.homeDir+"soundfiles"):
    os.system("mkdir "+G.homeDir+"soundfiles &")


if checkDiskSpace() == 1:
    U.toLog(-1, " please expand hard disk, not enough disk space left either do sudo raspi-config and expand HD  or replace ssd with larger ssd ",doPrint=True)
    time.sleep(50)
    exit()


if os.path.isfile(G.homeDir+"temp/rebootNeeded"):
    os.remove(G.homeDir+"temp/rebootNeeded")
if os.path.isfile(G.homeDir+"temp/restartNeeded"):
    os.remove(G.homeDir+"temp/restartNeeded")


# check if all libs for sensors etc are installed
installLibs()
time.sleep(0.5)
for ii in range(200):
    if  os.path.isfile(G.homeDir+"installLibs.done"):
        break
    if ii%10==0:
        U.toLog (-1, " master still waiting for installibs to finish",doPrint=True)
    time.sleep(5)



GPIO.setwarnings(False)




#(re)start beaonloop for bluez / iBeacons
if enableiBeacons =="1": 
    startProgam("beaconloop.py", params="", reason=" at startup ")
    checkIfAliveFileOK("beaconloop",force="set")
 
if checkRamDisk(): 
    U.toLog (-1, " master  waiting to reboot due to ram disk change",doPrint=True)
    time.sleep(60) # give it some time, it should never happen here 
    U.sendRebootHTML("change_in_ramdisk_for_logfiles")

lastrebootWatchDogTime = time.time() - rebootWatchDogTime*60. +30.
os.system("shutdown - c >/dev/null 2>&1") ## stop any pending shutdowns

U.toLog(-1," starting master loop ",doPrint=True)
beforeLoop           = False
# main loop every 30 seconds

# do a system boot sector check / repair
os.system("dosfsck -w -r -l -a -v -t /dev/mmcblk0p1 >> "+G.logDir+G.program+".log")


# reset rights and ownership just in case
os.system("chmod a+r -R "+G.homeDir0+"*")
os.system("chmod a+x "+G.homeDir0+"callbeacon.py")

os.system("chmod a+w -R "+G.homeDir+"*")
os.system("chown -R pi:pi "+G.homeDir0+"*")

os.system("sudo chown -R  pi:pi  /run/user/1000/pibeacon")
os.system("sudo chmod a+x  /lib/udev/hwclock-set")





#startProgam("actions.py", params="", reason=" at startup ")
#checkIfAliveFileOK("actions",force="set")

G.tStart      = time.time()

sendi2cToPlugin()        
tAtLoopSTart =time.time()

U.testNetwork()
U.testNTP()
if G.ntpStatus != "started, working":
    U.startNTP(mode="simple")
    if G.ntpStatus !="started, working":
        #print "master: stopping NTP, not working", G.ntpStatus
        U.stopNTP("final")
        G.ntpStatus ="stopped, after not working"


if  ((G.networkStatus.find("Inet") > -1) and  # network up
     (G.ntpStatus=="started, working"  ) and  # NTP working
     (G.useRTC != "" and G.useRTC != "0")  ):                    # RTC installed ...   ==>  set HW clock to NTP time stamp:
        os.system("sudo /sbin/hwclock -w")

startingnetworkStatus = G.networkStatus
startingnetworkype    = G.networkType
restartCLock          = time.time() +  999999999.

ipx, changed = U.getIPNumberMaster(quiet=True)
if ipx ==0 and G.ipAddress !="":
    U.setNetwork("on")
    
if changed: 
    U.restartMyself(reason="changed ip number, ie wifi was switched off with eth0 present")


os.system("rm  "+ G.homeDir+"temp/sending          > /dev/null 2>&1 ")


U.toLog(1," starting master loop ")
while True:

    if abs(tAtLoopSTart  - time.time()) > 30:
        if G.networkType.find("indigo") >-1 and G.wifiType =="normal":
            U.restartMyself(reason="new time set, delta="+unicode(tAtLoopSTart  - time.time()))
        
    tAtLoopSTart =time.time()
        
    loopCount+=1
    try:    
        readNewParams()
        if loopCount%5 == 0: 
            if checkRamDisk():
                if loopCount < 10: 
                    U.toLog (-1, " master  waiting to reboot due to ram disk change",doPrint=True)
                    time.sleep(60) # give it some time directly after reboot
                U.sendRebootHTML("change_in_ramdisk_for_logfiles")
            # check if fs is still ok

                
        if loopCount%60 == 0: # every 10 minutes
            sendi2cToPlugin()        
            if (unicode(subprocess.Popen("echo x > x" ,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate())).find("Read-only file system") > 0:
                U.doReboot(10.," reboot due to bad SD, 'file system is read only'")                
                time.sleep(10)
                os.system("reboot now")
            os.system("rm x")
            
            os.system("sudo chown -R  pi  "+G.homeDir)
            os.system("sudo chown -R  pi  /run/user/1000/pibeacon")

            #check if IP number has changed, or if we should switch off IP for wifi if eth0 is present 
        if loopCount%24 == 0: # every 2 minutes
            ipx, changed = U.getIPNumberMaster(quiet=True)
            if  G.ipAddress =="" and G.networkType !="clockMANUAL" :
                U.doReboot(10.," reboot due to  no IP nummber")                
                time.sleep(10)
                os.system("reboot now")
            if changed: 
                U.restartMyself(reason="changed ip number, ie wifi was switched off with eth0 present")
            if ipx ==0 and G.ipAddress !="":
                U.setNetwork("on")


        if str(rPiCommandPORT) !="0"  and G.wifiType =="normal" and G.networkType !="clockMANUAL" and (G.networkStatus).find("indigo") >-1: 
            checkIfPGMisRunning("receiveGPIOcommands.py",checkAliveFile="", parameters=str(rPiCommandPORT))

        if "BLEconnect" in sensors:
            startBLEconnect()
            
        if enableiBeacons == "0" and "BLEsensor" in sensors:
            startBLEsensor()

        if displayActive: 
            checkIfDisplayIsRunning()

        if neopixelActive: 
            checkIfNeopixelIsRunning(pgm= "neopixel")

        if neopixelClockActive: 
            checkIfNeopixelIsRunning(pgm= "neopixelClock")
            
        if getSensorsActive ==1:
            checkIfPGMisRunning("getsensorvalues.py" )
            
        if tea5767Active: 
            checkIfPGMisRunning("setTEA5767.py")

        for ss in G.theSpecialSensorList:
            if  ss in sensors: 
                checkIfPGMisRunning(ss+".py",checkAliveFile=ss)
                               
        for ss in activePGMdict:
            checkIfPGMisRunning(activePGMdict[ss][0],checkAliveFile=activePGMdict[ss][1] )

        checkIfPGMisRunning("copyToTemp.py")
        
        checkSystemLOG()
        
        if enableiBeacons != "0":
            checkIfbeaconLoopIsRunning()

        checkIfRebootRequest()
        
        if rebootHour >-1:
            checkIfNightReboot()
            if datetime.datetime.now().hour > rebootHour: rebooted = False

        checkIfAliveNeedsToBeSend()
        

        if loopCount %4 ==0: # check network every 40 secs
            U.testNetwork(force = True)
            U.checkNTP()
            #print "startingnetworkStatus", startingnetworkStatus , G.networkStatus , G.networkType
            if  ((G.networkStatus.find("Inet") > -1 ) and   # network up
                 (G.ntpStatus=="started, working"   ) and   # NTP working
                 (G.useRTC !="" and G.useRTC != "0")  ):            # RTC installed ...   ==>  set HW clock to NTP time stamp:
                os.system("sudo /sbin/hwclock -w")

            if (G.networkStatus).find("indigo") > -1 and (G.networkType).find("clock") ==-1:
                if U.testPing()==2:             # if no ping gets return we assume we are not connected, this happens after powerfailure. the router comes aback after rpi and wifi has given up, need to restart
                    if time.time() - G.ipConnection > 600.: # after 10 minutes 
                        if enableRebootCheck.find("rebootPing") >-1:
                            U.sendURL(sendAlive="reboot")
                            U.doReboot(30.," reboot due to no  PING reply from MAC for 10 minutes ")                

            if  G.networkType.find("clock")> -1:
                    if startingnetworkStatus.find("Inet") >-1 and G.networkStatus.find("Inet") == -1 : # was up at start, now down
                        if (time.time() - restartCLock) < 0:
                            G.networkType ="clockMANUAL"
                            #print "set to clock manual"
                            restartCLock = time.time()+2  # wait at least one round before declaring a loss of wifi 
                            cycleWifi()
                    else:
                        restartCLock = time.time()+ 999999999
                        G.networkType ="clock"

                    #print "restartCLock", time.time() - restartCLock
                    if G.networkType =="clockMANUAL"  and (time.time() - restartCLock)> 0  :
                        xx = G.networkType
                        G.networkType="x"
                        ipOK = U.getIPNumberMaster()
                        G.networkType = xx
                        #print " networkStatus, ipOK : ",  G.networkStatus, ipOK

                        if  ipOK >0 and G.networkStatus.find("Inet") ==-1:
                            U.setNetwork("off")
                            G.networkType="clockMANUAL"
                            cycleWifi()
                            #print " setting to clockmanual "
                            U.restartMyself(reason="network went down ")

                    if ( startingnetworkStatus.find("Inet") ==-1 and  G.networkStatus.find("Inet") >-1  ) :
                        U.clearNetwork()
                        xx = G.networkType
                        G.networkType="x"
                        ipOK = U.getIPNumberMaster()
                        G.networkType = xx
                        #print " networkStatus, ipOK : ",  G.networkStatus, ipOK
                        if ipOK ==0 and G.networkStatus.find("Inet") >-1:
                            U.restartMyself(reason="network came back ")



        if loopCount %120 ==0: # check logfiles every 150*10=1200 seconds ~ 30 minutes
            checkLogfiles()
            loopCount =0
            ## check if we have network back
                
        delayAndWatchDog()
       
    except  Exception, e :
        U.toLog (-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e),doPrint=True)
        

sys.exit(0)        
