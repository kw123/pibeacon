#! /usr/bin/env python
# -*- coding: utf-8 -*-
# karl wachs oct/12, 2017
# use at your own risk
#  v 1.0
# change log
#
#
#
#
 
import sys, os, subprocess
import time
import datetime 
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches

#################################
#################################
   

def toLog(text):
    global logfileName, logLevel, printON
    if not logLevel: return 

    l=open(logfileName,"a")
    l.write( text+"\n")
    l.close()
    if printON:
        print text

####### main pgm / loop ############
global logfileName, logLevel, printON

printON = False



indigoDir       = sys.argv[0].split("makeBeaconPositionPlots")[0]
piPositionsDir  = sys.argv[1]

f=open(piPositionsDir+"positions.json")
plotData = json.loads(f.read())
f.close()

### logfile setup
logLevel = plotData["logLevel"]
logfileName=plotData["logFile"]

if printON:  print logLevel, logfileName
try:  
    if os.path.getsize(logfileName.encode('utf8')) > 2000000:   # delete logfile if > 20 MB
        os.remove((logfileName).encode('utf8'))
except: pass


# print start to logfile 
toLog("\nstart @ "+unicode(datetime.datetime.now()) )
tStart= time.time()

toLog("u'imageYscale        :"+unicode(plotData["Yscale"]) )
toLog("u'imageXscale        :"+unicode(plotData["Xscale"]) )
toLog("u'imageDotsY         :"+unicode(plotData["dotsY"]) )
toLog("u'imageText          :"+unicode(plotData["Text"]) )
toLog("u'imageTextColor     :"+unicode(plotData["TextColor"]) )
toLog("u'imageTextPos       :"+unicode(plotData["TextPos"]) )
toLog("u'imageTextRotation  :"+unicode(plotData["TextRotation"]) )
toLog("u'distanceUnits      :"+unicode(plotData["distanceUnits"]) )
toLog("u'imageOutfile       :"+unicode(plotData["Outfile"]) )
toLog("u'compressImag       :"+unicode(plotData["compress"]) )
toLog("u'Zlevels            :"+unicode(plotData["Zlevels"]) )


toLog("u'beacon data:")

for mac in plotData["mac"]:
    toLog(mac+"  "+unicode(plotData["mac"][mac]) )

Yscale                  = float(plotData["Yscale"])
Xscale                  = float(plotData["Xscale"])
Zlevels                 = plotData["Zlevels"].split(",")
nZlevels = min(len(Zlevels),4)
for i in range(nZlevels):
    Zlevels[i] = int(Zlevels[i])
hatches = ["","//","\\","+"]

dotsY                   = int(plotData["dotsY"])
dotsX                   = dotsY *( Xscale/Yscale) 

distanceUnits            = float(plotData["distanceUnits"])

textOffY = 4 *Yscale/ dotsY  # move 4 points 
toLog("u'textOffY       :"+unicode(textOffY) )
textOffX = 5 *Xscale/ dotsX  # move 4 points 
toLog("u'textOffX       :"+unicode(textOffX) )

imageOutfile            = plotData["Outfile"]
if imageOutfile =="":
    imageOutfile = piPositionsDir+"beaconPositions.png"


TransparentBackground ="0.0"


#
toLog("time used %4.2f"%(time.time()-tStart)+ " --   setup fig, ax" )
plt.figure()
fig = plt.gcf()
ax = fig.add_axes([0, 0, 1, 1], frameon=False)

ax.set_ylim( 0.,Yscale )
ax.set_xlim( 0.,Xscale )

# set # of pixels 
DPI = fig.get_dpi()
fig.set_size_inches(dotsX/float(DPI),dotsY/float(DPI))    
#plt.tight_layout()

# dont show anything
plt.axis('off')
#ax.set_axis_off()

#  
backgroundFile          = "background.png"
if os.path.isfile((piPositionsDir+backgroundFile).encode('utf8')):
    toLog("time used %4.2f"%(time.time()-tStart)+ " --   loading background image file " )
    img = plt.imread(piPositionsDir+backgroundFile)
    ax.imshow(img, extent=[0., Xscale, 0., Yscale])
      


