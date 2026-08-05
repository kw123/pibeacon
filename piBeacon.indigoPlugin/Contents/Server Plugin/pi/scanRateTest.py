#!/usr/bin/env python
# -*- coding: utf-8 -*-
####################
# scanRateTest.py - standalone BLE scan delivery-rate benchmark
#
# Measures how many advertising reports each Bluetooth adapter delivers in
# LEGACY scan mode vs BT5 EXTENDED scan mode.  The two command families are
# mutually exclusive until an HCI reset (spec: after extended commands the
# legacy scan commands return 0x0C Command Disallowed), so every phase gets
# its own controller reset.
#
# Three phases per adapter:
#    1. LEGACY   scan via raw HCI socket   (what beaconloop uses on non-BLE5 dongles)
#    2. EXTENDED scan via raw HCI socket   (what beaconloop uses on BLE5 dongles)
#    3. CLASSIC  hcitool lescan + hcidump  (the old pre-socket acquisition method)
#
# usage:
#    sudo python3 scanRateTest.py                 -> all adapters, 10 s per phase
#    sudo python3 scanRateTest.py 20              -> all adapters, 20 s per phase
#    sudo python3 scanRateTest.py 10 hci0 hci1    -> only these adapters
#
# phase 3 needs the bluez-hcidump package (hcidump in PATH); it is skipped if missing.
#
# IMPORTANT: stop beaconloop first or the results are invalid (it owns the
# radio and keeps reconfiguring scanning):
#    sudo pkill -f beaconloop.py ; sudo pkill -f master.py
# (restart afterwards with the usual autostart / reboot)
#
# python3 only - uses the native AF_BLUETOOTH raw HCI socket (no pybluez needed).
####################
from __future__ import print_function
import sys
import time
import struct
import subprocess
import re

import os
import select
import socket as pySocket

VERSION = 1.0

OGF_LE_CTL                 = 0x08
OCF_LE_SET_SCAN_PARAMETERS = 0x000B
OCF_LE_SET_SCAN_ENABLE     = 0x000C
OCF_LE_READ_LOCAL_FEATURES = 0x0003
OCF_LE_SET_EVENT_MASK      = 0x0001
OCF_LE_EXT_SCAN_PARAMS     = 0x0041
OCF_LE_EXT_SCAN_ENABLE     = 0x0042

SOL_HCI       = 0
HCI_FILTER    = 2
HCI_EVENT_PKT = 0x04


def shell(cmd):
	try:
		out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
		if not isinstance(out, str): out = out.decode("utf-8", "replace")
		return out
	except Exception as e:
		return "{}".format(e)


def listAdapters():
	return re.findall(r"^(hci\d+):", shell("hciconfig"), re.M)


def adapterInfo(hci):
	out  = shell("hciconfig -a {}".format(hci))
	mac  = ""
	manu = ""
	m = re.search(r"BD Address: ([0-9A-F:]{17})", out)
	if m: mac = m.group(1)
	m = re.search(r"Manufacturer: (.*)", out)
	if m: manu = m.group(1).strip()
	return mac, manu


def resetHCI(hci):
	shell("sudo hciconfig {} reset".format(hci))
	time.sleep(0.3)
	# a DOWN adapter (e.g. never used by beaconloop) stays down after reset -
	# bring it up explicitly or the socket bind fails with "Network is down"
	shell("sudo hciconfig {} up".format(hci))
	time.sleep(0.3)
	if "UP" not in shell("hciconfig {}".format(hci)):
		print("  WARNING  : {} did not come UP after reset+up - dongle may be faulty".format(hci))


def openSock(hci):
	devId = int(hci.replace("hci", ""))
	sock  = pySocket.socket(pySocket.AF_BLUETOOTH, pySocket.SOCK_RAW, pySocket.BTPROTO_HCI)
	sock.bind((devId,))
	# struct hci_filter: u32 type_mask, u32 event_mask[2], u16 opcode (+2 pad = 16 bytes,
	# kernels >= 6.1.91 reject shorter buffers): pass all HCI events
	flt = struct.pack("<IIIH2x", 1 << HCI_EVENT_PKT, 0xFFFFFFFF, 0xFFFFFFFF, 0)
	sock.setsockopt(SOL_HCI, HCI_FILTER, flt)
	sock.settimeout(0.5)
	return sock


def sendCmd(sock, ocf, params):
	"""raw HCI command packet: 0x01, opcode (OGF<<10|OCF), plen, params"""
	opcode = (OGF_LE_CTL << 10) | ocf
	sock.send(b"\x01" + struct.pack("<HB", opcode, len(params)) + params)


