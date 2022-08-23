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
import logging.handlers
global logging, logger


#################################
   
####### main pgm / loop ############

tStart			  = time.time()
pluginDir		  = sys.argv[0].split("makeCamera")[0]
indigoDir		  = pluginDir.split("Plugins/")[0]
imageParams		  = json.loads(sys.argv[1])
data			  = json.loads(sys.argv[2])

imageOutfile	  = imageParams["fileName"] 
logfileName		  = imageParams["logFile"]
logLevel		  = True# imageParams["logLevel"] =="1"
numberOfPixels	  = float(imageParams["numberOfDots"])
imageFileDynamic  = imageParams["dynamic"] 
compress		  = imageParams["compress"]	 =="1"
colorBar		  = imageParams["colorBar"].split(",") 


logging.basicConfig(level=logging.DEBUG, filename= logfileName,format='%(module)-23s L:%(lineno)3d Lv:%(levelno)s %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)
#
if not logLevel:
	logger.setLevel(logging.ERROR)
else:
	logger.setLevel(logging.DEBUG)

## disable fontmanager logging output 
logging.getLogger('matplotlib.font_manager').disabled = True
logging.getLogger("PIL.PngImagePlugin").setLevel(logging.CRITICAL + 1)


# for debugging
printON			  = False

logger.log(20,"========= start @ {}  =========== ".format(datetime.datetime.now()) )

imageType = "dynamic"
if "," in imageFileDynamic:
	imageFileDynamic = imageFileDynamic.split(",")
	imageType= "fixed"
else:
	imageFileDynamic = int(imageFileDynamic)
	if imageFileDynamic >0:
		imageType= "dynamicWindow"
	
logger.log(20,"imageFile:           {}.png".format(imageOutfile) )
logger.log(20,"Dynamic:             {}".format(imageFileDynamic) )
logger.log(20,"imageType:           {}".format(imageType) )
logger.log(20,"colorsetting:        {}".format(colorBar) )
logger.log(20,"numberOfPixels in x: {} ".format(numberOfPixels) )
logger.log(20,"data: len: {}".format(len(data)))
for kk in range(len(data)):
		logger.log(20, "{}: {}".format(kk, data[kk]).replace(" ","") )

pixelsIndata = len(data)


pltDpi = 256

plt.figure(figsize=(numberOfPixels/pltDpi, numberOfPixels/pltDpi), dpi=pltDpi)


if True:

	if	 imageType == "fixed":
		norm = mpl.colors.Normalize(vmin=float(imageFileDynamic[0]),vmax=float(imageFileDynamic[1]))
	elif imageType == "dynamicWindow":
		ma = -999
		mm = +999
		for ii in range(len(data)):
			ma = max(ma,max(data[ii]))
			mm = min(mm,min(data[ii]))
		
		vmid = (mm-ma) /2. +mm
		norm = mpl.colors.Normalize(vmin=vmid - float(imageFileDynamic),vmax=vmid + float(imageFileDynamic))
		logger.log(20, "min:%3.1f;  max:{3.1f};  mid:{3.1f}; lower:{3.1f};   upper:{%3.1f}".format(mm,ma,vmid, vmid - float(imageFileDynamic), vmid + float(imageFileDynamic) ))


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
		cb.ax.tick_params(labelsize=int((10./512) *numberOfPixels)	 )



ifname = imageOutfile+".png"
plt.savefig((ifname).encode('utf8'),dpi=pltDpi,bbox_inches='tight')	  
try:	pngSize = os.path.getsize((ifname).encode('utf8'))/1024.
except: pnGsize = 0

# compress file
logger.log(20, "file sizes: original file: {:5.1f}[KB]".format(pngSize) )
if compress:
	tt1= time.time()
	cmd = "'"+pluginDir+"pngquant' --force --ext .xxx '"+ifname+"'"
	ppp = subprocess.Popen(cmd.encode('utf8'),shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()  ## creates a file with .xxx, wait for completion
	try:	compSize = os.path.getsize((imageOutfile+".xxx").encode('utf8'))/1024.
	except: compSize = 0
	if os.path.isfile((ifname).encode('utf8')): os.remove((ifname).encode('utf8'))
	os.rename((imageOutfile+".xxx").encode('utf8'),(imageOutfile+".png").encode('utf8') )
	logger.log(20, "          compressed file: {:5.1f}[KB];  time used {:4.2f}".format(compSize, (time.time()-tt1)) )

logger.log(20,"time used {:4.2f} --   end  @ {}".format((time.time()-tStart), datetime.datetime.now())  )

sys.exit(0)
