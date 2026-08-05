#!/usr/bin/env python
# -*- coding: utf-8 -*-
####################
# qualifyDongle.py - decide WHICH ROLES a bluetooth adapter is good for
#
# scanRateTest.py measures throughput, extScanTest.py checks E1 reception. This one answers the
# buying/deployment question instead: given this dongle, which of piBeacon's four radio roles can
# it actually do - scan, broadcast, BLEconnect, extListener (BT5 extended / Ruuvi Air E1)?
#
# Nothing here trusts what the adapter CLAIMS. LE feature bit 12 is set by dongles that deliver
# zero extended reports (TP-Link 18:69:45), and dongles that pass the extended test can be useless
# as scanners (Barrot 04:7F:0E: 2.6 reports/s and legacy commands rejected with 0x0C). Only
# delivered packets count.
#
# phases per adapter:
#    1 fingerprint     hciconfig (bus, OUI, ACL/SCO MTU) + lsusb VID:PID + kernel
#    2 health          comes UP after a reset, ACL MTU != 0
#                      (ACL MTU 0:0 = the "binds but never finishes HCI init" failure on old kernels)
#    3 claimed         LE Read Local Supported Features bit 12 - recorded, never trusted
#    4 extended        reset -> event mask (bit12!) -> clear -> ext params -> enable, count 0x0D,
#                      SPLIT by event-type bit 4 (legacy PDU): a BT5 controller reports the ordinary
#                      BLE4 advs in extended mode too, so this says whether ONE radio can serve as
#                      scanner AND extListener at the same time (beaconloop: scanExtendedMode)
#    5 legacy          reset -> legacy params -> enable, count 0x02, and whether the commands
#                      were even ACCEPTED (0x0C Command Disallowed = not a scanner)
#    6 advertising     set adv params/data/enable - a radio that cannot advertise cannot broadcast
#    7 connect         OPTIONAL (connect=<MAC>): ATT (L2CAP CID 4) connections to a real tag,
#                      repeated (tries=N) - one lucky connect proves nothing, the ENOSYS problem
#                      looks like "works, but only on the 3rd attempt after 30 s"
#
# Every measuring phase also profiles PERFORMANCE, not just the average rate: per-second buckets
# and the longest silence (catches a radio that delivers one burst and then stops - an average
# hides that completely), plus the rssi distribution as a sensitivity/range proxy.
#
# usage:
#    sudo python3 qualifyDongle.py                          all adapters, 10 s per measuring phase
#    sudo python3 qualifyDongle.py 20                       20 s per phase
#    sudo python3 qualifyDongle.py 10 hci1                  only hci1
#    sudo python3 qualifyDongle.py 10 connect=C6:79:FA:75:BF:0F      + connect test (3 attempts)
#    sudo python3 qualifyDongle.py 10 connect=C6:.. tries=10          + 10 connect attempts
#    sudo python3 qualifyDongle.py 10 connect=C6:.. addrType=public   force public (default: derived)
#    sudo python3 qualifyDongle.py 10 send=yes              + send the result to indigo
#    sudo python3 qualifyDongle.py 10 catalogue=/tmp/x.json write the local catalogue elsewhere
#    sudo python3 qualifyDongle.py 10 catalogue=none        no local catalogue (plugin keeps the
#                                                           shared one in the indigo prefs dir)
#
# IMPORTANT: stop beaconloop first, it owns the radios and keeps reconfiguring them:
#    sudo pkill -f beaconloop.py ; sudo pkill -f master.py
#
# python3 only (native AF_BLUETOOTH raw HCI socket, no pybluez needed).
####################
from __future__ import print_function
import sys
import os
import re
import time
import json
import struct
import socket as pySocket
import subprocess

VERSION = 2.4

OGF_LE_CTL                 = 0x08
OCF_LE_SET_EVENT_MASK      = 0x0001
OCF_LE_READ_LOCAL_FEATURES = 0x0003
OCF_LE_SET_ADV_PARAMETERS  = 0x0006
OCF_LE_SET_ADV_DATA        = 0x0008
OCF_LE_SET_ADV_ENABLE      = 0x000A
OCF_LE_SET_SCAN_PARAMETERS = 0x000B
OCF_LE_SET_SCAN_ENABLE     = 0x000C
OCF_LE_EXT_SCAN_PARAMS     = 0x0041
OCF_LE_EXT_SCAN_ENABLE     = 0x0042

SOL_HCI       = 0
HCI_FILTER    = 2
HCI_EVENT_PKT = 0x04

# thresholds, all from measurements on real hardware (scanRateTest, 2026-07):
#   109/s pi onboard broadcom | 92/s good USB | 56/s CSR clone | 24/s ASUS extended | 2.6/s Barrot
SCAN_GOOD      = 80.0		# reports/s: full-time scanner
SCAN_OK        = 40.0		# reports/s: usable scanner (clone territory)
EXT_MIN_RATE   = 1.0		# reports/s in extended mode to call extended reception WORKING
EXT_MIN_MACS   = 5			# ... and it has to hear more than one talkative neighbour
CLONE_ACL_MTU  = 400		# ACL MTU <= this = CSR8510 clone: scans fine, unreliable for connects
# COMBINED scan+extListener on ONE radio is judged differently from a dedicated scanner. piBeacon
# listens for ~60 s and then summarises (the rssi it keeps is an AVERAGE), so what matters is not
# reports/s but "did I hear each device often enough in one summary window". A radio that delivers
# half the raw rate but still sees every mag ~25x per minute is perfectly good here.
# RELATIVE to what the same radio hears in BLE4 mode - the absolute mac count is a property of the
# neighbourhood (60 in a block of flats, 4 in a quiet house), not of the dongle.
COMBINED_MIN_COVERAGE  = 60.0	# % of the macs this radio hears in BLE4-only mode
COMBINED_MIN_PER_MIN   = 5.0	# reports per mac per 60 s window - enough to average an rssi


