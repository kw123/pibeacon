#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Standalone BT5 extended-advertising test - the same checks beaconloop's
probeExtendedScan runs, but with a verbose report. Run on the rpi:

    sudo python3 extScanTest.py          # test ALL adapters (each gets a fresh reset first)
    sudo python3 extScanTest.py 0        # test only hci0
    sudo python3 extScanTest.py all 10   # 2nd number = listen seconds (default 5)

Per adapter: hciconfig reset -> LE feature bit 12 -> LE event mask -> extended scan
params/enable (all statuses shown) -> counts extended reports for N seconds, lists the
loudest macs, flags Ruuvi E1 frames (mfg data 9904E1). A summary of all verdicts is
printed at the end. Each tested adapter is left with scanning DISABLED - beaconloop's
watchdog re-enables its own scan within ~15s if its live adapter was tested.
NOTE: sends only LE scan/read commands after the reset - it does NOT touch advertising,
so it cannot lock an adapter's legacy/extended command-set choice."""

import sys, os, time, struct, subprocess
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import hciRawSocket as hrs

OGF_LE = 0x08


def cmdComplete(sock, ocf, params=b""):
	"""sends one LE command, returns (status, event bytearray); status -1 on timeout"""
	hrs.hci_send_cmd(sock, OGF_LE, ocf, params)
	opcode = (OGF_LE << 10) | ocf
	t0 = time.time()
	while time.time() - t0 < 1.5:
		try:	ev = bytearray(sock.recv(512))
		except Exception:	break
		if len(ev) >= 7 and ev[1] == 0x0E and (ev[4] | (ev[5] << 8)) == opcode:
			return ev[6], ev
	return -1, bytearray()


def listAdapters():
	"""[(devId, mac, bus), ...] from hciconfig output"""
	out = []
	try:
		ret = subprocess.Popen("hciconfig", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0].decode("utf-8")
		lines = ret.split("\n")
		for ii, ll in enumerate(lines):
			if ll.startswith("hci"):
				devId = int(ll.split(":")[0][3:])
				bus   = ll.split("Bus: ")[1].strip() if "Bus: " in ll else "?"
				mac   = "?"
				if ii+1 < len(lines) and "BD Address: " in lines[ii+1]:
					mac = lines[ii+1].split("BD Address: ")[1].split(" ")[0]
				out.append((devId, mac, bus))
	except Exception as e:
		print("could not enumerate adapters: {}".format(e))
	return sorted(out)


