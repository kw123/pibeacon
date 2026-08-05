#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Very basic Ruuvi reader: listens on one BLE adapter and PRINTS every Ruuvi
advertisement it hears - Bluetooth 4 (legacy) AND Bluetooth 5 (extended) frames:

    data format 3  (RuuviTag RAWv1, old firmware)
    data format 5  (RuuviTag RAWv2:  temp, hum, pressure, acceleration, battery, ...)
    data format 6  (Ruuvi Air, compact legacy adv)
    data format E1 (Ruuvi Air, FULL data set via BT5 extended adv - needs an
                    extended-advertising capable adapter, e.g. the UGREEN 33fa:0012)
    anything else from a Ruuvi (encrypted df8, future formats) is printed as raw hex,
    so EVERY ruuvi in range shows up.

Run on any linux box with python 3.3+ (STANDALONE - stdlib only, no other files needed):
    sudo python3 ruuviPrint.py            # overview of ALL adapters, then use the best (BT5 first)
    sudo python3 ruuviPrint.py 2          # force hci2, no overview
Stop with ctrl-c. If another program already scans on that adapter the tool just
listens along (the kernel copies HCI events to every raw socket) - you then see
whatever THAT program's scan settings deliver: a passive or duplicate-filtered scan
yields fewer frames than this tool's own 100%-duty active scan. Standalone it enables
scanning itself (extended when the adapter supports it, else legacy).


KarlWachs July 26, 2026 

MIT lisence 
The software is provided "as is"