def shell(cmd):
	try:
		out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
		if not isinstance(out, str): out = out.decode("utf-8", "replace")
		return out
	except Exception as e:
		return "{}".format(e)


def listAdapters():
	return re.findall(r"^(hci\d+):", shell("hciconfig"), re.M)


def fingerprint(hci):
	"""everything that identifies the MODEL, so a result can be recognised again later"""
	out = shell("hciconfig -a {}".format(hci))
	fp  = {"hci": hci, "mac": "", "manufacturer": "", "bus": "", "aclMTU": 0, "scoMTU": "",
			"usb": "", "usbName": "", "usbProven": False, "kernel": shell("uname -r").strip()}
	m = re.search(r"BD Address: ([0-9A-F:]{17})", out)
	if m:	fp["mac"] = m.group(1)
	m = re.search(r"Manufacturer: (.*)", out)
	if m:	fp["manufacturer"] = m.group(1).strip()
	m = re.search(r"Bus: (\w+)", out)
	if m:	fp["bus"] = m.group(1)
	m = re.search(r"ACL MTU: (\d+):(\d+)\s+SCO MTU: (\d+):(\d+)", out)
	if m:
		fp["aclMTU"] = int(m.group(1))
		fp["scoMTU"] = "{}:{}".format(m.group(3), m.group(4))
	fp["oui"] = fp["mac"][:8]
	# USB id: the only stable model identifier - two dongles of the same model share it, and it is
	# what you type into a shop search. UART (onboard) radios simply have none.
	if fp["bus"].upper() == "USB":
		# walk sysfs for THIS adapter: /sys/class/bluetooth/hciN/device/.. up to the usb device that
		# carries idVendor/idProduct. Reading lsusb instead reported the FIRST dongle for every
		# adapter - the live report showed the Realtek and the Barrot both as "33fa:0012 UGREEN".
		try:
			base = os.path.realpath("/sys/class/bluetooth/{}/device".format(hci))
			for _ in range(6):
				vid = os.path.join(base, "idVendor")
				pid = os.path.join(base, "idProduct")
				if os.path.isfile(vid) and os.path.isfile(pid):
					f = open(vid); v = f.read().strip(); f.close()
					f = open(pid); d = f.read().strip(); f.close()
					fp["usb"]       = "{}:{}".format(v, d)
					fp["usbProven"] = True				# read from THIS adapter's sysfs path
					for nn in ["manufacturer", "product"]:
						pp = os.path.join(base, nn)
						if os.path.isfile(pp):
							f = open(pp)
							fp["usbName"] = (fp["usbName"] + " " + f.read().strip()).strip()
							f.close()
					break
				base = os.path.dirname(base)
		except Exception:
			pass
		if fp["usb"] == "":			# sysfs layout not as expected: fall back to lsusb (first match)
			for line in shell("lsusb").split("\n"):
				mm = re.search(r"ID ([0-9a-f]{4}:[0-9a-f]{4})\s*(.*)", line)
				if not mm:	continue
				if mm.group(1) in ("1d6b:0002", "1d6b:0003", "1d6b:0001"):	continue	# root hubs
				# the id goes in CLEAN - it is the catalogue KEY. Appending "?" here filed the same
				# dongle under "0b05:190e" on a run where sysfs worked and "0b05:190e?" on a run where
				# it did not, silently splitting one model into two entries. The uncertainty is a
				# separate flag now, and only the PRINTED form carries the "?" (see usbText).
				fp["usb"]       = mm.group(1)
				fp["usbProven"] = False					# first lsusb match, not proven to be THIS adapter
				fp["usbName"]   = mm.group(2).strip()
				break
	return fp


def usbText(fp):
	"""usb id for DISPLAY: a trailing "?" means it came from the lsusb fallback and is not proven to
	belong to this adapter. Never use this for the catalogue key - use fp["usb"], which is clean."""
	if not fp.get("usb", ""):	return ""
	return fp["usb"] + ("" if fp.get("usbProven", False) else "?")


def vendorName(fp):
	"""what the dongle IS, in words. The summary used to show the usb id or - for an onboard radio
	that has none - the OUI, which is literally the first 3 bytes of the mac printed next to it:
	"B8:27:EB  B8:27:EB:9D:3A:63" identifies nothing. usbName is the sysfs product string
	("Realtek ASUS USB-BT500"), manufacturer is what the controller reports over HCI
	("Broadcom Corporation (15)" - the (nn) is the HCI company id, dropped here)."""
	name = "{}".format(fp.get("usbName", "") or "").strip()
	if name == "":
		name = re.sub(r"\s*\(\d+\)\s*$", "", "{}".format(fp.get("manufacturer", "") or "").strip())
	return name or "unknown"


def resetHCI(hci):
	shell("sudo hciconfig {} reset".format(hci))
	time.sleep(0.4)
	shell("sudo hciconfig {} up".format(hci))
	time.sleep(0.4)
	return "UP" in shell("hciconfig {}".format(hci))


def resetAllAdapters(adapters):
	"""Reset EVERY adapter before the run, not just the one under test.

	Adapters are not independent: a sibling USB radio left in extended-scan mode (or with a stuck
	scan state from beaconloop) skews the neighbour's numbers, and a reset on one USB adapter has
	been seen to ripple to another on the same bus. Starting from a known state for all of them is
	the only way two runs are comparable.

	Inputs:
	    adapters (list): hci names
	Outputs:
	    None
	"""
	print("resetting all adapters first: {}".format(", ".join(adapters)))
	for hci in adapters:
		shell("sudo hciconfig {} down".format(hci))
	time.sleep(0.3)
	for hci in adapters:
		shell("sudo hciconfig {} reset".format(hci))
	time.sleep(0.5)
	for hci in adapters:
		shell("sudo hciconfig {} up".format(hci))
	time.sleep(0.5)
	for hci in adapters:
		state = "UP" if "UP" in shell("hciconfig {}".format(hci)) else "DOWN"
		mtu   = fingerprint(hci)["aclMTU"]
		print("   {}: {}  ACL MTU:{}{}".format(hci, state, mtu, "   <-- not usable" if (state != "UP" or mtu == 0) else ""))


