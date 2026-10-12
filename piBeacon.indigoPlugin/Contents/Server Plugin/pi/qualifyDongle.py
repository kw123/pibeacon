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
#    sudo python3 qualifyDongle.py 10 stop=no               do NOT stop/start piBeacon (for a caller
#                                                           that already did - receiveCommands does)
#
# piBeacon IS STOPPED AUTOMATICALLY for the measurement and started again when the run ends, also on
# an exception and on ctrl-c. It has to be: a radio that beaconloop is scanning on refuses
# create-connection with ENOSYS and shares its report rate, so a perfectly good dongle is reported as
# "connect unreliable" and "scan too slow" - measured on one rpi minutes apart, the same ASUS at 100%
# with piBeacon stopped and 40% with it running. The old "REMINDER: stop beaconloop first" was
# printed on every such run and read straight past, every time.
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
import signal				# restart piBeacon on ctrl-c / kill - see startPiBeacon()
import atexit				# ... and on a normal end or an exception

VERSION = 2.9

OGF_LE_CTL                 = 0x08
OCF_LE_SET_EVENT_MASK      = 0x0001
OCF_LE_READ_LOCAL_FEATURES = 0x0003
OCF_LE_SET_ADV_PARAMETERS  = 0x0006
OCF_LE_SET_ADV_DATA        = 0x0008
OCF_LE_SET_ADV_ENABLE      = 0x000A
OCF_LE_SET_SCAN_PARAMETERS = 0x000B
OCF_LE_SET_SCAN_ENABLE     = 0x000C
OCF_LE_SET_EXT_ADV_ENABLE  = 0x0039
OCF_LE_EXT_SCAN_PARAMS     = 0x0041
OCF_LE_EXT_SCAN_ENABLE     = 0x0042

SOL_HCI       = 0
HCI_FILTER    = 2
HCI_EVENT_PKT = 0x04

# thresholds, all from measurements on real hardware (scanRateTest, 2026-07):
#   109/s pi onboard broadcom | 92/s good USB | 56/s CSR clone | 24/s ASUS extended | 2.6/s Barrot
SCAN_GOOD      = 80.0		# reports/s: full-time scanner
SCAN_OK        = 40.0		# reports/s: usable scanner - FALLBACK ONLY, see COVERAGE_* below
COVERAGE_GOOD  = 85.0		# % of the macs ANY radio on this rpi heard: full-time scanner
COVERAGE_OK    = 65.0		# % ditto: usable scanner. Two live runs on rpi#2 moved each radio
							# by ~5 points (ASUS 94.3/89.0, onboard 74.3/78.1, UB500 71.4/67.1),
							# so the bands are set wide enough that nobody changes role between runs
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


def followAdapter(mac, oldHci=""):
	"""which hci name carries this MAC right now?

	A USB dongle can RE-ENUMERATE while it is being reset and comes back under a NEW name. Measured
	on a BCM20702A0 (0a5c:21e8) that has no firmware patch installed - the kernel says
	"BCM: firmware Patch file not found: brcm/BCM20702A1-0a5c-21e8.hcd" at every probe - and the log
	then reads "usb 1-1.2: USB disconnect, device number 7" / "new full-speed USB device number 8",
	with the same radio reappearing as hci3 while the tool was still addressing hci0. Everything sent
	to the old name goes to a device node that no longer exists: ACL MTU 0, zero reports, advertising
	"FAILED", and the verdict "ROLES: NONE - do not use this dongle" about a radio that measures
	94.5 reports/s once it is addressed by its new name. The MAC is the only stable identity here,
	which is also why beaconloop pins its roles by MAC.

	Inputs:
	    mac (str): the BD address to look for
	    oldHci (str): the name it used to have, skipped in the search
	Outputs:
	    str: the new hci name, or "" if that MAC is not on the bus at all
	"""
	if not mac:	return ""
	for _try in range(3):
		time.sleep(1.0)							# re-enumeration takes a moment to settle
		for hh in listAdapters():
			if hh == oldHci:	continue
			try:
				if fingerprint(hh).get("mac", "") == mac:	return hh
			except Exception:	pass
	return ""


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
	"""down+up, NEVER "hciconfig reset". HCIDEVRESET does not clear every controller and leaves some
	DOWN: measured here on a BCM20702A0 (0a5c:21e8) that stayed down for the whole run and was duly
	reported as "adapter does not come up properly - unusable" with 0 reports and no advertising -
	a perfectly good dongle, condemned by its own reset. It came back only when the USB device
	re-enumerated, and a plain down+up brought the same dongle up every time afterwards (10/10
	connects right after). beaconloop learned the identical lesson on a different radio, see
	hciNeedsDownUp / temp/hciMuteOnReset.json. The second attempt waits longer: a controller that
	needs re-probing by the kernel is not always back within half a second."""
	for _try in range(2):
		shell("sudo hciconfig {} down".format(hci))
		time.sleep(0.4)
		shell("sudo hciconfig {} up".format(hci))
		time.sleep(0.6 if _try == 0 else 2.0)
		if "UP" in shell("hciconfig {}".format(hci)):	return True
	return False


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
	# down-all then up-all, with NO "hciconfig reset" in between - see resetHCI(): the reset is what
	# left a healthy BCM20702A0 down for an entire run and got it reported as unusable.
	for hci in adapters:
		shell("sudo hciconfig {} down".format(hci))
	time.sleep(0.5)
	for hci in adapters:
		shell("sudo hciconfig {} up".format(hci))
	time.sleep(0.5)
	for hci in adapters:
		# VERIFY, and give a slow controller a second chance before calling it unusable. A USB
		# BCM20702A0 needs noticeably longer than half a second to come back after a down, and this
		# status line printed "DOWN   <-- not usable" for a radio that went on to scan at 94.5/s in
		# the very same run - with its ACL MTU already readable as 1021 on the same line, which is
		# what gave the premature read away. resetHCI does its own down+up and retries once.
		if "UP" not in shell("hciconfig {}".format(hci)):	resetHCI(hci)
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