def cmdComplete(sock, ocf, params):
	"""send one LE command, wait for its command-complete; returns (status, event) - status -1 on timeout"""
	sendCmd(sock, ocf, params)
	opcode = (OGF_LE_CTL << 10) | ocf
	t0 = time.time()
	while time.time() - t0 < 1.2:
		try:	ev = bytearray(sock.recv(255))
		except Exception:	break
		if len(ev) >= 7 and ev[1] == 0x0E and (ev[4] | (ev[5] << 8)) == opcode:
			return ev[6], ev
	return -1, bytearray()


def countReports(sock, secs, subevent):
	"""count LE meta events with the given subevent (0x02 legacy adv report, 0x0D extended);
	also counts DISTINCT macs as a coverage measure"""
	n    = 0
	macs = set()
	t0   = time.time()
	while time.time() - t0 < secs:
		try:	ev = bytearray(sock.recv(512))
		except Exception:	continue
		if len(ev) > 4 and ev[1] == 0x3E and ev[3] == subevent:
			n += 1
			try:
				if subevent == 0x02:	macs.add(bytes(ev[7:13]))		# num_reports, evt_type, addr_type, then mac
				else:					macs.add(bytes(ev[9:15]))		# ext: num_reports, evt_type(2), addr_type, then mac
			except Exception:
				pass
	return n, len(macs)


def testAdapter(hci, secs):
	mac, manu = adapterInfo(hci)
	print("")
	print("==== {}  mac:{}  ({}) ====".format(hci, mac, manu))
	result = {"hci": hci, "mac": mac, "manu": manu, "nLeg": -1, "uLeg": 0, "nExt": -1, "uExt": 0, "ble5": False}

	# ---- phase 1: LEGACY (fresh command family after reset) ----
	resetHCI(hci)
	sock = openSock(hci)
	try:
		stF, evF = cmdComplete(sock, OCF_LE_READ_LOCAL_FEATURES, b"")
		ble5 = (stF == 0 and len(evF) >= 15 and bool(evF[8] & 0x10))	# feature bit 12
		result["ble5"] = ble5

		stP, _ = cmdComplete(sock, OCF_LE_SET_SCAN_PARAMETERS, struct.pack("<BHHBB", 0x01, 0x0010, 0x0010, 0x00, 0x00))
		stE, _ = cmdComplete(sock, OCF_LE_SET_SCAN_ENABLE,     struct.pack("<BB", 0x01, 0x00))
		if stP == 0 and stE == 0:
			print("  LEGACY   scanning {} s ...".format(secs))
			nLeg, uLeg = countReports(sock, secs, 0x02)
			result["nLeg"], result["uLeg"] = nLeg, uLeg
			print("  LEGACY   : {:5d} reports = {:6.1f}/s   from {:3d} distinct macs".format(nLeg, nLeg / float(secs), uLeg))
		else:
			print("  LEGACY   : commands rejected (params:0x{:02X} enable:0x{:02X})".format(stP & 0xFF, stE & 0xFF))
	finally:
		try:	sock.close()
		except Exception:	pass

	# ---- phase 2: EXTENDED (own reset, own command family) ----
	if not result["ble5"]:
		print("  EXTENDED : not supported (LE feature bit 12 not set)")
	else:
		resetHCI(hci)
		sock = openSock(hci)
		try:
			stM, _ = cmdComplete(sock, OCF_LE_SET_EVENT_MASK,  struct.pack("<Q", 0x000FFFFF))		# incl. bit12 ext adv report
			stP, _ = cmdComplete(sock, OCF_LE_EXT_SCAN_PARAMS, struct.pack("<BBBBHH", 0x00, 0x00, 0x01, 0x01, 0x0010, 0x0010))
			stE, _ = cmdComplete(sock, OCF_LE_EXT_SCAN_ENABLE, struct.pack("<BBHH", 0x01, 0x00, 0x0000, 0x0000))
			if stP == 0 and stE == 0:
				print("  EXTENDED scanning {} s ...".format(secs))
				nExt, uExt = countReports(sock, secs, 0x0D)
				result["nExt"], result["uExt"] = nExt, uExt
				print("  EXTENDED : {:5d} reports = {:6.1f}/s   from {:3d} distinct macs".format(nExt, nExt / float(secs), uExt))
			else:
				print("  EXTENDED : commands rejected (mask:0x{:02X} params:0x{:02X} enable:0x{:02X})".format(stM & 0xFF, stP & 0xFF, stE & 0xFF))
		finally:
			try:	sock.close()
			except Exception:	pass

	# ---- phase 3: CLASSIC hcitool lescan + hcidump (the old acquisition method) ----
	result["nDump"], result["uDump"] = -1, 0
	if shell("which hcidump").strip() == "":
		print("  HCIDUMP  : skipped - hcidump not installed (apt install bluez-hcidump)")
	else:
		resetHCI(hci)
		nDump, uDump = testHcidump(hci, secs)
		result["nDump"], result["uDump"] = nDump, uDump
		if nDump >= 0:
			print("  HCIDUMP  : {:5d} reports = {:6.1f}/s   from {:3d} distinct macs".format(nDump, nDump / float(secs), uDump))
		else:
			print("  HCIDUMP  : failed to start hcitool lescan / hcidump")

	# leave the adapter in a clean state
	resetHCI(hci)
	return result