def openSock(hci):
	devId = int(hci.replace("hci", ""))
	sock  = pySocket.socket(pySocket.AF_BLUETOOTH, pySocket.SOCK_RAW, pySocket.BTPROTO_HCI)
	sock.bind((devId,))
	# struct hci_filter (16 bytes; kernels >= 6.1.91 reject shorter): all HCI events
	flt = struct.pack("<IIIH2x", 1 << HCI_EVENT_PKT, 0xFFFFFFFF, 0xFFFFFFFF, 0)
	sock.setsockopt(SOL_HCI, HCI_FILTER, flt)
	sock.settimeout(0.5)
	return sock


def cmdComplete(sock, ocf, params=b""):
	"""one LE command + its command-complete; (status, event). status -1 = no answer"""
	opcode = (OGF_LE_CTL << 10) | ocf
	sock.send(b"\x01" + struct.pack("<HB", opcode, len(params)) + params)
	t0 = time.time()
	while time.time() - t0 < 1.2:
		try:	ev = bytearray(sock.recv(255))
		except Exception:	break
		if len(ev) >= 7 and ev[1] == 0x0E and (ev[4] | (ev[5] << 8)) == opcode:
			return ev[6], ev
	return -1, bytearray()


def countReports(sock, secs, subevent):
	"""Delivery measurement AND performance profile.

	The plain reports/s number hides the two failure modes that actually hurt piBeacon:
	  - a radio that delivers a burst and then goes quiet (the Barrot did 92/min, then 0/min, and
	    the average still looked acceptable) -> per-second buckets + the longest silent gap
	  - a radio that hears only the loudest neighbours -> rssi distribution and distinct macs
	Both are measured here, in the same window, so nothing extra has to run.

	Inputs:
	    sock: open raw HCI socket, scanning already enabled
	    secs (float): measuring window
	    subevent (int): 0x02 legacy adv report, 0x0D extended
	Outputs:
	    dict: n, macs, buckets(list per second), gapMax, rssiMean, rssiMin, rssiMax
	"""
	n, macs   = 0, set()
	nLegacyPdu, nExtPdu = [0], [0]			# only filled for subevent 0x0D - see the split below
	macsLegacyPdu, macsExtPdu = set(), set()
	rssis     = []
	buckets   = [0] * int(max(1, secs))
	t0        = time.time()
	tLast     = t0
	gapMax    = 0.0
	while True:
		now = time.time()
		if now - t0 >= secs:	break
		try:	ev = bytearray(sock.recv(512))
		except Exception:
			if time.time() - tLast > gapMax:	gapMax = time.time() - tLast
			continue
		if len(ev) > 4 and ev[1] == 0x3E and ev[3] == subevent:
			n += 1
			idx = int(time.time() - t0)
			if 0 <= idx < len(buckets):	buckets[idx] += 1
			gap   = time.time() - tLast
			if gap > gapMax:	gapMax = gap
			tLast = time.time()
			try:
				# LEGACY 0x02 report:   [4]=num, [5]=evt, [6]=addrType, [7:13]=mac ... rssi = LAST byte
				# EXTENDED 0x0D report: [4]=num, [5:7]=evt, [7]=addrType, [8:14]=mac,
				#                       [14]=primaryPhy [15]=secondaryPhy [16]=sid [17]=txPower [18]=RSSI
				# The extended layout is NOT "rssi at the end" (data follows), and the mac starts one
				# byte earlier than the legacy one - both were wrong here: the report showed
				# "rssi mean/max 16/113 dBm", which are txPower/length bytes read as a signed rssi.
				if subevent == 0x02:
					macs.add(bytes(ev[7:13]))
					r = ev[-1]
				else:
					macs.add(bytes(ev[8:14]))
					r = ev[18] if len(ev) > 18 else 0
					# Event_Type bit 4 = "legacy PDU used": a BT5 controller in EXTENDED scan mode
					# reports the ordinary BLE4 advertisements too, flagged with this bit. Counting
					# the two apart is the whole question of "can ONE dongle cover BLE4 + BLE5".
					evt = ev[5] | (ev[6] << 8)
					if evt & 0x0010:
						nLegacyPdu[0] += 1
						macsLegacyPdu.add(bytes(ev[8:14]))
					else:
						nExtPdu[0] += 1
						macsExtPdu.add(bytes(ev[8:14]))
				rssis.append(r - 256 if r > 127 else r)
			except Exception:	pass
	if time.time() - tLast > gapMax:	gapMax = time.time() - tLast
	out = {"n": n, "macs": len(macs), "buckets": buckets, "gapMax": round(gapMax, 1),
			"rssiMean": 0, "rssiMin": 0, "rssiMax": 0,
			"nLegacyPdu": nLegacyPdu[0], "macsLegacyPdu": len(macsLegacyPdu),
			"nExtPdu": nExtPdu[0], "macsExtPdu": len(macsExtPdu)}
	if rssis:
		out["rssiMean"] = int(sum(rssis) / float(len(rssis)))
		out["rssiMin"]  = min(rssis)
		out["rssiMax"]  = max(rssis)
	return out