def macToStr(b6):
	"""HCI carries addresses LSB FIRST - print them the way everyone else writes them."""
	try:	return ":".join("{:02X}".format(b) for b in bytearray(b6)[::-1])
	except Exception:	return "??"


def addrRotates(addrType, mb):
	"""does this address CHANGE OVER TIME, making it useless for comparing one radio against another?

	BLE random addresses carry a subtype in the TOP TWO BITS of their most significant byte - which
	is the LAST byte of the little-endian HCI buffer, and the FIRST one when printed:
	   11 -> static random      - fixed while the device stays powered, comparable
	   01 -> RESOLVABLE private - rotates, typically every 15 minutes
	   00 -> non-resolvable     - rotates
	Only Address_Type 0x01 (Random) has a subtype at all. A public address's first byte is an OUI
	octet, where those same bit patterns mean nothing, so the type field has to be read first - this
	is exactly the case that cannot be decided from the address alone.

	WHY IT MATTERS HERE: the phases run sequentially, so a phone that rotates between two radios'
	windows is counted as a mac each radio "missed". Measured on rpi#2: the ASUS was charged with
	missing 66:B0:1E:B3:DA:65, 69:8C:AE:CA:47:5E and 58:D6:9C:2D:80:7D - three addresses, ~40 msgs
	each, ALL at exactly -67 dBm and all 01xxxxxx. That is one or two phones it had already heard
	under another name, and 23 of the 80 macs in that run were heard by one radio only.

	Inputs:
	    addrType (int): Address_Type from the advertising report
	    mb (bytes): the 6 address bytes, little-endian as the HCI buffer carries them
	Outputs:
	    bool: True when the address is a private one that rotates
	"""
	if addrType != 0x01:	return False
	try:    return (bytearray(mb)[-1] & 0xC0) in (0x40, 0x00)
	except Exception:    return False


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
	perMac    = {}							# mac -> [reports, best rssi], consumed by macCoverage()
	nLegacyPdu, nExtPdu = [0], [0]			# only filled for subevent 0x0D - see the split below
	macsLegacyPdu, macsExtPdu = set(), set()
	rssis     = []
	rssiBad   = [0]							# samples outside the spec range - see the filter below
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
					mb = bytes(ev[7:13])
					aType = ev[6]			# [6]=Address_Type, see addrRotates()
					macs.add(mb)
					r = ev[-1]
				else:
					mb = bytes(ev[8:14])
					aType = ev[7]			# [7]=Address_Type, see addrRotates()
					macs.add(mb)
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
				# PER MAC, counted BEFORE the rssi filter: the report arrived either way, and the
				# count is what decides whether another radio missing this mac means anything.
				ent = perMac.setdefault(mb, [0, -999, 1 if addrRotates(aType, mb) else 0])
				ent[0] += 1
				rssi = r - 256 if r > 127 else r
				# BT Core: RSSI is a signed byte in -127..+20 dBm, and 127 means "not available".
				# Anything outside that is NOT an rssi - it is a txPower/length/flags byte the
				# slicing picked up, which is what "rssi mean/max -71/123 dBm" was: an impossible
				# +123 dBm in the max. A single HCI event can also carry SEVERAL reports (ev[4] =
				# num_reports), and ev[-1] is then only the last one's rssi. Out-of-range samples are
				# DISCARDED and counted, so a parse that drifts shows up as a number on the report
				# instead of quietly skewing the mean and the sensitivity verdict built on it.
				if -127 <= rssi <= 20:
					rssis.append(rssi)
					if rssi > ent[1]:	ent[1] = rssi
				else:
					rssiBad[0] += 1
			except Exception:	pass
	if time.time() - tLast > gapMax:	gapMax = time.time() - tLast
	out = {"n": n, "macs": len(macs), "buckets": buckets, "gapMax": round(gapMax, 1),
			"rssiMean": 0, "rssiMin": 0, "rssiMax": 0, "rssiBad": rssiBad[0],
			"nLegacyPdu": nLegacyPdu[0], "macsLegacyPdu": len(macsLegacyPdu),
			"nExtPdu": nExtPdu[0], "macsExtPdu": len(macsExtPdu),
			"perMac": dict((macToStr(k), v) for k, v in perMac.items())}
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
		# LEAVE THE RADIO IDLE FIRST, as phaseExtended and the connect phase already do.
		# "LE Set Scan Parameters" is DISALLOWED (0x0C) while scanning is enabled - that is
		# the spec, not a quirk - and the down+up in resetHCI hands the adapter straight back
		# to bluetoothd, which re-arms its own background LE scan on the adapters it manages.
		# So a 0x0C here could be the tool's own leftover state rather than the dongle, and it
		# was being read as "this firmware has no legacy scan mode". The ASUS 0b05:1d70 showed
		# exactly that: legCmdStatus [12,12] in a run where its extended scan did 32.9/s from
		# 45 macs. Clearing both scan families first costs two commands whose status we ignore.
		cmdComplete(sock, OCF_LE_SET_SCAN_ENABLE, struct.pack("<BB", 0x00, 0x00))			# legacy scan off
		cmdComplete(sock, OCF_LE_EXT_SCAN_ENABLE, struct.pack("<BBHH", 0x00, 0x00, 0, 0))	# extended scan off
		stP, _ = cmdComplete(sock, OCF_LE_SET_SCAN_PARAMETERS, struct.pack("<BHHBB", 0x01, 0x0010, 0x0010, 0x00, 0x00))
		stE, _ = cmdComplete(sock, OCF_LE_SET_SCAN_ENABLE, struct.pack("<BB", 0x01, 0x00))
		res["legCmdStatus"] = [stP, stE]
		if stP != 0 or stE != 0:
			# 0x0C = Command Disallowed. With both scan families turned off immediately above,
			# the controller has no scan running to object to, so this now really does mean the
			# firmware is locked to the extended command family - the Barrot signature, and
			# "never give this dongle the scan role".
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
		# IDLE FIRST - see phaseLegacy. "LE Set Advertising Parameters" is disallowed (0x0C)
		# while advertising is already enabled, which is the state bluetoothd leaves a powered
		# connectable adapter in. A controller that implements only the extended family also
		# wants its extended sets disabled before it will take the legacy commands, so disable
		# those too: Enable=0 with Num_Sets=0 means "all advertising sets off".
		cmdComplete(sock, OCF_LE_SET_ADV_ENABLE,     struct.pack("<B", 0x00))				# legacy adv off
		cmdComplete(sock, OCF_LE_SET_EXT_ADV_ENABLE, struct.pack("<BB", 0x00, 0x00))		# all ext adv sets off
		cmdComplete(sock, OCF_LE_SET_SCAN_ENABLE,    struct.pack("<BB", 0x00, 0x00))		# and both scans
		cmdComplete(sock, OCF_LE_EXT_SCAN_ENABLE,    struct.pack("<BBHH", 0x00, 0x00, 0, 0))
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
	# THE RADIO MUST BE IDLE FIRST. This phase runs straight after two scan phases and an advertise
	# phase on the SAME radio, and a create-connection on a controller that still has a scan running
	# is refused with ENOSYS (SO_ERROR:38). That cost real verdicts: the ASUS measured 30% here with
	# 7x ENOSYS and 100% with the scan stopped, and the onboard radio - the proven connector all
	# along - was marked "connect(weak)" off a single ENOSYS. phaseExtended already clears a stuck
	# scan this way before it starts; the connect phase never did.
	try:
		sock = openSock(hci)
		try:
			cmdComplete(sock, OCF_LE_SET_SCAN_ENABLE, struct.pack("<BB", 0x00, 0x00))			# legacy scan off
			cmdComplete(sock, OCF_LE_EXT_SCAN_ENABLE, struct.pack("<BBHH", 0x00, 0x00, 0, 0))	# extended scan off
			cmdComplete(sock, OCF_LE_SET_ADV_ENABLE,  struct.pack("<B", 0x00))					# and advertising
		finally:
			sock.close()
	except Exception:
		pass
	time.sleep(0.5)

	# ONE WARM-UP ATTEMPT, NOT COUNTED. Even with the scan disabled above, the first connect after a
	# radio has been scanning routinely fails once or twice and then succeeds for the rest of the
	# run - measured on three different dongles, including 3 ENOSYS in a row followed by 7 clean
	# connects at 0.23 s. Which radio happens to eat that leftover state is luck, and it should not
	# decide the report. The result is kept and printed, so the warm-up is never silently hidden.
	warm = {"fingerprint": res["fingerprint"]}
	phaseConnect(hci, mac, warm, timeout)
	res["connectWarmup"] = "ok" if warm.get("connectOk") else "{}".format(warm.get("connectErr", "?"))
	time.sleep(1.0)

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
# the piBeacon programs that HOLD RADIOS, found running at startup. Not cosmetic: every number in a
# run made while these are up is a measurement of a shared radio, and it reads exactly like a bad
# dongle. Measured on one rpi within minutes: the same ASUS 100% connect with piBeacon stopped and
# 40% (6x ENOSYS) with beaconloop scanning on it. So it is said once at the top AND carried into
# every adapter's notes - which is also what reaches the shared catalogue.
piBeaconRunning = [""]
stoppedByUs     = [False]		# did WE stop piBeacon? then WE have to start it again - see startPiBeacon


