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
import matplotlib as mlp
mlp.use("Agg")
import matplotlib.pyplot as plt
import logging.handlers


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


# level=INFO, not DEBUG: this sets the ROOT logger, which every third-party logger inherits - so
# matplotlib/PIL DEBUG chatter ("Loaded backend Agg version v2.2.", findfont scores, ...) never
# reaches the plugin log. Our OWN logger below sets its level explicitly and is therefore NOT
# filtered by this - the script's own logger.setLevel() below decides what IT logs (INFO when
# logLevel is on, WARNING when it is off).
logging.basicConfig(level=logging.INFO, filename= logfileName,format='%(module)-23s L:%(lineno)3d Lv:%(levelno)s %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)
#
if not logLevel:
	logger.setLevel(logging.WARNING)
else:
	logger.setLevel(logging.INFO)

## disable fontmanager logging output 
# silence the WHOLE matplotlib logger tree, not single sub-loggers. basicConfig above puts the ROOT
# logger at DEBUG, so every matplotlib module propagates into the plugin log - e.g. "Loaded backend
# Agg version v2.2." from matplotlib.pyplot, emitted when the backend is really loaded (at the first
# figure, which is why it appears although pyplot is imported much earlier).
# Setting 'pyplot' never worked - the logger is named "matplotlib.pyplot"; the PARENT "matplotlib"
# covers pyplot, font_manager, backends, ticker and everything else in one line. Same for PIL.
logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)


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
		norm = mlp.colors.Normalize(vmin=float(imageFileDynamic[0]),vmax=float(imageFileDynamic[1]))
	elif imageType == "dynamicWindow":
		# NO SENTINELS. This used to start from ma = -999 / mm = +999 and max/min against them, so
		# the window silently clamped for any frame outside that range: a reading above 999 left ma
		# at the real max but a reading BELOW -999 would have left mm at -999, and the centre - and
		# with it the whole displayed contrast window - would have been computed from a number that
		# is not in the data. Taking min/max of the data itself cannot be wrong at any scale, and
		# says what it means.
		# An EMPTY frame has no min or max, so it is caught rather than raising ValueError on max()
		# of an empty sequence - which would have killed the script and produced no image.
		rowsWithData = [row for row in data if len(row) > 0]
		if len(rowsWithData) == 0:
			logger.log(20, "no pixel data at all - falling back to a fully dynamic scale")
			imageType = "dynamic"
		else:
			ma = max(max(row) for row in rowsWithData)
			mm = min(min(row) for row in rowsWithData)
		
			# (mm+ma)/2, NOT (mm-ma)/2+mm. The old form is mm - (ma-mm)/2, ie BELOW the minimum of
			# the frame: for a frame spanning 18..34 it put the window centre at 10.0, so a +-5
			# window was 5..15 and every pixel sat above it - the image saturated to one colour and
			# the "dynamic window" setting did nothing but wash the picture out.
			vmid = (mm+ma) /2.
			norm = mlp.colors.Normalize(vmin=vmid - float(imageFileDynamic),vmax=vmid + float(imageFileDynamic))
			logger.log(20, "min:{:3.1f};  max:{:3.1f};  mid:{:3.1f}; lower:{:3.1f};   upper:{:3.1f}".format(mm, ma, vmid, vmid - float(imageFileDynamic), vmid + float(imageFileDynamic) ))


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
plt.savefig(ifname, dpi=pltDpi, bbox_inches='tight')	  
try:	pngSize = os.path.getsize(ifname)/1024.
except Exception: pngSize = 0		# was "pnGsize" - a typo, so a missing file left pngSize UNDEFINED
									# and the log line below raised NameError instead

# compress file
logger.log(20, "file sizes: original file: {:5.1f}[KB]".format(pngSize) )
if compress:
	tt1= time.time()
	# THE PLOT USED TO BE DESTROYED WHENEVER pngquant FAILED: the original .png was removed first
	# and the .xxx renamed over it afterwards, unguarded - so if pngquant was missing, not
	# executable or refused the image, the png was already gone, the rename raised, and this script
	# has no try/except around it at all. Output lost, and the traceback was the only trace.
	# pngquant --ext .xxx writes the compressed copy ALONGSIDE the original, so renaming it over the
	# original is enough; nothing has to be deleted first. Same shape makeLidar360Plot already uses.
	xxxName = imageOutfile+".xxx"
	try:
		if os.path.isfile(xxxName): os.remove(xxxName)		# a stale .xxx would be renamed over the new png
		cmd = "'"+pluginDir+"pngquant' --force --ext .xxx '"+ifname+"'"
		ppp = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		if os.path.isfile(xxxName):
			compSize = os.path.getsize(xxxName)/1024.
			os.rename(xxxName, ifname)						# replaces the original in one step
			logger.log(20, "          compressed file: {:5.1f}[KB];  time used {:4.2f}".format(compSize, (time.time()-tt1)) )
		else:
			logger.log(20, "          pngquant produced no output - keeping the uncompressed png. stderr:{}".format(ppp[1]))
	except Exception as e:
		logger.log(20, "          compress failed ({}) - keeping the uncompressed png".format(e))

logger.log(20,"time used {:4.2f} --   end  @ {}".format((time.time()-tStart), datetime.datetime.now())  )

sys.exit(0)
