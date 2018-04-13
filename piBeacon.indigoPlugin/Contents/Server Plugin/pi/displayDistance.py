#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# feb 5 2016
# version 0.9 
##
##  get sensor values and write the to a file in json format for later pickup, 
##  do it in a timed manner not to load the system, is every 1 seconds then 30 senods break
##

import  sys, os, time, json, datetime,subprocess,copy
import math

sys.path.append(os.getcwd())
import  piBeaconUtils   as U
import  piBeaconGlobals as G
            
#################################
def displayDistance(dist,sensor,sensors, output,distanceUnits):
    global initDisplay, lastDistVal,lastMSG
    
    
    try:
        ##print " to display:", dist, output
        if len(output) ==0: return
        if "display" not in output: return
        try:
            a=initDisplay  # this fails if fist time
        except:
            lastMSG     = 0
            lastDistVal = 0
            initDisplay = 0 # start display.py if we come here after startup first time
            os.system("/usr/bin/python "+G.homeDir+"display.py  &" )
            time.sleep(0.1)
            #print "init variables", lastDistVal
        
        if initDisplay > 5000:
            os.system("/usr/bin/python "+G.homeDir+"display.py  &" )
            initDisplay =0
            time.sleep(0.1)
        initDisplay +=1
         
        if not U.pgmStillRunning("display.py"):
            os.system("/usr/bin/python "+G.homeDir+"display.py  &" )
            
        if sensor not in sensors: return    
        for devid in sensors[sensor]:
            ddd = sensors[sensor][devid]
            if "pos3LinLog"    in ddd: 
                if ddd["pos3LinLog"] =="log":
                    pos3LinLog        = "log"

            dist1, dist2,distText,unit= formatNumber(ddd,dist,distanceUnits)
        lastMSG     = time.time()
        lastDistVal = dist1
        
        font =""
        font2 =""
        width1= 0    
        width2= 0    
        width3= 12    
        pos1= [0,0]    
        pos2= [5,28]    
        pos3= [5,60,0]    
        pos3LinLog= "lin"    
        devType     = ""
        intensity=100
        for devid in output["display"]:
            ddd = output["display"][devid][0]
            if "devType" not in ddd:  continue
            devType     = ddd["devType"]

            displayResolution     = ""
            if "displayResolution" in ddd:
                try:
                    displayResolution   = ddd["displayResolution"].split("x")
                    displayResolution   = [int(displayResolution[0]),int(displayResolution[1])]                
                except:
                    pass
                    
            if "intensity"  in ddd: 
                intensity  = int(ddd["intensity"])
                
            if devType.find("RGBmatrix") >-1 or devType.lower() in ["ssd1351","st7735"] or devType.lower().find("screen") >-1:
                fill = [int(255*intensity/100),int(255*intensity/100),int(255*intensity/100)]
                fill0 = [0,0,0]
            if devType == "RGBmatrix16x16":
                distDispl = "dist"
                ymax = 16
                xmax = 16
                font  ="5x8.pil"    
                font2 ="5x8.pil"
                width3 = 2
                pos1= [0,0]    
                pos2= [0,8]    
                pos3= [0,33,0]    
            elif devType == "RGBmatrix32x16":
                distDispl = "dist["+unit+"]"
                ymax = 16
                xmax = 32
                font  ="5x8.pil"    
                font2 ="5x8.pil"
                width3 = 0
                pos1= [0,0]    
                pos2= [0,8]    
                pos3= [0,33,0]    
            elif devType == "RGBmatrix32x32":
                distDispl = "dist["+unit+"]"
                ymax = 32
                xmax = 32
                font  ="5x8.pil"    
                font2 ="5x8.pil"
                width3 = 2
                pos1= [0,0]    
                pos2= [0,12]    
                pos3= [0,25,0]    
            elif devType == "RGBmatrix64x32":
                distDispl = "dist["+unit+"]"
                ymax = 32
                xmax = 64
                font  ="5x8.pil"    
                font2 ="8x13.pil"
                width3 = 4
                pos1= [0,0]    
                pos2= [0,10]    
                pos3= [0,25,0]    
            elif devType == "RGBmatrix96x32":
                distDispl = "dist["+unit+"]"
                ymax = 32
                xmax = 96
                font  ="5x8.pil"    
                font2 ="8x13.pil"
                width3 = 4
                pos1= [0,0]    
                pos2= [5,10]    
                pos3= [5,25,0]    

            elif devType.lower() == "ssd1351":
                distDispl = "dist.["+unit+"]"
                ymax = 128
                xmax = 128
                font  ="Arial.ttf"    
                font2 ="Arial.ttf"
                width1 = 26
                width2 = 40
                width3 = 12
                fill0 = [0,0,0]
                pos1= [0,5]    
                pos2= [5,52]    
                pos3= [3,120,0]    

            elif devType=="st7735":
                distDispl = "dist.["+unit+"]"
                ymax = 128
                xmax = 160
                font  ="Arial.ttf"    
                font2 ="Arial.ttf"
                width1 = 26
                width2 = 40
                width3 = 12
                fill0 = [0,0,0]
                pos1= [0,5]    
                pos2= [5,52]    
                pos3= [3,120,0]    
    
            elif devType in ["ssd1306"]:
                distDispl = "dist.["+unit+"]"
                font  = "Arial.ttf"
                font2 = "Arial.ttf"
                width1 = 15
                width2 = 32
                width3 = 4
                ymax = 64
                xmax = 128
                fill = 255
                fill0 = 0
                pos1= [0,0]    
                pos2= [5,21]    
                pos3= [3,60,0]    

            elif devType in ["sh1106"]:
                distDispl = "dist.["+unit+"]"
                font  = "Arial.ttf"
                font2 = "Arial.ttf"
                width1 = 16
                width2 = 32
                width3 = 4
                ymax = 64
                xmax = 128
                fill = 255
                fill0 = 0
                pos1= [0,0]    
                pos2= [5,22]    
                pos3= [3,60,0]    

            elif devType.lower().find("screen") >-1:
                ymax = 480
                xmax = 800
                width1 = 100
                width2 = 260
                width3 = 50
                fill0 = [0,0,0]
                pos1= [0,5]    
                pos2= [5,130]    
                pos3= [3,430,0]    
                if len( displayResolution ) ==2:
                    try:
                        ymax   = displayResolution[1]
                        xmax   = displayResolution[0]
                        width1 = int(width1*ymax/500)
                        width2 = int(width2*ymax/500)
                        width3 = int(width3*ymax/500)
                        pos2   = [5,int(pos2[1]*ymax/500)]
                        pos3   = [3,int(pos3[1]*ymax/500),0]
                    except:
                        pass
                distDispl = "distance["+unit+"]"
                font  = "Arial.ttf"
                font2 = "Arial.ttf"
            break

        pos0= [0,int(ymax)/2,xmax]  

            
        try:    hbarDist = dist/500.
        except: hbarDist=1.
        if pos3LinLog =="log":
            h = (dist/500.)*10. + 1.  # between 1 and 11
            hbarDist = math.log10(h)  # then this is between 0 and 1.01
            
        if devType.find("RGBmatrix")>-1 or devType.lower()in ["ssd1351","st7735","screen"]: 
            if   hbarDist < 0.2: fillBar=[int(255*intensity/100),0,0]  # red
            elif hbarDist < 0.4: fillBar=[int(200*intensity/100),int(200*intensity/100),0]  # yellow
            else:fillBar=[0,int(255*intensity/100),0]  # green

        else: fillBar = fill    
        hbarDist= int(min(hbarDist*xmax*0.95,xmax-2))
        pos3[2] = hbarDist
        #print pos3LinLog, dist,h,hbarDist 

        out={"resetInitial": "", "repeat": 1,"command":[]}
        out["command"].append({"type": "hBar","width":ymax,  "fill":str(fill0),  "position":pos0, "display": "wait"})
        out["command"].append({"type": "text","width":width1,"fill":str(fill),   "position":pos1, "display": "wait", "text":distDispl,"font":font})
        out["command"].append({"type": "text","width":width2,"fill":str(fill),   "position":pos2, "display": "wait", "text":distText, "font":font2})
        out["command"].append({"type": "hBar","width":width3,"fill":str(fillBar),"position":pos3, "display": "immediate"})
        #print out
        try:
            f=open(G.homeDir+"temp/display.inp","a"); f.write(json.dumps(out)+"\n"); f.close()
        except:
            try:
                print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S"),sensor,"retry to write to display.inp"
                time.sleep(0.1)
                f=open(G.homeDir+"temp/display.inp","a"); f.write(json.dumps(out)+"\n"); f.close()
            except  Exception, e:
                print datetime.datetime.now().strftime("%Y%m%d-%H:%M:%S"),sensor,u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e)
                if unicode(e).find("No space left on device") >-1:
                    os.system("rm "+G.homeDir+"temp/* ")
        return 
        
    except  Exception, e:
        U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))

    return
    
#################################
def formatNumber(ddd, data,distanceUnits):
        dist1 = 0
        dist  = 0 
        dist0 = ""
        ud    = ""
        try:
                dist1 = float(data)  
                dist  = float(data)  
                if   distanceUnits =="cm" or distanceUnits =="0.01":
                   ud = "cm"
                   dist0 = ("%8.1f"%(dist)).replace(" ","")
                elif   distanceUnits =="inches" or distanceUnits =="0.0254":
                   ud = 'in'
                   dist = dist/2.54
                   dist0 = ("%7.1f"%(dist)).replace(" ","")
                elif   distanceUnits =="feet" or distanceUnits =="0.348":
                   ud = 'ft'
                   dist = dist*0.0348
                   dist0 = ("%7.1f"%(dist)).replace(" ","")
                elif  distanceUnits =="yard" or distanceUnits =="0.9144":
                   ud = "yd"
                   dist = dist*0.009144
                   dist0 = ("%8.2f"%(dist)).replace(" ","")
                else:
                   ud = "m"
                   dist = dist*0.01
                   dist0 = ("%8.2f"%(dist)).replace(" ","")
 
        except  Exception, e:
            U.toLog(-1, u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e))
        return dist1, dist, dist0, ud