def findPiBeacon():
	"""the running piBeacon programs that hold radios, as "pid command-line" lines ("" = none).

	receiveCommands is deliberately NOT in this list: when the plugin menu runs this tool, that is
	our own parent - killing it would kill the run and the report with it."""
	try:	return shell("pgrep -af 'python.*(beaconlo[o]p\\.py|BLEconne[c]t\\.py|mast[e]r\\.py)' || true").strip()
	except Exception:	return ""


def stopPiBeacon():
	"""stop the radio users. Supervisors FIRST: master.sh restarts master.py within 90 s and
	master.py restarts everything else, so killing the workers first just feeds them back."""
	for pat in ["mast[e]r.sh", "startmast[e]r.sh"]:
		shell("sudo pkill -f '{}'".format(pat))
	time.sleep(1.0)
	for pat in ["mast[e]r.py", "beaconlo[o]p.py", "BLEconne[c]t.py"]:
		shell("sudo pkill -9 -f '{}'".format(pat))
	time.sleep(2.0)
	stoppedByUs[0] = True


def startPiBeacon():
	"""start it again, but ONLY if we were the one who stopped it.

	Registered with atexit AND called from the signal handler, because the failure mode here is the
	worst one this tool has: nothing on the rpi brings master back by itself - no cron entry, no
	systemd unit, callbeacon.py runs only at boot - so a tool that stops piBeacon and then exits
	through an exception or a ctrl-c would leave the rpi dead until someone noticed. ctrl-c during a
	measurement is not hypothetical, it happened while testing this."""
	if not stoppedByUs[0]:	return
	stoppedByUs[0] = False							# never twice
	shell("cd /home/pi/pibeacon; nohup /bin/bash master.sh yes > /dev/null 2>&1 &")
	print("\npiBeacon restarted (master.sh -> master.py -> beaconloop/BLEconnect)")


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

	# A radio that is NOT THERE gets no roles, and no findings either. Everything below counts
	# delivered packets, and an adapter that left the bus delivers none - so it collected "no BLE5",
	# "scan too slow" and "cannot advertise" as though those were discoveries about the dongle, and
	# was then handed "connect" by the ACL MTU fallback at the bottom, read from a fingerprint taken
	# BEFORE it vanished. Seen in the fleet sweep: an onboard radio that had dropped off the bus
	# mid-run was reported as "ROLES: connect".
	if res.get("vanished") or not res.get("healthy", True):
		if res.get("vanished"):
			why = ["{} was not on the bus during this run - nothing was measured and no role can be"
					" judged. This is NOT a verdict on the dongle".format(res.get("vanished"))]
		else:
			why = ["the adapter did not come up - nothing was measured and no role can be judged"]
		res["rateLegacy"], res["rateExtended"] = 0.0, 0.0
		res["roles"], res["notes"] = [], why
		return [], why

	rLeg   = res.get("nLeg", 0) / float(secs) if res.get("nLeg", 0) > 0 else 0.0
	rExt   = res.get("nExt", 0) / float(secs) if res.get("nExt", 0) > 0 else 0.0
	roles, why = [], []

	if rExt >= EXT_MIN_RATE and res.get("uExt", 0) >= EXT_MIN_MACS:
		roles.append("BLE5-listener")
	else:
		why.append("no BLE5: {:.1f} BLE5 reports/s from {} macs".format(rExt, res.get("uExt", 0)))

	# 0x0C Command Disallowed on either legacy scan command = this controller has NO BLE4 scan mode
	# at all (BLE5-only firmware, e.g. the Barrot/UGREEN 33fa:0012). Needed in TWO places: here, and
	# in the combined-scanner test below which used to award such a radio a perfect score.
	legRejected = (res.get("legCmdStatus", [0, 0])[0] == 0x0C or res.get("legCmdStatus", [0, 0])[1] == 0x0C)

	# SCAN ROLE ON MAC COVERAGE, not reports/s - see coverageIntoEntries(). The rate threshold
	# stays as the FALLBACK, because coverage needs at least two radios to compare and an rpi
	# with a single radio has nothing to measure itself against.
	cov = res.get("covPct")
	if legRejected:
		why.append("BLE4 scan commands REJECTED (0x0C) - BLE5-only firmware, cannot be the scan radio")
	elif cov is not None:
		if cov >= COVERAGE_OK:
			roles.append("scan-BLE4" + ("" if cov >= COVERAGE_GOOD else "(weak)"))
			why.append("scan judged on COVERAGE: heard {}/{} of the macs any radio here heard = {:.0f}%"
				" at {:.1f} reports/s".format(res.get("covHeard", 0), res["covTotal"], cov, rLeg))
		else:
			why.append("scan coverage too low: heard only {}/{} macs = {:.0f}% (need {:.0f}%),"
				" even at {:.1f} reports/s".format(res.get("covHeard", 0), res["covTotal"],
				cov, COVERAGE_OK, rLeg))
	elif rLeg >= SCAN_OK:
		roles.append("scan-BLE4" + ("" if rLeg >= SCAN_GOOD else "(weak)"))
	else:
		why.append("scan too slow: {:.1f}/s (need {:.0f}) - only one radio here, so there is no"
			" coverage to compare against".format(rLeg, SCAN_OK))

	# ONE radio for BLE4+BLE5. A BT5 controller is REQUIRED to report legacy advs while in extended
	# mode (event type bit 4), but how much it delivers is firmware - so it is measured, not assumed.
	# Judged by COVERAGE + samples per summary window, NOT by reports/s: see COMBINED_MIN_* above.
	rLegInExt = res.get("nExtLegacyPdu", 0) / float(secs)
	uLegInExt = res.get("uExtLegacyPdu", 0)
	perMacMin = (60.0 * rLegInExt / uLegInExt) if uLegInExt > 0 else 0.0
	res["combinedPerMacPerMin"] = round(perMacMin, 1)
	uLegOwn  = res.get("uLeg", 0)
	# A radio with no BLE4 scan mode hears 0 macs in BLE4 mode, and the old "else 100.0" then handed
	# it PERFECT coverage of a set that does not exist. That is how the BLE5-only UGREEN/Barrot
	# earned "scan-BLE4+BLE5" on the very same report that said "BLE4 scan commands REJECTED (0x0C)
	# - cannot be the scan radio", and printed "reaches 100% of the macs it hears in BLE4 mode
	# (8 of 0)". A combined scanner is one radio REPLACING a BLE4 scanner plus a BLE5 listener;
	# with no BLE4 mode there is nothing to replace and nothing to compare against.
	noLegacyMode = legRejected or uLegOwn == 0
	coverage = (100.0 * uLegInExt / uLegOwn) if uLegOwn > 0 else 0.0
	# capped for DISPLAY and for the catalogue: extended mode can legitimately hear MORE macs than
	# the legacy run did (the ASUS reported "104%"), which reads like a bug. The raw counts are
	# printed next to it, so nothing is hidden.
	covShown = min(coverage, 100.0)
	res["combinedCoveragePct"] = round(covShown, 0)
	if noLegacyMode:
		why.append("not a combined BLE4+BLE5 scanner: this radio has no BLE4 scan mode at all, so the"
					" {} macs it hears in BLE5 mode cannot be compared with a BLE4 run".format(uLegInExt))
	elif coverage >= COMBINED_MIN_COVERAGE and perMacMin >= COMBINED_MIN_PER_MIN and rExt >= EXT_MIN_RATE:
		roles.append("scan-BLE4+BLE5")
		why.append("one radio can do BLE4+BLE5 here: in BLE5 mode it still reaches {:.0f}% of the macs it hears in BLE4 mode ({} vs {}), {:.0f} reports per mac per minute".format(
					covShown, uLegInExt, uLegOwn, perMacMin))
	elif rExt >= EXT_MIN_RATE:
		if coverage < COMBINED_MIN_COVERAGE:
			why.append("not a combined BLE4+BLE5 scanner: in BLE5 mode it reaches only {:.0f}% of the macs it hears in BLE4 mode ({} vs {})".format(
						covShown, uLegInExt, uLegOwn))
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
	# FIRST note, not last: this one changes how every other line on the adapter has to be read, and
	# it travels with the entry into the shared catalogue so a contaminated run cannot quietly become
	# received wisdom about a dongle model.
	if piBeaconRunning[0] != "":
		why.insert(0, "MEASURED WHILE PIBEACON WAS RUNNING - the radios were shared, so these rates and"
					" connect results are not a verdict on this dongle")

	# ONBOARD RADIO = SAME SILICON AS WIFI, always. Every Pi's built-in Bluetooth is one die
	# with the WiFi - BCM43430A1 on a 3B, BCM43455 on a 3B+/4 - sharing a single antenna and
	# time-sliced with it by a coexistence scheduler. This is stated UNCONDITIONALLY and
	# WITHOUT reading wlan0: the state at measuring time says nothing about the state next
	# month, and a radio that is fine today because wlan0 happens to be down becomes the
	# wrong scan radio the moment someone switches WiFi on. The rate is not demoted - an
	# rpi whose only radio is the onboard one still has to scan with it.
	if fp.get("bus", "") == "UART":
		why.append("onboard radio: one die and one antenna shared with WiFi, time-sliced. This"
			" rate holds only while WiFi is unused and will drop if it is ever switched on -"
			" prefer a USB dongle for the scan role")
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
		# "unusable" is a verdict on a DONGLE. A radio that left the usb bus is not a bad dongle, it
		# is not here - and saying so points at the real cause (re-enumeration, a missing firmware
		# patch, a power or cabling problem) instead of at the hardware.
		if res.get("vanished"):
			# bus-aware: the onboard UART radio is not on the usb bus at all, so "re-enumeration" and
			# "check dmesg | grep usb" are the wrong advice for it. Seen on an rpi whose B8:27:EB
			# onboard radio disappeared mid-run while that same rpi was reporting under-voltage.
			if "{}".format(fp.get("bus", "")).upper() == "UART":
				print("  HEALTH   : {} (the ONBOARD uart radio) disappeared during the run - it cannot"
						" re-enumerate on usb, so look at the bluetooth service and at POWER:"
						" 'dmesg | grep -i -e bluetooth -e voltage' and 'vcgencmd get_throttled'."
						" This is NOT a verdict on the radio".format(res.get("vanished")))
			else:
				print("  HEALTH   : {} is NO LONGER ON THE BUS under any hci name - it disconnected during"
						" the run (usb re-enumeration?). Check 'dmesg | grep -i usb' and whether its"
						" firmware patch is installed; this is NOT a verdict on the dongle".format(res.get("vanished")))
		else:
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
		# never silent about discarded samples: a handful is the odd malformed report, a large share
		# means the rssi is being read from the wrong byte and the mean above is not to be trusted.
		if pr.get("rssiBad", 0) > 0:
			print("             {} of {} {} reports had an out-of-range rssi (not -127..+20 dBm) and were not counted".format(
					pr.get("rssiBad"), pr.get("n", 0) , label))
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
		# the uncounted warm-up is PRINTED, never hidden: a warm-up that failed with SO_ERROR:38 is
		# the proof that this radio needed one, and the reason the counted attempts look clean.
		if res.get("connectWarmup", "ok") != "ok":
			print("             warm-up attempt (not counted) failed with {} - leftover scan state on this radio".format(
					res.get("connectWarmup")))
	if res["roles"]:					noRoles = ", ".join(res["roles"])
	elif res.get("vanished"):			noRoles = "none judged - the radio was not on the bus"
	elif not res.get("healthy", True):	noRoles = "none judged - the adapter did not come up"
	else:								noRoles = "NONE - do not use this dongle"
	print("  ROLES    : {}".format(noRoles))
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


