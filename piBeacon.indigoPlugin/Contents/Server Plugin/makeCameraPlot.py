#! /usr/bin/env python
# -*- coding: utf-8 -*-
# karl wachs oct/12, 2018
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
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import matplotlib.cm as cm


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

tStart            = time.time()
indigoDir         = sys.argv[0].split("makeCamera")[0]
imageParams       = json.loads(sys.argv[1])
data              = json.loads(sys.argv[2])

imageOutfile      = imageParams["fileName"] 
logdir            = imageOutfile.split("/")
logfileName       = "/".join(logdir[0:-1])+"/cameraImage.log"
logLevel          = imageParams["logLevel"] =="1"
printON           = False
numberOfPixels    = float(imageParams["numberOfDots"])
imageFileDynamic  = imageParams["dynamic"] 
colorBar          = imageParams["colorBar"].split(",") 
compress          = imageParams["compress"]  =="1"

try:  
    if os.path.getsize(logfileName.encode('utf8')) > 200000:   # delet logfile if > 2 MB
        os.remove((logfileName).encode('utf8'))
except: pass



toLog("\nstart @ "+unicode(datetime.datetime.now()) )

imageType = "dynamic"
if "," in imageFileDynamic:
    imageFileDynamic = imageFileDynamic.split(",")
    imageType= "fixed"
else:
    imageFileDynamic = int(imageFileDynamic)
    if imageFileDynamic >0:
        imageType= "dynamicWindow"
    
toLog("imageFile:        " + imageOutfile+".png")
toLog("Dynamic:          " + unicode(imageFileDynamic))
toLog("imageType:        " + imageType)
toLog("colorBar:         " + unicode(colorBar))
toLog("numberOfPixels:   " + unicode(int(numberOfPixels)))
toLog("data:             ")
for kk in range(len(data)):
    toLog( unicode(data[kk]).replace(" ","") )

pixelsIndata = len(data)
pltDpi = 256

plt.figure(figsize=(numberOfPixels/pltDpi, numberOfPixels/pltDpi), dpi=pltDpi)

if   imageType == "fixed":
    norm = mpl.colors.Normalize(vmin=float(imageFileDynamic[0]),vmax=float(imageFileDynamic[1]))
elif imageType == "dynamicWindow":
    ma = -999
    mm = +999
    for ii in range(len(data)):
        ma = max(ma,max(data[ii]))
        mm = min(mm,min(data[ii]))
        
    vmid = (mm-ma) /2. +mm
    norm = mpl.colors.Normalize(vmin=vmid - float(imageFileDynamic),vmax=vmid + float(imageFileDynamic))
    toLog( "min:%3.1f;  max:%3.1f;  mid:%3.1f;  lower:%3.1f;  upper:%3.1f"%(mm,ma,vmid, vmid - float(imageFileDynamic), vmid + float(imageFileDynamic) ))


cur_axes = plt.gca()
cur_axes.axes.get_xaxis().set_visible(False)
cur_axes.axes.get_yaxis().set_visible(False)


if imageType !="dynamic":
    if colorBar[0] =="color":
        plt.imshow(data, norm=norm)
    else:
        plt.imshow(data, norm=norm, cmap='gray')
else:
    if colorBar[0] =="color":
        plt.imshow(data)
    else:
        plt.imshow(data, cmap='gray')
        
if colorBar[1] == "bar":
    cb = plt.colorbar()
    cb.ax.tick_params(labelsize=int((10./512) *numberOfPixels)   )

ifname = imageOutfile+".png"
plt.savefig((ifname).encode('utf8'),dpi=pltDpi,bbox_inches='tight')   
try:    pngSize = os.path.getsize((ifname).encode('utf8'))/1024.
except: pnGsize = 0

# compress file
toLog("time used %4.2f"%(time.time()-tStart)+ "  plot saved")

if compress:
    cmd = "'"+indigoDir+"pngquant' --force --ext .xxx '"+ifname+"'"
    ppp = subprocess.Popen(cmd.encode('utf8'),shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()  ## creates a file with .xxx, wait for completion
    try:    compSize = os.path.getsize((imageOutfile+".xxx").encode('utf8'))/1024.
    except: compSize = 0
    if os.path.isfile((ifname).encode('utf8')): os.remove((ifname).encode('utf8'))
    os.rename((imageOutfile+".xxx").encode('utf8'),(imageOutfile+".png").encode('utf8') )
    toLog("time used %4.2f"%(time.time()-tStart)+ " --   file sizes: original file: %5.1f;  compressed file: %5.1f  [KB]"%(pngSize,compSize) )
toLog("time used %4.2f"%(time.time()-tStart)+ " --   finished\nEND")

sys.exit(0)