"""

import sys, time, struct, socket

OGF_LE     = 0x08
OGF_INFO   = 0x04
SOL_HCI    = 0
HCI_FILTER = 2


def hciOpen(devId):
	"""raw HCI socket bound to hci<devId>, filter = all events (16-byte struct hci_ufilter)"""
	sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW, socket.BTPROTO_HCI)
	sock.bind((devId,))
	#                       type_mask: bit4=HCI_EVENT_PKT   event_mask: all         opcode + pad
	flt = struct.pack("<LLLHH", 1 << 0x04, 0xFFFFFFFF, 0xFFFFFFFF, 0, 0)
	sock.setsockopt(SOL_HCI, HCI_FILTER, flt)
	return sock


def hciCmd(sock, ogf, ocf, params=b""):
	"""sends one HCI command packet (fire and forget)"""
	sock.send(struct.pack("<BHB", 0x01, (ogf << 10) | ocf, len(params)) + params)


def s16(b, i):	v = (b[i] << 8) | b[i+1];	return v - 65536 if v > 32767 else v
def u16(b, i):	return (b[i] << 8) | b[i+1]
def u24(b, i):	return (b[i] << 16) | (b[i+1] << 8) | b[i+2]


RAWCOLUMN = 186		# decoded text is padded to this width, then "raw:<hex>" follows


def markerOr(isInvalid, marker, txt):
	"""df fields that a tag does not have carry an all-ones marker (FFFF / FFFFFF).
	Show the marker itself instead of decoding it - 65535*0.0025 = 163.8% is not a reading.
	Padded to the width of txt so the columns stay aligned."""
	if isInvalid: return marker.rjust(len(txt))
	return txt


def decodeRuuvi(mac, rssi, mfg):
	"""mfg = manufacturer-data bytes AFTER the 0499 company id; prints one line"""
	tt = time.strftime("%H:%M:%S")
	if len(mfg) < 1: return
	df  = mfg[0]
	txt = ""
	if df == 0x03 and len(mfg) >= 14:				# RuuviTag RAWv1 (old firmware)
		temp = (mfg[2] & 0x7F) + mfg[3]/100.
		if mfg[2] & 0x80: temp = -temp
		hum3   = markerOr(mfg[1] == 0xFF,      "FF",   "{:5.1f}".format(mfg[1]*0.5))
		press3 = markerOr(u16(mfg,4) == 0xFFFF, "FFFF", "{:6d}".format(u16(mfg,4)+50000))
		txt = ("{} {} rssi:{:4d}  df3   temp:{:6.2f}C  hum:{}%  press:{}Pa  accXYZ:{:5d}/{:5d}/{:5d}mg  batt:{}mV".format(
			tt, mac, rssi, temp, hum3, press3,
			s16(mfg,6), s16(mfg,8), s16(mfg,10), u16(mfg,12)))
	elif df == 0x05 and len(mfg) >= 18:				# RuuviTag RAWv2
		battmV = 1600 + ((u16(mfg,13) >> 5) & 0x7FF)
		hum   = markerOr(u16(mfg,3) == 0xFFFF, "FFFF", "{:5.1f}".format(u16(mfg,3)*0.0025))
		press = markerOr(u16(mfg,5) == 0xFFFF, "FFFF", "{:6d}".format(u16(mfg,5)+50000))
		txt = ("{} {} rssi:{:4d}  df5   temp:{:6.2f}C  hum:{}%  press:{}Pa  accXYZ:{:5d}/{:5d}/{:5d}mg  batt:{}mV  moves:{}  seq:{}".format(
			tt, mac, rssi, s16(mfg,1)*0.005, hum, press,
			s16(mfg,7), s16(mfg,9), s16(mfg,11), battmV, mfg[15], u16(mfg,16)))
	elif df == 0x06 and len(mfg) >= 17:				# Ruuvi Air compact; VOC/NOx are 9 bit: (byte<<1)+flag bit
		flags = mfg[16]
		hum   = markerOr(u16(mfg,3) == 0xFFFF, "FFFF", "{:5.1f}".format(u16(mfg,3)*0.0025))
		press = markerOr(u16(mfg,5) == 0xFFFF, "FFFF", "{:6d}".format(u16(mfg,5)+50000))
		txt = ("{} {} rssi:{:4d}  df6   temp:{:6.2f}C  hum:{}%  press:{}Pa  PM2.5:{:5.1f}  CO2:{:4d}ppm  VOC:{:3d}  NOx:{:3d}  cnt:{}".format(
			tt, mac, rssi, s16(mfg,1)*0.005, hum, press,
			u16(mfg,7)*0.1, u16(mfg,9), (mfg[11]<<1)|((flags>>6)&1), (mfg[12]<<1)|((flags>>7)&1), mfg[15]))
	elif df == 0xE1 and len(mfg) >= 40:				# Ruuvi Air FULL (BT5 extended)
		flags = mfg[28]
		hum   = markerOr(u16(mfg,3)  == 0xFFFF,   "FFFF",   "{:5.1f}".format(u16(mfg,3)*0.0025))
		press = markerOr(u16(mfg,5)  == 0xFFFF,   "FFFF",   "{:6d}".format(u16(mfg,5)+50000))
		co2   = markerOr(u16(mfg,15) == 0xFFFF,   "FFFF",   "{:4d}".format(u16(mfg,15)))
		lumi  = markerOr(u24(mfg,19) == 0xFFFFFF, "FFFFFF", "{:6.0f}".format(u24(mfg,19)*0.01))
		pm    = "/".join(markerOr(u16(mfg,i) == 0xFFFF, "FFFF", "{:5.1f}".format(u16(mfg,i)*0.1)) for i in (7,9,11,13))
		voc9  = (mfg[17]<<1)|((flags>>6)&1)
		nox9  = (mfg[18]<<1)|((flags>>7)&1)
		txt = ("{} {} rssi:{:4d}  E1    temp:{:6.2f}C  hum:{}%  press:{}Pa  PM1/2.5/4/10:{}  CO2:{}ppm  VOC:{}  NOx:{}  lumi:{}lx  seq:{}".format(
			tt, mac, rssi, s16(mfg,1)*0.005, hum, press, pm, co2,
			markerOr(voc9 == 0x1FF, "1FF", "{:3d}".format(voc9)),
			markerOr(nox9 == 0x1FF, "1FF", "{:3d}".format(nox9)), lumi, u24(mfg,25)))
	else:											# unknown/encrypted format - still show it
		txt = "{} {} rssi:{:4d}  df:{:02X} <not decoded>".format(tt, mac, rssi, df)

	# every line ends with the RAW manufacturer payload in a fixed column, so the hex of
	# different formats lines up under each other. FFFF in a field = that sensor is not
	# present in this tag (eg a sealed Pro with an external probe: no humidity/pressure).
	print("{}  raw:{}".format(txt.ljust(RAWCOLUMN), "".join("{:02X}".format(c) for c in mfg)))


def ruuviFromAdvData(mac, rssi, data):
	"""walks the AD sections; ruuvi = manufacturer data (FF) with company id 0499"""
	pos = 0
	while pos + 1 < len(data):
		ll = data[pos]
		if ll == 0: break
		if data[pos+1] == 0xFF and ll >= 3 and data[pos+2] == 0x99 and data[pos+3] == 0x04:
			decodeRuuvi(mac, rssi, bytes(data[pos+4:pos+1+ll]))
		pos += 1 + ll


def checkBT5(sock):
	"""True when the adapter supports BT5 extended advertising (LE feature bit 12) -
	only then E1 frames are receivable; the label on the box means nothing."""
	try:
		sock.settimeout(0.8)
		hciCmd(sock, OGF_LE, 0x0003)						# LE Read Local Supported Features
		t0 = time.time()
		while time.time() - t0 < 1.5:
			ev = bytearray(sock.recv(512))
			if len(ev) >= 15 and ev[1] == 0x0E and (ev[4] | (ev[5] << 8)) == 0x2003 and ev[6] == 0:
				return bool(ev[8] & 0x10)					# feats byte1 bit4 = feature bit 12
	except Exception:	pass
	return False



def hciReply(sock, ogf, ocf, params=b"", timeout=1.0):
	"""send a command and return the command-complete RETURN PARAMETERS (after the status
	byte), or None. Used to read the adapter properties for the overview."""
	opcode = (ogf << 10) | ocf
	try:
		sock.settimeout(timeout)
		hciCmd(sock, ogf, ocf, params)
		t0 = time.time()
		while time.time() - t0 < timeout + 0.5:
			ev = bytearray(sock.recv(512))
			#      event pkt      cmd complete      matching opcode                    status ok
			if len(ev) >= 7 and ev[1] == 0x0E and (ev[4] | (ev[5] << 8)) == opcode and ev[6] == 0:
				return ev[7:]
	except Exception:
		pass
	return None


def hciProperties(sock):
	"""mac + the parameters that matter for a scan adapter:
	   aclMTU  - real radios report ~1017-1021, CSR8510 CLONES report 310 (they scan but
	             fail LE connects, so a low value here is the fake-dongle fingerprint)
	   btVer   - HCI version byte: 6=4.0, 7=4.1, 8=4.2, 9=5.0, 10=5.1, 11=5.2, 12=5.3, 13=5.4
	   manuf   - company id of the chip maker"""
	mac, aclMTU, btVer, manuf = "?", 0, 0, 0
	r = hciReply(sock, OGF_INFO, 0x0009)					# Read BD_ADDR
	if r is not None and len(r) >= 6:
		mac = ":".join("{:02X}".format(r[i]) for i in range(5, -1, -1))
	r = hciReply(sock, OGF_INFO, 0x0005)					# Read Buffer Size
	if r is not None and len(r) >= 2:
		aclMTU = r[0] | (r[1] << 8)
	r = hciReply(sock, OGF_INFO, 0x0001)					# Read Local Version Information
	if r is not None and len(r) >= 8:
		btVer = r[0]
		manuf = r[4] | (r[5] << 8)
	return mac, aclMTU, btVer, manuf


_BTVER = {6:"4.0", 7:"4.1", 8:"4.2", 9:"5.0", 10:"5.1", 11:"5.2", 12:"5.3", 13:"5.4",
          14:"6.0", 15:"6.1"}
_MANUF = {2:"Intel", 10:"CSR/Qualcomm", 13:"TI", 15:"Broadcom", 18:"Zeevo", 72:"MediaTek",
          93:"Realtek", 2279:"Barrot"}


def btVerText(v):
	"""HCI version byte -> marketing name; unknown/newer values are shown as the raw
	number (never "?") so a new chip is still identifiable. 0 = the read failed."""
	if v in _BTVER:	return _BTVER[v]
	if v == 0:		return "n/a"
	return "v{}".format(v)


def listHCIdevices(maxDev=10):
	"""hci numbers that can actually be opened, lowest first"""
	found = []
	for n in range(maxDev):
		try:
			so = hciOpen(n)
			so.close()
			found.append(n)
		except Exception:
			pass
	return found


def pickBestHCI():
	"""No hci number given -> probe EVERY adapter and take the best one for ruuvi:
	a BT5 (extended advertising) radio first, because only that one receives the Ruuvi Air
	E1 frames; otherwise the first adapter that opens at all. Returns (devId, isBT5) or
	(None, False) when there is no usable adapter."""
	devs = listHCIdevices()
	if not devs:
		return None, False
	print("no hci number given - probing {} adapter(s)\n".format(len(devs)))
	print("   hci  mac                aclMTU  BT    chip           ruuvi formats")
	print("   ---  -----------------  ------  ----  -------------  ---------------------------")
	best, firstOK = None, None
	for n in devs:
		try:
			so = hciOpen(n)
		except Exception as e:
			print("   {:<3}  cannot open: {}".format(n, e))
			continue
		mac, aclMTU, btVer, manuf = hciProperties(so)
		bt5 = checkBT5(so)
		so.close()
		clone = "  <- CLONE? (real radios ~1021)" if 0 < aclMTU <= 400 else ""
		print("   {:<3}  {:17}  {:>6}  {:<4}  {:<13}  {}{}".format(
			n, mac, aclMTU or "?", btVerText(btVer), _MANUF.get(manuf, "id {}".format(manuf)),
			"df3/df5/df6 + E1" if bt5 else "df3/df5/df6 only", clone))
		if bt5 and best is None:	best = n
		if firstOK is None:			firstOK = n
	print("")
	if best is not None:	return best, True
	return firstOK, False


def main():
	if len(sys.argv) > 1:
		devId = int(sys.argv[1])
		sock  = hciOpen(devId)
		isBT5 = checkBT5(sock)
	else:
		devId, isBT5 = pickBestHCI()
		if devId is None:
			print("no usable bluetooth adapter found - is bluetooth enabled? (try: sudo hciconfig hci0 up)")
			return
		print("--> using hci{}{}".format(devId, " (best: BT5 capable)" if isBT5 else " (no BT5 adapter present)"))
		sock = hciOpen(devId)
	sock.settimeout(2.0)

	# best effort scan enable - statuses are not checked: if another program already scans
	# on this adapter these commands are rejected/ignored and we simply listen to its stream
	if isBT5:
		print("hci{}: adapter supports BT5 extended advertising -> E1 receivable".format(devId))
		try:	hciCmd(sock, OGF_LE, 0x0001, struct.pack("<Q", 0x000FFFFF))	# event mask incl. bit12 ext reports
		except Exception:	pass
		try:
			hciCmd(sock, OGF_LE, 0x0041, struct.pack("<BBBBHH", 0, 0, 0x01, 0x01, 0x0010, 0x0010))
			hciCmd(sock, OGF_LE, 0x0042, struct.pack("<BBHH", 0x01, 0x00, 0, 0))
		except Exception:	pass
	else:
		print("hci{}: adapter has NO BT5 extended advertising -> only legacy frames (df5/df6); E1 needs a capable dongle (e.g. UGREEN 33fa:0012)".format(devId))
		try:
			hciCmd(sock, OGF_LE, 0x000B, struct.pack("<BHHBB", 0x01, 0x0010, 0x0010, 0x00, 0x00))
			hciCmd(sock, OGF_LE, 0x000C, struct.pack("<BB", 0x01, 0x00))
		except Exception:	pass

	print("listening on hci{} for ruuvi df5 / df6{} - ctrl-c to stop".format(devId, " / E1" if isBT5 else ""))
	while True:
		try:	ev = bytearray(sock.recv(512))
		except KeyboardInterrupt:	break
		except Exception:			continue
		if len(ev) < 5 or ev[0] != 0x04 or ev[1] != 0x3E:	continue
		if ev[3] == 0x0D:								# BT5 extended advertising report(s)
			pos = 5
			for ii in range(ev[4]):
				if pos + 24 > len(ev): break
				mac     = ":".join("{:02X}".format(c) for c in reversed(ev[pos+3:pos+9]))
				rssi    = ev[pos+13] - 256 if ev[pos+13] > 127 else ev[pos+13]
				dataLen = ev[pos+23]
				ruuviFromAdvData(mac, rssi, ev[pos+24:pos+24+dataLen])
				pos += 24 + dataLen
		elif ev[3] == 0x02:								# BT4 legacy advertising report(s)
			pos = 4
			for ii in range(ev[4] if len(ev) > 4 else 0):
				if pos + 9 > len(ev): break
				mac     = ":".join("{:02X}".format(c) for c in reversed(ev[pos+2:pos+8]))
				dataLen = ev[pos+8]
				rssiPos = pos + 9 + dataLen
				rssi    = (ev[rssiPos] - 256 if ev[rssiPos] > 127 else ev[rssiPos]) if rssiPos < len(ev) else 0
				ruuviFromAdvData(mac, rssi, ev[pos+9:pos+9+dataLen])
				pos += 10 + dataLen


if __name__ == "__main__":
	main()