def testHcidump(hci, secs):
	"""classic pipeline: hcitool lescan --duplicates configures scanning the old way,
	hcidump --raw taps the HCI traffic; counts LE meta advertising-report events.
	The script itself runs under sudo, so the child processes need no inner sudo
	and proc.terminate() works directly."""
	lescan = None
	dump   = None
	n      = -1
	macs   = set()
	try:
		devnull = open(os.devnull, "wb")
		lescan  = subprocess.Popen(["hcitool", "-i", hci, "lescan", "--duplicates"], stdout=devnull, stderr=devnull)
		time.sleep(0.7)
		if lescan.poll() is not None:
			return -1, 0										# lescan died immediately
		dump = subprocess.Popen(["hcidump", "--raw", "-i", hci], stdout=subprocess.PIPE, stderr=devnull)
		n    = 0
		buf  = b""
		t0   = time.time()
		fd   = dump.stdout.fileno()
		while time.time() - t0 < secs:
			r, _, _ = select.select([fd], [], [], 0.5)
			if not r: continue
			chunk = os.read(fd, 65536)
			if not chunk: break
			buf += chunk
			while b"\n" in buf:
				line, buf = buf.split(b"\n", 1)
				# raw incoming HCI event lines start with "> 04 3E <len> <subevent> ..."
				toks = line.strip().split()
				if len(toks) >= 5 and toks[0] == b">" and toks[1] == b"04" and toks[2] == b"3E":
					sub = toks[4]
					if sub in (b"02", b"0D"):
						n += 1
						try:
							if sub == b"02":	macs.add(b"".join(toks[7:13]))		# legacy: num evtype addrtype mac(6)
							else:				macs.add(b"".join(toks[9:15]))		# extended report layout
						except Exception:
							pass
	except Exception as e:
		print("  HCIDUMP  : error {}".format(e))
	finally:
		for p in (dump, lescan):
			try:
				if p is not None: p.terminate()
			except Exception:	pass
		time.sleep(0.2)
	return n, len(macs)


def main():
	secs = 10
	args = sys.argv[1:]
	if args and args[0].isdigit():
		secs = int(args[0])
		args = args[1:]
	adapters = args if args else listAdapters()
	if not adapters:
		print("no HCI adapters found (hciconfig empty) - is bluetooth up?")
		return

	print("BLE scan delivery-rate benchmark v{}   {} s per phase, adapters: {}".format(VERSION, secs, ", ".join(adapters)))
	print("REMINDER: beaconloop must NOT be running (sudo pkill -f beaconloop.py; sudo pkill -f master.py)")

	results = []
	for hci in adapters:
		try:
			results.append(testAdapter(hci, secs))
		except Exception as e:
			print("  {} FAILED: {}".format(hci, e))

	print("")
	print("==== summary ================================================================")
	print("{:6} {:18} {:5} {:>10} {:>6} {:>10} {:>6} {:>10} {:>6}   verdict".format("hci", "mac", "BLE5", "legacy/s", "macs", "ext/s", "macs", "hcidump/s", "macs"))
	for r in results:
		leg = "{:.1f}".format(r["nLeg"]  / float(secs)) if r["nLeg"]  >= 0 else "n/a"
		ext = "{:.1f}".format(r["nExt"]  / float(secs)) if r["nExt"]  >= 0 else "n/a"
		dmp = "{:.1f}".format(r["nDump"] / float(secs)) if r.get("nDump", -1) >= 0 else "n/a"
		best = max(r["nLeg"], r["nExt"], r.get("nDump", -1))
		if   best < 0:										verdict = "BROKEN - no mode delivers"
		elif r["nExt"] >= 0 and r["nExt"] * 10 >= best * 7:	verdict = "extended OK"
		elif r["nLeg"] >= 0 and r["nLeg"] * 10 >= best * 7:	verdict = "use LEGACY socket mode"
		else:												verdict = "only hcidump performs - socket path loses packets!"
		print("{:6} {:18} {:5} {:>10} {:>6} {:>10} {:>6} {:>10} {:>6}   {}".format(
			r["hci"], r["mac"], "yes" if r["ble5"] else "no", leg, r["uLeg"], ext, r["uExt"], dmp, r.get("uDump", 0), verdict))
	print("=============================================================================")


if __name__ == "__main__":
	main()
