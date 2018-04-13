#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# mar 2 2016
# version 0.95
##
##    --- utils 
#
#    
import  sys 
import  os 
import  time
sys.path.append(os.getcwd())
import piBeaconGlobals as G
import piBeaconUtils as U


if __name__ == "__main__":
    G.program = "copyToTemp"
    timeLastFile =0
    myPID       = str(os.getpid())
    U.killOldPgm(myPID,G.program+".py")

    os.system("chmod a+w -R "+G.homeDir+"*")
    os.system("chown -R pi:pi "+G.homeDir+"*")
    try:    
        os.system("touch "+G.homeDir+"temp/touchFile")
        timeLastFile = os.path.getmtime(G.homeDir+"temp/touchFile") -1
    except: 
        timeLastFile = 0

    while True:    
        doCopy= 0

        if os.path.isfile(G.homeDir+"temp/touchFile"):
            if timeLastFile != os.path.getmtime(G.homeDir+"temp/touchFile"):
                doCopy= 1
                
        elif os.path.isdir(G.homeDir+"temp"):
                doCopy= 2
                os.system("touch "+G.homeDir+"temp/touchFile")

        if not os.path.isfile(G.homeDir+"temp/parameters"):
                doCopy= 3
                
        ###print G.program, doCopy 
        if doCopy >0:
                ##print G.program, doCopy
                for fileName in G.parameterFileList:
                    if os.path.isfile(G.homeDir+fileName):
                            os.system("sudo cp "+G.homeDir+fileName +" " +G.homeDir+"temp/"+fileName)
                try:  
                    timeLastFile = os.path.getmtime(G.homeDir+"temp/touchFile")
                except:  timeLastFile = -10
                os.system("chmod a+w -R "  +G.homeDir+"temp/*")
                os.system("chown -R pi:pi "+G.homeDir+"temp/*")
                time.sleep(10)

        time.sleep(0.5)