def phaseExtended(hci, secs, res):
	resetHCI(hci)
	sock = openSock(hci)
	try:
		# order matters: the event mask FIRST. bit12 (extended adv report) is OFF in the controller
		# default, so an adapter that is otherwise fine scans happily and delivers NOTHING.
		stM, _ = cmdComplete(sock, OCF_LE_SET_EVENT_MASK, struct.pack("<Q", 0x000FFFFF))
		cmdComplete(sock, OCF_LE_EXT_SCAN_ENABLE, struct.pack("<BBHH", 0x00, 0x00, 0, 0))	# clear a stuck scan
		stP, _ = cmdComplete(sock, OCF_LE_EXT_SCAN_PARAMS, struct.pack("<BBBBHH", 0x00, 0x00, 0x01, 0x01, 0x0010, 0x0010))
		stE, _ = cmdComplete(sock, OCF_LE_EXT_SCAN_ENABLE, struct.pack("<BBHH", 0x01, 0x00, 0, 0))
		res["extCmdStatus"] = [stM, stP, stE]
		if stP != 0 or stE != 0:
			res["nExt"], res["uExt"] = 0, 0
			return
		prof = countReports(sock, secs, 0x0D)
		res["nExt"], res["uExt"], res["profExt"] = prof["n"], prof["macs"], prof
		# what the SAME extended scan heard, split by PDU kind: this is what a single combined
		# BLE4+BLE5 listener would actually deliver (beaconloop's scanExtendedMode does exactly
		# this - extendedReportToLegacyFrames rewrites both kinds into the legacy layout).
		res["nExtLegacyPdu"], res["uExtLegacyPdu"] = prof["nLegacyPdu"], prof["macsLegacyPdu"]
		res["nExtOnlyPdu"],   res["uExtOnlyPdu"]   = prof["nExtPdu"],    prof["macsExtPdu"]
		cmdComplete(sock, OCF_LE_EXT_SCAN_ENABLE, struct.pack("<BBHH", 0x00, 0x00, 0, 0))
	finally:
		try:	sock.close()
		except Exception:	pass


def phaseLegacy(hci, secs, res):
	resetHCI(hci)
	sock = openSock(hci)
	try:
		stP, _ = cmdComplete(sock, OCF_LE_SET_SCAN_PARAMETERS, struct.pack("<BHHBB", 0x01, 0x0010, 0x0010, 0x00, 0x00))
		stE, _ = cmdComplete(sock, OCF_LE_SET_SCAN_ENABLE, struct.pack("<BB", 0x01, 0x00))
		res["legCmdStatus"] = [stP, stE]
		if stP != 0 or stE != 0:
			# 0x0C = Command Disallowed: the controller is locked to the extended command family.
			# That is the Barrot signature and it means "never give this dongle the scan role".
			res["nLeg"], res["uLeg"] = 0, 0
			return
		prof = countReports(sock, secs, 0x02)
		res["nLeg"], res["uLeg"], res["profLeg"] = prof["n"], prof["macs"], prof
		cmdComplete(sock, OCF_LE_SET_SCAN_ENABLE, struct.pack("<BB", 0x00, 0x00))
	finally:
		try:	sock.close()
		except Exception:	pass


def phaseAdvertise(hci, res):
	"""can it BROADCAST? piBeacon's iBeacon transmitter needs legacy advertising to work."""
	resetHCI(hci)
	sock = openSock(hci)
	try:
		stP, _ = cmdComplete(sock, OCF_LE_SET_ADV_PARAMETERS,
							struct.pack("<HHBBB6sBB", 0x00A0, 0x00A0, 0x03, 0x00, 0x00, b"\x00"*6, 0x07, 0x00))
		data   = bytearray(32)
		payload = bytes(bytearray([0x02, 0x01, 0x06, 0x03, 0x03, 0xAA, 0xFE]))
		data[0] = len(payload)
		data[1:1+len(payload)] = payload
		stD, _ = cmdComplete(sock, OCF_LE_SET_ADV_DATA, bytes(data))
		stE, _ = cmdComplete(sock, OCF_LE_SET_ADV_ENABLE, struct.pack("<B", 0x01))
		cmdComplete(sock, OCF_LE_SET_ADV_ENABLE, struct.pack("<B", 0x00))
		res["advCmdStatus"] = [stP, stD, stE]
	finally:
		try:	sock.close()
		except Exception:	pass


def phaseConnectRepeat(hci, mac, res, tries, timeout=12.):
	"""CONNECT PERFORMANCE: one successful connect proves nothing - the ENOSYS problem on the
	onboard radio shows up as "works, but only after 3 attempts and 30 s". So connect N times and
	report the success RATE, the times, and which errors came back.

	Inputs:
	    hci (str), mac (str): adapter and target tag
	    res (dict): result dict to fill
	    tries (int): how many attempts
	    timeout (float): per attempt
	Outputs:
	    None
	"""
	ok, times, errs = 0, [], {}
	for ii in range(max(1, tries)):
		one = {"fingerprint": res["fingerprint"]}
		phaseConnect(hci, mac, one, timeout)
		if one.get("connectOk"):
			ok += 1
			times.append(one.get("connectSecs", 0))
		else:
			ee = one.get("connectErr", "?")
			errs[ee] = errs.get(ee, 0) + 1
		time.sleep(1.0)
	res["connectTarget"]   = mac
	res["connectAddrType"] = "random" if peerAddrType(mac) == BDADDR_LE_RANDOM else "public"
	res["connectTries"]    = max(1, tries)
	res["connectOk"]      = ok > 0
	res["connectRate"]    = round(100.0 * ok / float(max(1, tries)), 0)
	res["connectSecs"]    = round(sum(times) / float(len(times)), 1) if times else 0
	res["connectSecsMax"] = round(max(times), 1) if times else 0
	res["connectErrors"]  = errs


