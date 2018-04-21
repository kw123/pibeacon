#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.7 
##
import SocketServer
import RPi.GPIO as GPIO
import smbus
import re
import json, sys,subprocess, os, time, datetime
import copy

sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G
G.program = "execcommands"

allowedCommands=["up","down","pulseUp","pulseDown","continuousUpDown","analogWrite","disable","myoutput","omxplayer","display","newMessage","startCalibration","file","BLEreport"]


def execCMDS(data):
    global execcommands, PWM

    for ijji in range(1):
            try:
                next = json.loads(data)
            except  Exception, e:
                    U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                    U.toLog(-1," bad command: json failed  "+unicode(data))

            #print next
            #print "next command: "+unicode(next)
            U.toLog(-1,"next command: "+unicode(next))
            cmd= next["command"]

            for cc in next:
                if cc == "startAtDateTime":
                    next["startAtDateTime"] = time.time() + next["startAtDateTime"]
                


            if "restoreAfterBoot" in next:
                restoreAfterBoot= next["restoreAfterBoot"]
            else:
                restoreAfterBoot="0"


            U.toLog(1,"next cmd: "+json.dumps(cmd))

            if cmd =="general":
                if "cmdLine" in next:
                    os.system(next["cmdLine"] )  
                    continue


            if cmd =="file":
                if "fileName" in next and "fileContents" in next:
                    #print next
                    try:
                        m = "w"
                        if "fileMode" in next and next["fileMode"].lower() =="a": m="a"
                        #print "write to",next["fileName"], json.dumps(next["fileContents"]), m
                        f=open(next["fileName"],m)
                        f.write(json.dumps(next["fileContents"]))
                        f.close()
                        if "touchFile" in next and next["touchFile"]:
                            os.system("echo  "+str(time.time())+" > "+G.homeDir+"temp/touchFile" )
                    except  Exception, e:
                        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                continue


            if cmd =="BLEreport":
                try:
                    U.killOldPgm(-1,"master.py")
                    U.killOldPgm(-1,"beaconloop.py")
                    U.killOldPgm(-1,"BLEconnect.py")
                    U.getIPNumber()
                    data   = {"BLEreport":{},"pi":str(G.myPiNumber)}
                    
                    cmd = "sudo hciconfig "
                    dataW = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
                    U.toLog(1, unicode(dataW))
                    data   = {"BLEreport":{}}
                    data["BLEreport"]["hciconfig"]            = dataW
                    cmd = "sudo hciconfig hci0 down; sudo hciconfig hci0 up ; sudo timeout -s SIGINT 15s hcitool lescan "
                    dataW = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
                    U.toLog(1, unicode(dataW))
                    data["BLEreport"]["hcitool lescan"]       = dataW
                    cmd = "sudo timeout -s SIGINT 25s hcitool scan "
                    dataW = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
                    U.toLog(1, unicode(dataW)) 
                    data["BLEreport"]["hcitool scan"]         = dataW
                    U.toLog(1, unicode(data))
                    U.sendURL(data,squeeze=False)
                    time.sleep(2)
                    os.system("sudo reboot")
                    exit()
                except  Exception, e:
                        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                continue



            if "device" not in next:
                U.toLog(-1," bad cmd no device given "+unicode(next))
                continue
                
            device=next["device"]
            
            if device.lower()=="output-display":
                cmdOut = json.dumps(next)
                if cmdOut != "":
                    try:
                        #print "execcmd", cmdOut
                        if not U.pgmStillRunning("display.py"):
                            os.system("/usr/bin/python "+G.homeDir+"display.py &" )
                        f=open(G.homeDir+"temp/display.inp","a")
                        f.write(cmdOut+"\n")
                        f.close()
                        f=open(G.homeDir+"display.inp","w")
                        f.write(cmdOut+"\n")
                        f.close()
                    except  Exception, e:
                        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                continue


            if device.lower()=="output-neopixel":
                cmdOut = json.dumps(next)
                if cmdOut != "":
                    try:
                        #print "execcmd", cmdOut
                        if  not U.pgmStillRunning("neopixel.py"):
                            os.system("/usr/bin/python "+G.homeDir+"neopixel.py  &" )
                        else:
                            f=open(G.homeDir+"temp/neopixel.inp","a")
                            f.write(cmdOut+"\n")
                            f.close()
                            f=open(G.homeDir+"neopixel.inp","w")
                            f.write(cmdOut+"\n")
                            f.close()
                    except  Exception, e:
                        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                continue




            if cmd not in allowedCommands:
                U.toLog(-1," bad cmd not in allowed commands "+unicode(next))
                continue


            if "values" in next:
                values = next["values"]
            else:
                values =""

            startAtDateTime =unicode(time.time())
            if "startAtDateTime" in next:
                startAtDateTime = next["startAtDateTime"]

            if "inverseGPIO" in next:
                inverseGPIO = next["inverseGPIO"]
            else:
                inverseGPIO = False




            if  cmd == "newMessage":
                    if next["device"].find(",")> 1:
                        list = next["device"].split(",")
                    elif next["device"]== "all":
                        list = G.programFiles
                    else:
                        list = [next["device"]]
                    for pgm in list:
                        os.system("echo x > "+G.homeDir+"temp/"+pgm+".now")
                    continue




            if  cmd == "startCalibration":
                    if next["device"].find(",")> 1:
                        list = next["device"].split(",")
                    elif next["device"]== "all":
                        list = G.files
                    else:
                        list = [next["device"]]
                    for pgm in list:
                        os.system("echo x > "+G.homeDir+"temp/"+pgm+".startCalibration")
                    continue




            if device=="setMCP4725":
                        try:
                            i2cAddress=str(next["i2cAddress"])
                            if cmd =="disable" :
                                if str(int(i2cAddress)+1000) in execcommands:
                                    del execcommands[str(int(i2cAddress)+1000)]
                            cmdJ= json.dumps({"cmd":cmd,"i2cAddress":i2cAddress,"startAtDateTime":startAtDateTime,"values":values })
                            U.toLog(1,json.dumps(next))
                            cmdOut="python "+G.homeDir+"setmcp4725.py '"+ cmdJ+"'  &"
                            U.toLog(1," cmd= "+cmdOut)
                            os.system(cmdOut)
                            if restoreAfterBoot == "1":
                                execcommands[str(int(i2cAddress)+1000)] = next
                            else:
                                try: del execcommands[str(int(i2cAddress)+1000)]
                                except:pass

                        except  Exception, e:
                            U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                        continue

            if device=="setPCF8591dac":
                        try:
                            i2cAddress=str(next["i2cAddress"])
                            if cmd =="disable" :
                                del execcommands[str(int(i2cAddress)+1000)]
                                continue
                            cmdJ= json.dumps({"cmd":cmd,"i2cAddress":i2cAddress,"startAtDateTime":startAtDateTime,"values":values })
                            U.toLog(1,json.dumps(next))
                            cmdOut="python "+G.homeDir+"setPCF8591dac.py '"+ cmdJ+"'  &"
                            U.toLog(1," cmd= "+cmdOut)
                            os.system(cmdOut)
                            if restoreAfterBoot == "1":
                                execcommands[str(int(i2cAddress)+1000)] = next
                            else:
                                try: del execcommands[str(int(i2cAddress)+1000)]
                                except:pass

                        except  Exception, e:
                            U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                        continue


            if device=="OUTgpio" or device.find("OUTPUTgpio")> -1:
                        try:
                            pinI = int(next["pin"])
                            pin = str(pinI)
                        except  Exception, e:
                            U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                            U.toLog(-1," bad pin "+unicode(next))
                            continue
                        #print "pin ok"
                        if "values" in next: values= next["values"]
                        else:                values={}
   
                        if restoreAfterBoot == "1":
                            execcommands[str(pin)] = next
                        else:
                            try: del execcommands[str(pin)]
                            except: pass
                        U.killOldPgm(-1,"'setGPIO.py "+pin+" '" )
                        if cmd =="disable" :
                            continue
                        time.sleep(0.01)
                        cmdJ= json.dumps({"pin":pin,"cmd":cmd,"startAtDateTime":startAtDateTime,"values":values, "inverseGPIO": inverseGPIO,"debug":G.debug,"PWM":PWM })
                        cmdOut="python "+G.homeDir+"setGPIO.py '"+ cmdJ+"'  &"
                        U.toLog(1," cmd= "+cmdOut)
                        os.system(cmdOut)
                        continue

            if device=="myoutput":
                        try:
                            text   = next["text"]
                            cmdOut= "/usr/bin/python "+G.homeDir+"myoutput.py "+text+"  &"
                            U.toLog(1," cmd= "+cmdOut)
                            os.system(cmdOut)
                        except  Exception, e:
                            U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                        continue

            if device=="playSound":
                        cmdOut=""
                        try:
                            if   cmd  == "omxplayer":
                                cmdOut = json.dumps({"player":"omxplayer","file":G.homeDir+"soundfiles/"+next["soundFile"]})
                            elif cmd  == "aplay":
                                cmdOut = json.dumps({"player":"aplay","file":G.homeDir+"soundfiles/"+next["soundFile"]})
                            else:
                                U.toLog(-1, u"bad command : player not right =" + cmd)
                            if cmdOut != "":
                                U.toLog(1," cmd= "+cmdOut)
                                os.system("/usr/bin/python playsound.py '"+cmdOut+"' &" )
                        except  Exception, e:
                            U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
                        continue

            U.toLog(-1," bad device number/number: "+device)
    f=open(G.homeDir+"execcommands.current","w")
    f.write(json.dumps(execcommands))
    f.close()
                   
    return
                 
           

def readParams():
    global execcommands, PWM
    inp,inpRaw = U.doRead()
    if inp == "": return
    try:
        if u"debugRPI"              in inp:  G.debug=             int(inp["debugRPI"]["debugRPIOUTPUT"])
        if u"GPIOpwm"               in inp:  PWM=                 int(inp["GPIOpwm"])
        U.getGlobalParams(inp)
    except  Exception, e:
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
         

if __name__ == "__main__":
    global debug,  execcommands, PWM
    PWM = 100

    readParams()

    execcommands={}
    #print "execcommands" , sys.argv
    if os.path.isfile(G.homeDir+"execcommands.current"):
        try:
            f=open(G.homeDir+"execcommands.current","r")
            xx= f.read()
            f.close()
            execcommands=json.loads(xx)
        except:
            try:    f.close()
            except: pass
            execcommands={}
    else:
        execcommands={}

        
    execCMDS(sys.argv[1])
       