COVERAGE_MUST_HEAR = 3			# reports the best radio needs before a mac counts as missable


def _coverageData(entries):
	"""the maths behind the coverage section, separated from the printing because the SCAN ROLE is
	decided from it - and that has to happen before any adapter's report is written, while
	macCoverage() prints after the summary.

	Inputs:
	    entries (list): per-adapter result dicts, phases already run
	Outputs:
	    tuple: (obs, ref, total) - obs is [(label, {mac: [reports, rssi]})] per radio, ref is
	           {mac: [best reports, best rssi, how many radios heard it]}, total is len(ref).
	           obs is [] when fewer than 2 radios delivered anything, i.e. nothing to compare.
	           The 4th value is how many ROTATING addresses were excluded - see addrRotates().
	"""
	obs, rotSeen = [], set()
	for res in entries:
		if not res.get("healthy"):	continue
		fp	   = res["fingerprint"]
		merged = {}
		for key in ("profLeg", "profExt"):
			for mac, v in ((res.get(key) or {}).get("perMac", {})).items():
				# ROTATING ADDRESSES ARE NOT COMPARABLE and are left out of the union entirely -
				# see addrRotates(). They are not dropped silently: the count is printed.
				if len(v) > 2 and v[2]:
					rotSeen.add(mac)
					continue
				# BEST OF THE TWO MODES, not the sum: in production the radio runs ONE of them, so
				# adding legacy and extended would credit it with a coverage it never has at once.
				e = merged.setdefault(mac, [0, -999])
				if v[0] > e[0]:	e[0] = v[0]
				if v[1] > e[1]:	e[1] = v[1]
		res["_covHeard"] = merged
		if merged:	obs.append(("{} {}".format(fp["hci"], vendorName(fp) or usbText(fp) or fp["mac"]), merged))
	if len(obs) < 2:
		return [], {}, 0, len(rotSeen)
	ref = {}
	for _lab, m in obs:
		for mac, v in m.items():
			e = ref.setdefault(mac, [0, -999, 0])
			if v[0] > e[0]:	e[0] = v[0]			# best observer's report count
			if v[1] > e[1]:	e[1] = v[1]			# best observer's rssi
			e[2] += 1							# how many radios heard it at all
	return obs, ref, len(ref), len(rotSeen)


