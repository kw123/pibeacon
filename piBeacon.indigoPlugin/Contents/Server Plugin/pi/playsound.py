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
                toLog(-1, "killing "+pgmToKill)
                os.system("kill -9 "+str(pid))
        except Exception, e:
            toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

def toLog(lvl,msg):
        global debug
        if lvl<debug :
            f=open(logDir+"playsound.log","a")
            f.write(datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S")+" "+msg+"\n")
            f.close()
def readParams():
        global debug
        f=open(homeDir+"parameters","r")
        try:    inp =json.loads(f.read())
        except: return
        f.close()
        if u"debugRPI"          in inp:  debug=             int(inp["debugRPI"]["debugRPIOUTPUT"])

######### main  ########

readParams()

try:
    myPID = str(os.getpid())
    cmd= json.loads(sys.argv[1])
    if "delayStart" in cmd:
        delayStart =  float(cmd["delayStart"])
        time.sleep(delayStart)

    killOldPgm(myPID, "playsound.py")  # old old instances of myself if they are still running
    cmdOut= cmd["player"]+ " "+homeDir+"soundfiles/"++ cmd["file"] +" &"
    toLog(1, cmdOut)
    os.system(cmdOut)
except  Exception, e:
    toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

        
sys.exit(0)        