#  kernel l2cap bdaddr types - same values as gattAttClient.py, which connects for real every day.
#  0x00 is BDADDR_BREDR, NOT "LE public": using it, or using 0x01 where 0x02 belongs, makes the
#  controller look for a device that is not there and EVERY attempt on EVERY radio ends in "timeout".
BDADDR_LE_PUBLIC = 0x01
BDADDR_LE_RANDOM = 0x02

forceAddrType = ""		# "public" / "random" from the command line, "" = decide per address


def peerAddrType(mac):
	"""public or random for the TARGET? Only ONE case is decidable from the address itself: top two
	bits of the first octet = 11 means STATIC RANDOM (BT core spec Vol 6 Part B 1.3.2), which is what
	beacon tags use (CC:.., C6:.., E1:.., F4:..). The other random kinds cannot be told apart from a
	public address by bits alone - 01xxxxxx is "resolvable private", but 58:11:22 is also a perfectly
	real Realtek OUI - so anything else is treated as public, plus the locally-administered bit which
	no IEEE assigned OUI has set. A resolvable-private target needs an explicit addrType=random."""
	if forceAddrType == "public":	return BDADDR_LE_PUBLIC
	if forceAddrType == "random":	return BDADDR_LE_RANDOM
	try:	first = int(mac.split(":")[0], 16)
	except Exception:	return BDADDR_LE_RANDOM
	if (first & 0xC0) == 0xC0:	return BDADDR_LE_RANDOM		# static random - the beacon tag case
	if first & 0x02:			return BDADDR_LE_RANDOM		# locally administered = not an IEEE public address
	return BDADDR_LE_PUBLIC


def phaseConnect(hci, mac, res, timeout=12.):
	"""OPTIONAL: a real ATT connection to a real tag - the only honest connect test.
	Needs a beacon that is connectable RIGHT NOW, so it can never be part of the automatic run."""
	res["connectTarget"] = mac
	try:
		import ctypes
		BTPROTO_L2CAP = 0
		libc = ctypes.CDLL("libc.so.6", use_errno=True)

		def sockaddr(macStr, addrType):
			# struct sockaddr_l2 {u16 family; u16 psm; bdaddr_t addr; u16 cid; u8 addr_type;}
			# The previous "<HH6sBB" put the ATT CID in the PSM field and a byte where the u16 cid
			# belongs, so the kernel got a nonsense address: connect() returned instantly and every
			# adapter "passed" with 100% in 0.0s. Same layout as gattAttClient._sockaddrL2 now.
			bb = bytes(bytearray(int(x, 16) for x in reversed(macStr.split(":"))))
			return struct.pack("<HH6sHB", 31, 0, bb, 4, addrType) + b"\x00"

		ownMac = res["fingerprint"]["mac"]
		s  = pySocket.socket(31, pySocket.SOCK_SEQPACKET, BTPROTO_L2CAP)
		sa = sockaddr(ownMac, BDADDR_LE_PUBLIC)		# the local adapter is always a public address
		libc.bind(s.fileno(), sa, len(sa))
		s.setblocking(False)
		t0 = time.time()
		sa = sockaddr(mac, peerAddrType(mac))		# public or RANDOM - see peerAddrType()
		ret = libc.connect(s.fileno(), sa, len(sa))
		import select
		if ret != 0:
			rl, wl, xl = select.select([], [s], [], timeout)
			if not wl:
				res["connectOk"], res["connectSecs"], res["connectErr"] = False, time.time()-t0, "timeout"
				s.close()
				return
			err = s.getsockopt(pySocket.SOL_SOCKET, pySocket.SO_ERROR)
			if err != 0:
				res["connectOk"], res["connectSecs"], res["connectErr"] = False, time.time()-t0, "SO_ERROR:{}".format(err)
				s.close()
				return
		res["connectOk"], res["connectSecs"], res["connectErr"] = True, time.time()-t0, ""
		s.close()
	except Exception as e:
		res["connectOk"], res["connectErr"] = False, "{}".format(e)