def coverageIntoEntries(entries):
	"""store each radio's coverage on its own result dict, so verdict() can judge the scan role on
	MAC COVERAGE instead of reports/s. Measured on rpi#2: the onboard radio delivered 821 reports in
	10 s - more than both dongles together - and heard 57 of 73 macs, while the ASUS BT500 heard 65
	at two thirds the rate. piBeacon summarises every ~60 s and keeps an AVERAGE rssi, so a tag the
	radio never hears is lost outright and a tag heard 80 times instead of 50 is worth nothing extra.
	"""
	_obs, ref, total, _nRot = _coverageData(entries)
	for res in entries:
		res["covTotal"] = total
		if total:
			heard = len(res.get("_covHeard", {}) or {})
			res["covHeard"] = heard
			res["covPct"]   = round(100.0 * heard / float(total), 1)


def macCoverage(entries, secs):
	"""WHICH macs does a slower radio MISS, and do the missed ones matter?

	"the uart heard 59 macs, the tp-link 50" says nothing on its own. The 9 missing ones could be
	chatty neighbours the slower radio cannot keep up with - a real defect - or tags that advertise
	once a minute and simply did not transmit during its window. THE MESSAGE COUNT DECIDES IT.

	Every phase measures for the same number of seconds, so a mac the best observer heard >=3 times
	has an advertising interval short enough that it MUST transmit again inside any other window of
	that length. Missing such a mac is a real miss. Below 3 reports the comparison is inconclusive,
	so those are listed separately instead of being scored - otherwise a slow radio gets blamed for
	the sampling, which is exactly the mistake this whole report exists to avoid.

	THE PHASES ARE SEQUENTIAL, not simultaneous: each radio gets its own window, a minute or more
	apart. That is why the 3-report bar exists, and it is printed with the result so nobody reads
	these percentages as a same-instant comparison.

	The rssi line is the diagnosis. If the macs a radio missed were weaker than the ones it heard, it
	is a sensitivity/antenna limit and the fix is placement. If they were just as strong, the radio is
	dropping reports it could hear - a throughput limit, and no amount of placement helps.

	Inputs:
	    entries (list): the per-adapter result dicts, after the phases have run
	    secs (float): the measuring window each phase used
	Outputs:
	    None: prints the coverage section; returns early with fewer than 2 measured radios
	"""
	obs, ref, total, nRot = _coverageData(entries)
	if not obs:	return
	MUST_HEAR = COVERAGE_MUST_HEAR
	print("\n==== mac coverage: {} distinct macs, heard by {} radios ====".format(total, len(obs)))
	print("   each radio measured in its OWN {:.0f}s window, minutes apart - so a mac is only scored as".format(secs))
	print("   MISSED when the best radio heard it >={} times, which means its interval is short enough".format(MUST_HEAR))
	print("   that it had to transmit again during every other window too. Rarer macs are listed apart.")
	if nRot:
		print("   {} rotating private address(es) left out of the comparison - they change between"
			" the windows, so each radio hears the same phone under a different name".format(nRot))
	uniq = [mac for mac, e in ref.items() if e[2] == 1]
	if uniq:
		print("   {} mac(s) were heard by ONE radio only - those are what the differences are made of".format(len(uniq)))
	for lab, m in obs:
		missReal, missRare = [], []
		for mac, e in ref.items():
			if mac in m:	continue
			if e[0] >= MUST_HEAR:	missReal.append((mac, e))
			else:					missRare.append((mac, e))
		heardR = [v[1] for v in m.values() if v[1] > -999]
		missR  = [e[1] for _mac, e in missReal if e[1] > -999]
		msgs   = sum(v[0] for v in m.values())
		# THE SUM MUST RECONCILE ON THE LINE. "heard 65/73 ... real misses: 1" reads as "only one
		# mac missing" while 8 are: 1 scored and 7 below the bar. Print the total missing and
		# its split, so heard + missing = total is visible instead of having to be worked out.
		print("\n{:32s} heard {:3d}/{:3d} = {:5.1f}%  {:5d} msgs   missing {:2d} = {} scored + {} too rare to judge".format(
				lab[:32], len(m), total, 100.*len(m)/float(total), msgs,
				len(missReal) + len(missRare), len(missReal), len(missRare)))
		# THREE outcomes, not two, and only with enough missed macs to mean anything. The first
		# live run compared ONE missed mac at -40 dBm against 66 heard at -81 dBm and announced
		# "just as strong: it is dropping reports it can hear" - drawn from a single sample, and
		# backwards: -40 is 41 dB STRONGER than the average, which is not a sensitivity story at
		# all. A mac that is both very strong and heard by one radio only was almost certainly not
		# transmitting during the other windows, so say that instead of blaming the radio.
		if heardR and len(missR) >= 3:
			mh, mm = sum(heardR)/float(len(heardR)), sum(missR)/float(len(missR))
			if   mm < mh - 5.:	what = "the missed ones are WEAKER: sensitivity or placement"
			elif mm > mh + 5.:	what = "the missed ones are STRONGER - not range: they were probably not transmitting in this window"
			else:				what = "the missed ones are JUST AS STRONG: it is dropping reports it can hear"
			print("     rssi heard {:4.0f} dBm  vs  missed {:4.0f} dBm  ->  {}".format(mh, mm, what))
		elif heardR:
			print("     rssi heard {:4.0f} dBm over {} macs - only {} scored miss(es), too few to compare".format(
					sum(heardR)/float(len(heardR)), len(heardR), len(missR)))
		for mac, e in sorted(missReal, key=lambda x: -x[1][0])[:12]:
			print("     MISSED {}  best radio: {:4d} msgs at {:4d} dBm, heard by {} of {} radios".format(
					mac, e[0], e[1], e[2], len(obs)))
		if len(missReal) > 12:
			print("     ... and {} more".format(len(missReal) - 12))


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
	# stop=no: for a caller that has ALREADY stopped piBeacon and will restart it itself -
	# receiveCommands (the plugin menu) does exactly that. Without it we would restart master at the
	# end of OUR run, master.py would wipe temp/ on startup, and the structured result would be gone
	# before receiveCommands had read it.
	doStop       = True
	catalogue = "/home/pi/pibeacon/dongleCatalogue.json"
	for a in sys.argv[1:]:
		if a.startswith("connect="):		connectTo = a.split("=", 1)[1].strip().upper()
		elif a.startswith("stop="):			doStop    = a.split("=", 1)[1].strip().lower() not in ("no", "false", "0")
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

	# ARM THE RESTART BEFORE ANYTHING IS STOPPED. atexit covers a normal end and an exception;
	# the signal handler covers ctrl-c and kill, which atexit does NOT see. os._exit in the handler
	# skips atexit, so the restart is done first, by hand.
	atexit.register(startPiBeacon)
	def _onSignal(_sig, _frm):
		print("\ninterrupted - restarting piBeacon before leaving")
		startPiBeacon()
		os._exit(1)
	for _s in ("SIGINT", "SIGTERM", "SIGHUP"):
		try:	signal.signal(getattr(signal, _s), _onSignal)
		except Exception:	pass

	print("BLE dongle role qualification v{}   {} s per measuring phase".format(VERSION, secs))
	if os.path.isfile("/home/pi/pibeacon/temp/beaconloop.pause"):
		print("beaconloop/BLEconnect are PAUSED by the caller (plugin menu) - radios are free")
	else:
		# a REMINDER is not enough - it was printed on every run that was then read as a dongle
		# verdict anyway. Look instead, and by default DO something about it: a radio that is being
		# scanned on refuses create-connection with ENOSYS and shares its report rate, so a good
		# dongle comes out as "connect unreliable" and "scan too slow".
		busy = findPiBeacon()
		if busy != "" and doStop:
			print("piBeacon is running - stopping it for this measurement:")
			for _ln in busy.split("\n"):	print("      {}".format(_ln.strip()))
			stopPiBeacon()
			busy = findPiBeacon()
			if busy == "":	print("   stopped - it is started again automatically when this run ends")
		piBeaconRunning[0] = busy
		if busy != "":
			print("")
			print("*** piBeacon IS RUNNING - the numbers below are NOT a verdict on these dongles ***")
			for _ln in busy.split("\n"):
				print("      {}".format(_ln.strip()))
			print("    Stop piBeacon first:   sudo bash /home/pi/pibeacon/stopAll.sh")
			print("    and start it again:    sudo python3 /home/pi/callbeacon.py &")
			print("")
		elif not stoppedByUs[0]:
			print("piBeacon is not running - the radios are free")
	if connectTo:	print("connect test against {} ({} attempts, address type {})".format(connectTo, connectTries,
						"random" if peerAddrType(connectTo) == BDADDR_LE_RANDOM else "public"))
	resetAllAdapters(listAdapters())		# ALL of them, not only the ones we are about to test

	# Which MAC each name carries, read BEFORE we start resetting things. Once a dongle has
	# re-enumerated, fingerprint(oldName) returns nothing at all and the MAC needed to find it again
	# would be lost - so it has to be captured up front, not looked up at the moment of failure.
	_macWanted = {}
	for hh in adapters:
		try:	_macWanted[hh] = fingerprint(hh).get("mac", "")
		except Exception:	_macWanted[hh] = ""

	entries = []
	for hci in adapters:
		res = {"fingerprint": fingerprint(hci)}
		_up  = resetHCI(hci)
		# the radio may have RE-ENUMERATED under a new name while we reset it - follow it by MAC
		# rather than condemning a dongle that is alive and well a few hci numbers further along.
		if not _up or res["fingerprint"]["aclMTU"] == 0:
			_mac = res["fingerprint"]["mac"] or _macWanted.get(hci, "")
			_new = followAdapter(_mac, hci)
			if _new != "":
				print("   {} re-enumerated as {} (same mac {}) - following it".format(hci, _new, _mac))
				hci  = _new
				res  = {"fingerprint": fingerprint(hci)}
				_up  = "UP" in shell("hciconfig {}".format(hci)) or resetHCI(hci)
			elif _mac != "":
				res["vanished"] = _mac
		res["healthy"] = _up and res["fingerprint"]["aclMTU"] > 0
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
		entries.append(res)
		if res["healthy"]:
			print("   {} measured: BLE4 {:.1f}/s from {} macs, BLE5 {:.1f}/s from {} macs".format(
				res["fingerprint"]["hci"], res.get("nLeg", 0)/float(secs), res.get("uLeg", 0),
				res.get("nExt", 0)/float(secs), res.get("uExt", 0)))

	# EVERY ADAPTER IS MEASURED BEFORE ANY IS JUDGED. The scan role is decided on mac coverage,
	# which is a comparison between the radios of this rpi - so no report can be written until
	# the last radio has been measured. The one-line progress above is why that is not silence.
	coverageIntoEntries(entries)
	for res in entries:
		verdict(res, secs)
		report(res, secs)

	print("\n==== summary ====")
	for res in entries:
		fp = res["fingerprint"]
		# usb id ONLY - no OUI fallback: the OUI is the first 3 bytes of the mac one column to the
		# left, so "B8:27:EB  B8:27:EB:9D:3A:63" said the same thing twice. UART radios have no usb
		# id and simply leave the column empty; the vendor name identifies them.
		print("{:6s} {:18s} {:5s} {:11s} {:26s} -> {}".format(fp["hci"], fp["mac"], fp.get("bus", ""),
				usbText(fp), vendorName(fp),
				", ".join(res["roles"]) if res["roles"] else "NONE"))
	macCoverage(entries, secs)
	saveCatalogue(entries, catalogue, send)


main()
