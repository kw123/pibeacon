#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# mar 2 2016
# version 0.95
##
##   read sensors and GPIO INPUT and send http to indigo with data
#
#    GPIO pins as inputs: GPIO:but#  ={"27":"0","22":"1","25":"2","24":"3","23":"4","18":"5"}

##
homeDir = "/home/pi/pibeacon/"
logDir  = "/var/log/"
import  sys, os, subprocess, copy
import  time,datetime
import  json
import	piBeaconUtils	as U
import	piBeaconGlobals as G


def killOldPgm(myPID,pgmToKill):
        global debug
        try:
            cmd= "ps -ef | grep "+pgmToKill+" | grep -v grep"
            ret = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
            lines=ret.split("\n")
            for line in lines:
                if len(line) < 10: continue
                line=line.split()
                pid=int(line[1])
                if pid == int(myPID): continue
                U.logger.log(30, "killing "+pgmToKill)
                subprocess.call("kill -9 "+str(pid), shell=True)
        except Exception as e:
            U.logger.log(30,"", exc_info=True)

def readParams():
        global debug
        f=open(homeDir+"parameters","r")
        try:    inp =json.loads(f.read())
        except: return
        f.close()
		U.getGlobalParams(inp)

######### main  ########
U.setLogging()

readParams()

try:
    myPID = str(os.getpid())
    cmd= json.loads(sys.argv[1])
    if "delayStart" in cmd:
        delayStart =  float(cmd["delayStart"])
        time.sleep(delayStart)

    killOldPgm(myPID, "playsound.py")  # old old instances of myself if they are still running
    cmdOut= cmd["player"]+ " "+homeDir+"soundfiles/"++ cmd["file"] +" &"
    U.logger.log(10, cmdOut)
    subprocess.call(cmdOut, shell=True)
except  Exception as e:
    U.logger.log(30,"", exc_info=True)

        
sys.exit(0)        