def verdict(res, secs):
	"""which piBeacon ROLES this adapter qualifies for - the actual output of the program"""
	fp     = res["fingerprint"]
	rLeg   = res.get("nLeg", 0) / float(secs) if res.get("nLeg", 0) > 0 else 0.0
	rExt   = res.get("nExt", 0) / float(secs) if res.get("nExt", 0) > 0 else 0.0
	roles, why = [], []

	if rExt >= EXT_MIN_RATE and res.get("uExt", 0) >= EXT_MIN_MACS:
		roles.append("BLE5-listener")
	else:
		why.append("no BLE5: {:.1f} BLE5 reports/s from {} macs".format(rExt, res.get("uExt", 0)))

	if rLeg >= SCAN_OK:
		roles.append("scan-BLE4" + ("" if rLeg >= SCAN_GOOD else "(weak)"))
	else:
		if res.get("legCmdStatus", [0, 0])[0] == 0x0C or res.get("legCmdStatus", [0, 0])[1] == 0x0C:
			why.append("BLE4 scan commands REJECTED (0x0C) - BLE5-only firmware, cannot be the scan radio")
		else:
			why.append("scan too slow: {:.1f}/s (need {:.0f})".format(rLeg, SCAN_OK))

	# ONE radio for BLE4+BLE5. A BT5 controller is REQUIRED to report legacy advs while in extended
	# mode (event type bit 4), but how much it delivers is firmware - so it is measured, not assumed.
	# Judged by COVERAGE + samples per summary window, NOT by reports/s: see COMBINED_MIN_* above.
	rLegInExt = res.get("nExtLegacyPdu", 0) / float(secs)
	uLegInExt = res.get("uExtLegacyPdu", 0)
	perMacMin = (60.0 * rLegInExt / uLegInExt) if uLegInExt > 0 else 0.0
	res["combinedPerMacPerMin"] = round(perMacMin, 1)
	uLegOwn  = res.get("uLeg", 0)
	coverage = (100.0 * uLegInExt / uLegOwn) if uLegOwn > 0 else 100.0
	res["combinedCoveragePct"] = round(coverage, 0)
	if coverage >= COMBINED_MIN_COVERAGE and perMacMin >= COMBINED_MIN_PER_MIN and rExt >= EXT_MIN_RATE:
		roles.append("scan-BLE4+BLE5")
		why.append("one radio can do BLE4+BLE5 here: in BLE5 mode it still reaches {:.0f}% of the macs it hears in BLE4 mode ({} of {}), {:.0f} reports per mac per minute".format(
					coverage, uLegInExt, uLegOwn, perMacMin))
	elif rExt >= EXT_MIN_RATE:
		if coverage < COMBINED_MIN_COVERAGE:
			why.append("not a combined BLE4+BLE5 scanner: in BLE5 mode it reaches only {:.0f}% of the macs it hears in BLE4 mode ({} of {})".format(
						coverage, uLegInExt, uLegOwn))
		else:
			why.append("not a combined BLE4+BLE5 scanner: only {:.0f} reports per mac per minute in BLE5 mode (need {:.0f})".format(
						perMacMin, COMBINED_MIN_PER_MIN))

	if res.get("advCmdStatus", [1, 1, 1]) == [0, 0, 0]:	roles.append("broadcast")
	else:												why.append("cannot advertise (adv cmd status {})".format(res.get("advCmdStatus")))

	# CONNECT: the ACL MTU guess and the MEASUREMENT reconciled in ONE place. A measurement always
	# beats the guess - a radio that connected 3/3 IS a connect radio whatever its MTU says (the
	# Barrot does 100% with ACL MTU 679, and used to be reported as "connect-PROVEN" WITHOUT
	# "connect", which reads as a contradiction), and one that failed every attempt is not, however
	# full sized its MTU. Only without a connect test does the MTU decide on its own. Every MTU band
	# produces a note, so a role missing because of the MTU is never silent - 401..1020 used to
	# match neither branch and vanished without a word.
	acl  = fp.get("aclMTU", 0)
	rate = res.get("connectRate", -1)					# -1 = no connect test was run at all
	if rate >= 100:
		roles.append("connect")
		roles.append("connect-PROVEN")
	elif rate >= 1:
		roles.append("connect(weak)")
		why.append("connect unreliable: only {:.0f}% of {} attempts succeeded {}".format(
					rate, res.get("connectTries"), res.get("connectErrors") or ""))
	elif rate == 0:
		# name the address type here too: "timeout on every radio" is what a WRONG address type looks
		# like, and it is the first thing to re-check (addrType=public|random) before blaming a dongle.
		why.append("connect FAILED in all {} attempts {} as address type {} - no connect role, whatever the ACL MTU ({})".format(
					res.get("connectTries"), res.get("connectErrors") or "", res.get("connectAddrType", "?"), acl))
	elif acl >= 1021:									roles.append("connect")
	elif 0 < acl <= CLONE_ACL_MTU:						why.append("clone dongle (ACL MTU {}) - connects unreliable".format(acl))
	elif acl > 0:										why.append("ACL MTU {} is below the 1021 of a full controller - connect not assumed, run with connect=<MAC> to settle it".format(acl))

	# stability: an average hides a radio that delivers a burst and then goes silent. A gap of more
	# than a quarter of the window with nothing at all means the role would keep dropping out.
	for label, key in [["BLE4", "profLeg"], ["BLE5", "profExt"]]:
		pr = res.get(key)
		if not pr or pr.get("n", 0) == 0:	continue
		if pr.get("gapMax", 0) > max(3.0, secs / 4.0):
			why.append("{} delivery UNSTABLE: {:.1f}s with no report at all".format(label, pr.get("gapMax")))
		if pr.get("rssiMean", 0) and pr.get("rssiMean", 0) < -90:
			why.append("{} sensitivity poor: mean rssi {} dBm - hears only the loudest neighbours".format(label, pr.get("rssiMean")))

	res["rateLegacy"], res["rateExtended"] = round(rLeg, 1), round(rExt, 1)
	res["roles"], res["notes"] = roles, why
	return roles, why