# 
imageText               = plotData["Text"]
if imageText !="":  
    toLog("time used %4.2f"%(time.time()-tStart)+ " --   adding  text" )
    imageTextColor          = plotData["TextColor"]
    imageTextSize           = int(plotData["TextSize"])
    imageTextPos            = plotData["TextPos"].split(",")
    imageTextPos            = [float(imageTextPos[0]),float(imageTextPos[1])]
    imageTextRotation       = int(plotData["TextRotation"])
    ax.text(imageTextPos[0],imageTextPos[1],imageText, color=imageTextColor ,size=imageTextSize, rotation=imageTextRotation,clip_on=True)




piColor = "#00FF00"
  
toLog("time used %4.2f"%(time.time()-tStart)+ " --   now loop though the beacons and add them" )
for mac in plotData["mac"]: # get the next beacon
    try:
            this  = plotData["mac"][mac]
            pos   = this["position"]
            alpha = float(this["symbolAlpha"])
            if len(pos) !=3: continue # data empty
            if pos[0] > Xscale : continue
            if pos[1] < 0      : continue
            if pos[0] > Yscale : continue
            if pos[1] < 0      : continue
            # show the marker
            try:     distanceToRPI = this["distanceToRPI"] *0.5 / distanceUnits
            except:  distanceToRPI  = 0.5 / distanceUnits
            distanceToRPI = max( min(distanceToRPI, 3./distanceUnits), 0.2/distanceUnits) 
            
            symbol = this["symbolType"].lower()
            edgecolor   = this["symbolColor"]
            color       = this["symbolColor"]
            if symbol !="text":
                if      symbol =="dot":
                    distanceToRPI  = 0.1 / distanceUnits
                    Dtype ="circle"
                elif    symbol =="smallcircle":
                    Dtype ="circle"
                    distanceToRPI  = 0.3 / distanceUnits
                elif    symbol =="largecircle":
                    Dtype ="circle"
                    distanceToRPI  = 0.5* distanceToRPI / distanceUnits
                elif    symbol =="square":
                    Dtype ="square"
                    distanceToRPI  = 0.7 / distanceUnits
                elif    symbol =="square45":
                    Dtype ="square45"
                    distanceToRPI  = 0.7 / distanceUnits
                else:
                    Dtype =""
            
                hatch=""
                for ii in range(nZlevels):
                    if int(pos[2]) == Zlevels[ii]:
                        hatch = hatches[ii]
                        break

                if this["status"] == u"up":
                    edgecolor= "#000000"
                
                toLog(this["name"].ljust(26)+"  "+ this["nickName"].ljust(6) +"  color:"+ color.ljust(7)+ "  edgecolor:"+ edgecolor.ljust(7) +" symbol:"+ symbol.ljust(11)+" type:"+ Dtype.ljust(6) +" distanceToRPI:%5.1f"%distanceToRPI+"  hatch:" +hatch.ljust(2) +"  status:"+ this["status"])

                if   Dtype == "circle":
                        circle = plt.Circle([pos[0],pos[1]], distanceToRPI, fc=color, ec=edgecolor,alpha=alpha,hatch=hatch)
                        ax.add_patch(circle)
                elif Dtype == "square":
                        piColor=color
                        square = patches.Rectangle((pos[0]- distanceToRPI/2., pos[1]- distanceToRPI/2.), distanceToRPI, distanceToRPI,fc=color, ec=edgecolor,alpha=alpha,hatch=hatch)
                        ax.add_patch(square)
                elif Dtype == "square45":
                        piColor=color
                        square = patches.Rectangle((pos[0]- distanceToRPI/2., pos[1]- distanceToRPI/2.), distanceToRPI, distanceToRPI,angle=45.,fc=color, ec=edgecolor,alpha=alpha,hatch=hatch)
                        ax.add_patch(square)
            
            # show the label next to the marker
            if this["nickName"] !="":
                if symbol =="text": 
                    ax.text(pos[0] ,pos[1] ,this["nickName"], color=this["textColor"] ,size="x-small")
                    toLog(this["name"].ljust(26)+"  "+ this["nickName"].ljust(6) +"  color:"+ color.ljust(7)  +"  status:"+ this["status"])
                else:
                    ax.text(pos[0]+ textOffX ,pos[1]- textOffY ,this["nickName"], color=this["textColor"] ,size="x-small")

    except  Exception, e:
        toLog(mac + u"in Line '%s' has error='%s'" % (sys.exc_traceback.tb_lineno, e) )