def testOne(devId, listen):
	"""resets + tests one adapter; returns a one-line verdict string"""
	print("\n=== hci{}: reset + extended-advertising test (listen {:.0f}s) ===".format(devId, listen))
	subprocess.call("hciconfig hci{} reset".format(devId), shell=True)
	time.sleep(1.0)
	subprocess.call("hciconfig hci{} up".format(devId), shell=True)
	time.sleep(0.3)

	try:
		sock = hrs.hci_open_dev(devId)
	except Exception as e:
		print("FAIL: cannot open hci{}: {}".format(devId, e));		return "cannot open ({})".format(e)
	flt  = hrs.hci_filter_new()
	hrs.hci_filter_all_events(flt)
	hrs.hci_filter_set_ptype(flt, hrs.HCI_EVENT_PKT)
	bb = bytes(flt);	bb += b"\x00" * max(0, 16 - len(bb))
	sock.setsockopt(hrs.SOL_HCI, hrs.HCI_FILTER, bb)
	sock.settimeout(0.8)

	st, ev = cmdComplete(sock, 0x0003)						# LE Read Local Supported Features
	if st != 0 or len(ev) < 15:
		print("FAIL: LE Read Local Supported Features status:{}".format(st))
		sock.close();	return "features read failed"
	feats = ev[7:15]
	extBit = bool(ev[8] & 0x10)
	print("LE features: {}  -> extended advertising feature bit 12: {}".format(" ".join("{:02X}".format(c) for c in feats), "YES" if extBit else "NO"))
	if not extBit:
		print("VERDICT: no extended-advertising support - legacy only")
		sock.close();	return "no BLE5 (feature bit off) - legacy only"

	cmdComplete(sock, 0x0042, struct.pack("<BBHH", 0x00, 0x00, 0, 0))				# clear stuck scan state
	stM, _ = cmdComplete(sock, 0x0001, struct.pack("<Q", 0x000FFFFF))				# LE event mask incl. bit12
	stP, _ = cmdComplete(sock, 0x0041, struct.pack("<BBBBHH", 0, 0, 0x01, 0x01, 0x0010, 0x0010))	# ext params: 1M active 100%
	stE, _ = cmdComplete(sock, 0x0042, struct.pack("<BBHH", 0x01, 0x00, 0, 0))		# ext enable
	print("statuses: eventMask:0x{:02X}  setParams:0x{:02X}  enable:0x{:02X}   (0x00=ok, 0x0C=Command Disallowed)".format(stM & 0xFF, stP & 0xFF, stE & 0xFF))
	if stP != 0 or stE != 0:
		print("VERDICT: controller rejects the extended scan commands")
		sock.close();	return "claims BLE5, REJECTS scan commands (0x{:02X}/0x{:02X})".format(stP & 0xFF, stE & 0xFF)

	nExt = 0; nLeg = 0; macs = {}; e1macs = {}
	t0 = time.time()
	while time.time() - t0 < listen:
		try:	ev = bytearray(sock.recv(512))
		except Exception:	continue
		if len(ev) < 5 or ev[1] != 0x3E:	continue
		if ev[3] == 0x0D:									# extended report(s)
			pos = 5
			for ii in range(ev[4]):
				if pos + 24 > len(ev): break
				mac = ":".join("{:02X}".format(c) for c in reversed(ev[pos+3:pos+9]))
				dataLen = ev[pos+23]
				data = ev[pos+24:pos+24+dataLen]
				pos += 24 + dataLen
				nExt += 1
				macs[mac] = macs.get(mac, 0) + 1
				hexd = "".join("{:02X}".format(c) for c in data)
				if hexd.find("9904E1") > -1:
					e1macs[mac] = e1macs.get(mac, 0) + 1
		elif ev[3] == 0x02:
			nLeg += 1										# legacy report (should not happen in ext mode)
	cmdComplete(sock, 0x0042, struct.pack("<BBHH", 0x00, 0x00, 0, 0))				# scan off again
	sock.close()

	print("reports in {:.0f}s: {} extended, {} legacy, from {} devices".format(listen, nExt, nLeg, len(macs)))
	for mac in sorted(macs, key=lambda m: -macs[m])[:10]:
		print("   {}  x{}{}".format(mac, macs[mac], "   <== Ruuvi E1 (x{})".format(e1macs[mac]) if mac in e1macs else ""))
	if e1macs:
		print("VERDICT: extended advertising WORKS, Ruuvi E1 received from: {}".format(", ".join(e1macs)))
		return "BLE5 WORKS ({} reports, E1 from {})".format(nExt, ", ".join(e1macs))
	elif nExt:
		print("VERDICT: extended advertising WORKS ({} reports; no E1 frames heard - Ruuvi Air out of range?)".format(nExt))
		return "BLE5 WORKS ({} reports, no E1 in range)".format(nExt)
	print("VERDICT: commands accepted but NO reports delivered - broken implementation")
	return "claims BLE5, delivers NOTHING - broken"


def main():
	arg1   = sys.argv[1] if len(sys.argv) > 1 else "all"
	listen = float(sys.argv[2]) if len(sys.argv) > 2 else 5.
	adapters = listAdapters()
	if not adapters:
		print("no BLE adapters found");	return
	if arg1 != "all":
		adapters = [a for a in adapters if a[0] == int(arg1)]
		if not adapters:
			print("hci{} not found".format(arg1));	return

	results = []
	for devId, mac, bus in adapters:
		results.append((devId, mac, bus, testOne(devId, listen)))

	print("\n" + "=" * 70)
	print("SUMMARY:")
	for devId, mac, bus, verdict in results:
		print("   hci{}  {}  {:<5} -> {}".format(devId, mac, bus, verdict))
	print("=" * 70)
	print("note: tested adapters are left with scanning OFF - beaconloop's watchdog")
	print("      re-enables its own scan within ~15s; beeps/connects recover on next use")


if __name__ == "__main__":
	main()