def report(res, secs):
	fp = res["fingerprint"]
	print("")
	print("==== {}  {}  ({}) ====".format(fp["hci"], fp["mac"], fp["manufacturer"] or "?"))
	print("  bus:{}  ACL MTU:{}  SCO MTU:{}  usb:{} {}".format(
			fp["bus"], fp["aclMTU"], fp["scoMTU"], usbText(fp) or "-", fp["usbName"]))
	print("  kernel:{}   LE feature bit12 (CLAIMED BLE5): {}".format(fp["kernel"], res.get("claimsBLE5")))
	if not res.get("healthy", True):
		print("  HEALTH   : adapter does not come up properly (ACL MTU {}) - unusable".format(fp["aclMTU"]))
	print("  BLE4     : {:5d} reports = {:6.1f}/s from {:3d} macs   cmd status:{}".format(
			res.get("nLeg", 0), res.get("rateLegacy", 0), res.get("uLeg", 0), res.get("legCmdStatus")))
	print("  BLE5     : {:5d} reports = {:6.1f}/s from {:3d} macs   cmd status:{}".format(
			res.get("nExt", 0), res.get("rateExtended", 0), res.get("uExt", 0), res.get("extCmdStatus")))
	for label, key in [["BLE4", "profLeg"], ["BLE5", "profExt"]]:
		pr = res.get(key)
		if not pr or pr.get("n", 0) == 0:	continue
		bk = pr.get("buckets", [])
		print("  {:9s} performance: rssi mean/max {}/{} dBm, longest silence {:.1f}s, per-second {}".format(
				label, pr.get("rssiMean"), pr.get("rssiMax"), pr.get("gapMax"),
				"/".join("{}".format(b) for b in bk[:12]) + ("..." if len(bk) > 12 else "")))
	if "nExtLegacyPdu" in res:
		# the SAME extended scan, split by PDU kind. "legacyPDU" is what a BLE4-only tag looks like
		# when a BT5 controller reports it in extended mode - if that number is close to the LEGACY
		# phase above, this one radio can do BLE4 and BLE5 together (beaconloop scanExtendedMode).
		rl = res.get("nExtLegacyPdu", 0) / float(secs)
		re_ = res.get("nExtOnlyPdu", 0) / float(secs)
		leg = res.get("nLeg", 0) / float(secs)
		keep = (100.0 * rl / leg) if leg > 0 else 0.0
		print("  COMBINED : BLE5 scan reports {:.1f}/s BLE4-advs from {} macs + {:.1f}/s BLE5-advs from {} macs"
				.format(rl, res.get("uExtLegacyPdu", 0), re_, res.get("uExtOnlyPdu", 0)))
		if res.get("legCmdStatus", [0, 0])[0] == 0x0C or res.get("legCmdStatus", [0, 0])[1] == 0x0C:
			# extended-only firmware: there is no legacy-mode number to compare against, and printing
			# "keeps 0% of the 0.0/s" reads like a failure when it is simply not applicable.
			print("             -> BLE5-only firmware: no BLE4 scan mode to compare with;"
					" the BLE4 advs above are all it can hear")
		elif leg > 0:
			print("             -> keeps {:.0f}% of the {:.1f}/s this radio sees in BLE4-only mode".format(keep, leg))
		if res.get("uExtLegacyPdu", 0) > 0:
			print("             -> {:.0f} reports per mac per minute - piBeacon summarises every ~60 s and keeps an AVERAGE rssi"
					.format(60.0 * rl / res["uExtLegacyPdu"]))
	print("  ADVERTISE: {}".format("ok" if res.get("advCmdStatus") == [0, 0, 0] else "FAILED {}".format(res.get("advCmdStatus"))))
	if "connectRate" in res:
		# the ADDRESS TYPE belongs on this line: connecting to a static-random tag as "public" makes
		# every attempt time out on every radio and looks exactly like broken hardware (it did).
		print("  CONNECT  : {:.0f}% of {} attempts to {} ({}), mean {:.1f}s max {:.1f}s  {}".format(
				res.get("connectRate", 0), res.get("connectTries"), res.get("connectTarget"),
				res.get("connectAddrType", "?"),
				res.get("connectSecs", 0), res.get("connectSecsMax", 0),
				"errors:{}".format(res.get("connectErrors")) if res.get("connectErrors") else ""))
	print("  ROLES    : {}".format(", ".join(res["roles"]) if res["roles"] else "NONE - do not use this dongle"))
	for w in res["notes"]:
		print("             - {}".format(w))


def writeStructured(entries):
	"""the STRUCTURED result, for whoever called us. receiveCommands (plugin menu) picks this file up
	and sends it to indigo together with the text report, in ONE message - so this tool does not have
	to talk to indigo at all, and never has to load piBeaconUtils/sendURL with its non-daemon send
	thread. Written always: it costs nothing and a standalone ssh run can use it too."""
	entriesOut = [{"fingerprint": r["fingerprint"], "roles": r.get("roles"),
					"rateLegacy": r.get("rateLegacy"), "rateExtended": r.get("rateExtended"),
					"notes": r.get("notes")} for r in entries]
	try:
		f = open("/home/pi/pibeacon/temp/qualifyDongle.json", "w")
		f.write(json.dumps(entriesOut))
		f.close()
		try:	os.chmod("/home/pi/pibeacon/temp/qualifyDongle.json", 0o666)
		except Exception:	pass
	except Exception as e:
		print("could not write the structured result: {}".format(e))
	return entriesOut