if plotData["ShowCaption"] !="0":
    textDeltaX = 6  *Xscale / dotsX  # move 8 points 
    textDeltaY = 5  *Yscale / dotsY  # move 12 points 
    toLog("textDeltaX "+ unicode(textDeltaX))
    if plotData["ShowCaption"]=="1": y = Yscale - textDeltaY
    else:                        y = textDeltaY 

    ax.plot(textDeltaX,y+textOffY,marker="o",color="#9F9F9F", markeredgecolor= "#000000")
    ax.text(textDeltaX*2,y,"up" ,size=imageTextSize-3)

    ax.plot(textDeltaX*5,y+textOffY,marker="o",color="#9F9F9F", markeredgecolor= "#FFFFFF")
    ax.text(textDeltaX*6,y,"down" ,size=imageTextSize-3)

    square = patches.Rectangle((textDeltaX*11,y), 0.25, 0.25,angle=45.,fc="#9F9F9F", ec="#9F9F9F")
    ax.add_patch(square)
    ax.text(textDeltaX*12,y,"expired" ,size=imageTextSize-3)

    ax.text(textDeltaX*18,y,"levels "+unicode(hatches) ,size=imageTextSize-3)
    #ax.plot(textDeltaX*14,y+textOffY,marker="o",color="#9F9F9F", markeredgecolor= "#FFFFFF")


    if plotData["ShowRPIs"] !="0":
        ax.plot(textDeltaX*34,y+textOffY,marker="s",color=piColor)
        ax.text(textDeltaX*35,y,"RPIs" ,size=imageTextSize-3)


# 
toLog("time used %4.2f"%(time.time()-tStart)+ " --   making the plot:")
plt.savefig((piPositionsDir+"beaconPositions.png").encode('utf8'))    # this does not work ==>   ,bbox_inches = 'tight', pad_inches = 0)


try:    pngSize = os.path.getsize((piPositionsDir+"beaconPositions.png").encode('utf8'))/1024.
except: pnGsize = 0
# 

if plotData["compress"] :
    toLog("time used %4.2f"%(time.time()-tStart)+ " --   compressing the png file ")
    cmd = "'"+indigoDir+"pngquant' --force --ext .xxx '"+piPositionsDir+"beaconPositions.png"+"'"
    ppp = subprocess.Popen(cmd.encode('utf8'),shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()  ## creates a file with .xxx, wait for completion
    try:    compSize = os.path.getsize((piPositionsDir+"beaconPositions.xxx").encode('utf8'))/1024.
    except: compSize = 0
    if os.path.isfile((piPositionsDir+"beaconPositions.png").encode('utf8')): os.remove((piPositionsDir+"beaconPositions.png").encode('utf8'))
    os.rename((piPositionsDir+"beaconPositions.xxx").encode('utf8'),(piPositionsDir+"beaconPositions.png").encode('utf8') )
    toLog("time used %4.2f"%(time.time()-tStart)+ " --   file sizes: original file: %5.1f;  compressed file: %5.1f  [KB]"%(pngSize,compSize) )
    
if imageOutfile != piPositionsDir+"beaconPositions.png":
    toLog("time used %4.2f"%(time.time()-tStart)+ " --   moving file to destination: "+  imageOutfile)
    if os.path.isfile((imageOutfile).encode('utf8')): os.remove((imageOutfile).encode('utf8'))
    if os.path.isfile((piPositionsDir+"beaconPositions.png").encode('utf8')):
        os.rename((piPositionsDir+"beaconPositions.png").encode('utf8'),(imageOutfile).encode('utf8') )
        if os.path.isfile((piPositionsDir+"beaconPositions.png").encode('utf8')): os.remove((piPositionsDir+"beaconPositions.png").encode('utf8'))

toLog("time used %4.2f"%(time.time()-tStart)+  " --   end  @ " +unicode(datetime.datetime.now() )  )

sys.exit(0)
