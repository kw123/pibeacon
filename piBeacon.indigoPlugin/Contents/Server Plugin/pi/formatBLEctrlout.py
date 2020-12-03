#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# May 1 2020
# version 1.1 
##
import  sys, os,subprocess,json
import time
sys.path.append(os.getcwd())
import	piBeaconUtils	as U
import	piBeaconGlobals as G
G.program = "execcommands"


print "reading", sys.argv[1]

hci = sys.argv[1]

MACs={}
subprocess.Popen("sudo rm "+G.homeDir+"temp/lescan.data",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
subprocess.Popen("sudo rm "+G.homeDir+"temp/hcidump.data",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
subprocess.Popen("sudo rm "+G.homeDir+"temp/hcidump.temp",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
subprocess.Popen("sudo rm "+G.homeDir+"temp/bluetoothctl.data",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
subprocess.Popen("sudo chmod +777 "+G.homeDir+"temp/*",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
starttime = time.time()
print "hciconfig",time.time()-starttime , subprocess.Popen("sudo hciconfig "+hci+" reset",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
print "hcitool",time.time()-starttime ,subprocess.Popen("sudo timeout -s SIGINT 10s hcitool -i "+hci+" lescan > "+G.homeDir+"temp/lescan.data &",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
time.sleep(1)
print "hcidump1",time.time()-starttime ,subprocess.Popen("sudo timeout -s SIGINT 9s hcidump -i "+hci+" --raw  > "+G.homeDir+"temp/hcidump.temp &",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
time.sleep(10)
print "bluetoothctl",time.time()-starttime ,subprocess.Popen("sudo timeout -s SIGINT 9s bluetoothctl scan on > "+G.homeDir+"temp/bluetoothctl.data &",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
print "hcidump2",time.time()-starttime ,subprocess.Popen("cat "+G.homeDir+"temp/hcidump.temp | sed -e :a -e '$!N;s/\\n  //;ta' -e 'P;D' > "+G.homeDir+"temp/hcidump.data",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate
subprocess.Popen("sudo chmod +777 "+G.homeDir+"temp/*",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
time.sleep(10)


if True:

	f = open(G.homeDir+"temp/bluetoothctl.data","r")
	xxx = f.read()
	f.close()
	DeviceFound = False
	out = "bluethoothctrl"
	for line in xxx.split("\n"):
		if line.find("] Device ") > 0:
			out += "\n"+line[12:]
			DeviceFound  = True
			#print "dev found, pos of [", line.find("[")
			continue
		elif line.find("[bluetooth]#   ") == 0:
			if DeviceFound :
				out+=line[12:]
				#print "line attached"
				DeviceFound = False
		else:
			DeviceFound = False
			#print "dev not found", (line[0:10]).encode('hex')
	for line in out.split("\n"):
		#print line
		if " RSSI: " in line:
			items = line.split("Device ")[1].split(" RSSI: ")
			mac = items[0]
			#print mac, items
			if mac not in MACs: 
				MACs[mac] = {"rssi":-99,"mfg":"","msg":[]}
			try:	MACs[mac]["rssi"] = max(MACs[mac]["rssi"],int(items[1]))
			except: pass
			
		
if True:
#                          mac#
#> 04 3E 2A 02 01 00 01 54 E2 0B 23 EA 00 1E 02 01 06 1A FF 4C 00 02 15 07 77 5D D0 11 1B 11 E4 91 91 08 00 20 0C 9A 66 23 0B E2 54 C4 A7 
##reverse mac#:         xx xx xx xx xx xx              
#deleting: 0F:97:5F:57:04:56 {'msg': [
# '04 3E 1B 02 01 03 01 56 04 57 5F 97 0F 0F 02 01 1A 0B FF 4C 00 09 06 03 6D C0 A8 01 66 A8 '], 'rssi': -99, 'mfg': ''}

	f = open(G.homeDir+"temp/hcidump.data","r")
	xxx = f.read()
	f.close()
	print xxx [0:100]
	for line in xxx.split("\n"):
		if line.find(">") >-1:
			items = line.strip().split()
			mac = (items[8:14])[::-1]
			mac = ":".join(mac)
			if mac not in MACs: 
				MACs[mac] = {"rssi":-99,"mfg":"","msg":[]}
			#print mac, "present:>{}<".format(line[2:-3])
			present = False
			for ll in MACs[mac]["msg"]:
				#print mac, "test   :>{}<".format(ll[0:-3])
				if line[2:-3].strip() == ll[0:-3].strip():
					present = True
					#print mac, "test   : duplicate"
					break
			if not present:
				MACs[mac]["msg"].append((line[2:]).strip())
	out+= "\nhcidump\n" 
	out+= xxx

if True:
	f = open(G.homeDir+"temp/lescan.data","r")
	xxx = f.read()
	f.close()
	out += "\nlescan\n" 
	out += xxx
	for line in xxx.split("\n"):
		if line.find(":") >-1:
			items = line.split()
			mac = items[0]
			#print mac, items
			if mac not in MACs: 
				MACs[mac] = {"rssi":-99,"mfg":"","msg":[]}
			if items[1].find("unknown") ==-1:
				MACs[mac]["mfg"] = items[1].strip()

delMAC = {}
for mac in MACs:
	if MACs[mac]["msg"]  == []:  
		delMAC[mac] = True
	if MACs[mac]["rssi"] == -99: 
		delMAC[mac] = True
for mac in delMAC:
	#print "deleting:", mac, MACs[mac]
	del MACs[mac]

f= open(G.homeDir+"temp/BLEAnalysis.data","w")
f.write(out)
f.close()

print json.dumps(MACs, sort_keys=True, indent=2)

f= open(G.homeDir+"temp/BLEAnalysis.json","w")
f.write(json.dumps(MACs, sort_keys=True, indent=2) )
f.close()
subprocess.Popen("sudo chmod +777 "+G.homeDir+"temp/*",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