def saveCatalogue(entries, path, send):
	"""append to the local catalogue, keyed by usb id (or OUI for onboard radios).

	catalogue=none SKIPS this: the file here only ever holds what THIS rpi has seen, so its
	"(n models known)" is a per-pi count, not the shared knowledge it looks like. The catalogue that
	matters is the one the PLUGIN keeps in the indigo preferences directory - it receives the entries
	of every rpi and merges them under the same usb-id/OUI keys. receiveCommands therefore calls us
	with catalogue=none and forwards the structured result instead."""
	# NOTE: only the LOCAL file is skipped by catalogue=none - writeStructured and the optional
	# send=yes below still run, so "catalogue=none send=yes" from the command line still reaches indigo.
	if "{}".format(path).strip().lower() in ("none", "off", ""):
		print("\ncatalogue: entries go to the plugin -> merged into the shared dongleCatalogue.json"
				" in the indigo preferences directory (fed by every rpi), no local copy written")
	else:
		cat = {}
		try:
			if os.path.isfile(path):
				f = open(path)
				cat = json.load(f)
				f.close()
		except Exception:
			cat = {}
		for res in entries:
			fp  = res["fingerprint"]
			key = fp["usb"] or fp["oui"] or fp["mac"]
			cat.setdefault(key, [])
			cat[key].append({"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "host": shell("hostname").strip(),
							"mac": fp["mac"], "manufacturer": fp["manufacturer"], "usbName": fp["usbName"],
							"bus": fp["bus"], "aclMTU": fp["aclMTU"], "scoMTU": fp["scoMTU"], "kernel": fp["kernel"],
							"claimsBLE5": res.get("claimsBLE5"), "rateLegacy": res.get("rateLegacy"),
							"rateExtended": res.get("rateExtended"), "roles": res.get("roles"), "notes": res.get("notes")})
		try:
			f = open(path, "w")
			f.write(json.dumps(cat, indent=2, sort_keys=True))
			f.close()
			try:	os.chmod(path, 0o666)
			except Exception:	pass
			print("\nlocal catalogue updated: {} ({} model(s) seen by THIS rpi)".format(path, len(cat)))
		except Exception as e:
			print("\ncould not write catalogue {}: {}".format(path, e))

	entriesOut = writeStructured(entries)

	if not send:	return
	# OPTIONAL (send=yes): only for a STANDALONE run from the command line - nobody is waiting for
	# us then, so we have to reach indigo ourselves. The plugin menu path does NOT use this.
	try:
		sys.path.append(os.getcwd())
		sys.path.append("/home/pi/pibeacon")
		import piBeaconUtils as U
		import piBeaconGlobals as G
		# without these two, sendURL fails twice over: piBeaconUtils.logger only exists after
		# setLogging (every error inside execSend then dies with NameError: logger), and
		# G.ipOfServer/portOfServer come from the parameters file - the defaults gave
		# "ConnectionRefusedError: [Errno 111]" against the wrong port.
		G.program = "qualifyDongle"
		try:	U.setLogging()
		except Exception:	pass
		try:
			inp, inpRaw, lastRead = U.doRead()
			if inp not in ("", "error"):	U.getGlobalParams(inp)
		except Exception:	pass
		U.sendURL(data={"data": {"dongleQualify": json.dumps(entriesOut)}}, squeeze=False, wait=False)
		print("result sent to indigo (data key: dongleQualify)")

		# HARD EXIT. U.sendURL hands the payload to execSend, a NON-daemon thread running
		# "while G.sendThread['run']: ..." forever. beaconloop/BLEconnect never exit so they never
		# care - but this tool is short lived: main() returns, python then waits for that thread at
		# interpreter shutdown and the process NEVER ends. Visible as "python3 qualifyDongle.py"
		# lingering (with 0% cpu) long after the report was printed. The caller waits on the process,
		# so it kept beaconloop/BLEconnect paused and never sent the full text report on to indigo.
		# Drain the queue first so the payload really goes out, then leave without the shutdown join.
		for _ in range(100):					# up to 10 s for the queue to empty
			try:
				if G.sendThread == {} or G.sendThread["queue"].empty():	break
			except Exception:	break
			time.sleep(0.1)
		time.sleep(2.0)							# execSend polls once per second - let the last one go out
		try:	G.sendThread["run"] = False
		except Exception:	pass
		try:	sys.stdout.flush()
		except Exception:	pass
		os._exit(0)
	except Exception as e:
		print("could not send to indigo: {}".format(e))


def main():
	global forceAddrType
	secs      = 10
	adapters  = []
	connectTo    = ""
	connectTries = 3
	send         = False
	catalogue = "/home/pi/pibeacon/dongleCatalogue.json"
	for a in sys.argv[1:]:
		if a.startswith("connect="):		connectTo = a.split("=", 1)[1].strip().upper()
		elif a.startswith("tries="):		connectTries = int(a.split("=", 1)[1].strip())
		elif a.startswith("send="):			send      = a.split("=", 1)[1].strip().lower() in ("yes", "true", "1")
		elif a.startswith("catalogue="):	catalogue = a.split("=", 1)[1].strip()
		elif a.startswith("addrType="):		forceAddrType = a.split("=", 1)[1].strip().lower()
		elif a.startswith("hci"):			adapters.append(a)
		else:
			try:	secs = int(a)
			except Exception:	pass
	if not adapters:	adapters = listAdapters()
	if not adapters:
		print("no bluetooth adapters found")
		return

	print("BLE dongle role qualification v{}   {} s per measuring phase".format(VERSION, secs))
	if os.path.isfile("/home/pi/pibeacon/temp/beaconloop.pause"):
		print("beaconloop/BLEconnect are PAUSED by the caller (plugin menu) - radios are free")
	else:
		print("REMINDER: beaconloop must NOT be running (sudo pkill -f beaconloop.py; sudo pkill -f master.py)")
	if connectTo:	print("connect test against {} ({} attempts, address type {})".format(connectTo, connectTries,
						"random" if peerAddrType(connectTo) == BDADDR_LE_RANDOM else "public"))
	resetAllAdapters(listAdapters())		# ALL of them, not only the ones we are about to test

	entries = []
	for hci in adapters:
		res = {"fingerprint": fingerprint(hci)}
		res["healthy"] = resetHCI(hci) and res["fingerprint"]["aclMTU"] > 0
		if res["healthy"]:
			sock = openSock(hci)
			st, ev = cmdComplete(sock, OCF_LE_READ_LOCAL_FEATURES)
			res["claimsBLE5"] = bool(st == 0 and len(ev) >= 15 and (ev[8] & 0x10))
			sock.close()
			phaseExtended(hci, secs, res)
			phaseLegacy(hci, secs, res)
			phaseAdvertise(hci, res)
			if connectTo:	phaseConnectRepeat(hci, connectTo, res, connectTries)
		else:
			res["claimsBLE5"] = False
		verdict(res, secs)
		report(res, secs)
		entries.append(res)

	print("\n==== summary ====")
	for res in entries:
		fp = res["fingerprint"]
		# usb id ONLY - no OUI fallback: the OUI is the first 3 bytes of the mac one column to the
		# left, so "B8:27:EB  B8:27:EB:9D:3A:63" said the same thing twice. UART radios have no usb
		# id and simply leave the column empty; the vendor name identifies them.
		print("{:6s} {:18s} {:5s} {:11s} {:26s} -> {}".format(fp["hci"], fp["mac"], fp.get("bus", ""),
				usbText(fp), vendorName(fp),
				", ".join(res["roles"]) if res["roles"] else "NONE"))
	saveCatalogue(entries, catalogue, send)


main()
