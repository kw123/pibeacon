#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Minimal BLE GATT (ATT) client over an LE L2CAP socket - python stdlib only.

Replaces gatttool for BLEconnect's gatt jobs (phase 1: beacon-tag beep / battery /
time-set). No bluetoothd and no external libraries needed: connecting an L2CAP
socket on the ATT channel (CID 4) makes the KERNEL create the LE connection -
the same daemon-free architecture gatttool uses, which is being dropped from
newer BlueZ builds. Follows the hciRawSocket.py precedent:

	try:	import gattAttClient
	except:	attClientPresent = False		# -> keep using gatttool

Import raises ImportError on any platform without AF_BLUETOOTH socket support
(needs Linux and python >= 3.3).

ATT subset implemented (everything BLEconnect ever used through gatttool):
	Write Request (char-write-req)  /  Write Command (char-write-cmd)
	Read by handle (char-read-hnd)  /  Read By Type = read by 16-bit uuid
	(char-read-uuid, e.g. battery 2A19)  /  Handle Value Notifications.
Incoming MTU exchange requests and indications are answered automatically.
The default ATT_MTU of 23 is kept - the largest read used anywhere is 16 bytes.
"""

VERSION = 1.4	# 1.0 ATT engine; 1.1 classic presence + source-adapter bind; 1.2 pending-connection guards; 1.3 py>=3.5 floor; 1.4 connect error stage-tagged (connect()/SO_ERROR + numeric errno)

import socket as _socket
import struct, time, select, errno, fcntl
import ctypes, ctypes.util
import sys as _sys

if _sys.version_info < (3, 5):
	raise ImportError("python >= 3.5 required for the ATT/presence backend (this is python {}.{})".format(_sys.version_info[0], _sys.version_info[1]))
if not hasattr(_socket, "AF_BLUETOOTH"):
	raise ImportError("no AF_BLUETOOTH socket support (needs Linux with a bluetooth-enabled python build)")

SOL_HCI				= 0
HCI_FILTER			= 2
HCI_COMMAND_PKT		= 0x01
HCI_EVENT_PKT		= 0x04
HCIGETCONNINFO		= 0x800448D5	# _IOR('H', 213, int) from bluez hci.h

BTPROTO_L2CAP			= 0
ATT_CID					= 4
BDADDR_LE_PUBLIC		= 0x01
BDADDR_LE_RANDOM		= 0x02

# ATT protocol opcodes (Bluetooth Core spec Vol 3 Part F)
ATT_ERROR_RSP			= 0x01
ATT_MTU_REQ				= 0x02
ATT_MTU_RSP				= 0x03
ATT_READ_BY_TYPE_REQ	= 0x08
ATT_READ_BY_TYPE_RSP	= 0x09
ATT_READ_REQ			= 0x0A
ATT_READ_RSP			= 0x0B
ATT_WRITE_REQ			= 0x12
ATT_WRITE_RSP			= 0x13
ATT_WRITE_CMD			= 0x52
ATT_NOTIFY				= 0x1B
ATT_INDICATE			= 0x1D
ATT_CONFIRM				= 0x1E

_libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)


#################################
def _packMac(mac):
	"""bdaddr_t: 6 bytes, reversed byte order of the printed mac."""
	return bytes(bytearray(int(x, 16) for x in reversed(mac.split(":"))))


#################################
def _sockaddrL2(mac, bdaddrType, cid=ATT_CID, psm=0):
	"""struct sockaddr_l2 {u16 family; u16 psm; bdaddr_t; u16 cid; u8 bdaddr_type;}
	padded to 14 bytes (kernel copies min(sizeof, alen))."""
	return struct.pack("<HH6sHB", _socket.AF_BLUETOOTH, psm, _packMac(mac), cid, bdaddrType) + b"\x00"


#################################
def classicPresenceRSSI(peerMac, devId=0, connectTimeout=5., log=None, adapterMac=""):
	"""Classic (BR/EDR) presence check for phones/watches - stdlib only, no pybluez
	(gone on bookworm) and no hcitool (deprecated): an L2CAP connect to PSM 1 (SDP)
	pages the device, the ACL handle comes from the HCIGETCONNINFO ioctl, the RSSI
	from an HCI Read-RSSI command on a raw HCI socket bound to devId.
	Returns the 4 Command-Complete return bytes (status, handle lo, handle hi, rssi);
	None when the device is NOT REACHABLE (nobody answered the page = the NORMAL
	"away" answer, not an error); b"" when the page WAS answered but no reading came
	back (reset/refused/link dropped - phone present, e.g. iOS rate-limiting rapid
	pages; the caller should keep the previous state).
	Raises OSError only for adapter-level problems (no such hci device etc.).
	log: optional callable(str) - stage-by-stage diagnostics (which step fails/timings).
	adapterMac: OUR dongle's bdaddr - the page socket is bound to it; without the bind
	a multi-adapter rpi routes the page via the DEFAULT adapter and the ACL link is
	then invisible to devId's ioctl (page answered + "no ACL link" = this trap)."""
	def _log(msg):
		if log is not None:
			try:	log(msg)
			except Exception:	pass
	btSock = hciSock = None
	try:
		# adapter-level setup FIRST - failures here are real errors and raise
		hciSock = _socket.socket(_socket.AF_BLUETOOTH, _socket.SOCK_RAW, _socket.BTPROTO_HCI)
		hciSock.bind((devId,))
		btSock = _socket.socket(_socket.AF_BLUETOOTH, _socket.SOCK_SEQPACKET, _socket.BTPROTO_L2CAP)
		if adapterMac != "":
			try:	btSock.bind((adapterMac, 0))	# pin the page to OUR dongle (source bdaddr)
			except OSError as e:
				_log("bind to {} failed ({}) - paging via default adapter".format(adapterMac, e))
		btSock.settimeout(connectTimeout)
		t0 = time.time()
		pageAnswered = False
		try:
			btSock.connect((peerMac, 1))		# PSM 1 - Service Discovery; pages the phone
			pageAnswered = True
			_log("page/connect hci{}: answered after {:.1f}s".format(devId, time.time()-t0))
		except Exception as e:					# like the old connect_ex: HCIGETCONNINFO below decides
			# reset/refused = the phone ANSWERED the page and then dropped the channel
			# (e.g. iOS rate-limiting rapid pages) - that is presence, not absence
			pageAnswered = getattr(e, "errno", 0) in (errno.ECONNRESET, errno.ECONNREFUSED)
			_log("page/connect hci{}: {} after {:.1f}s (timeout={:.1f}s) - ACL check follows".format(devId, e, time.time()-t0, connectTimeout))
		req = bytearray(24)						# struct hci_conn_info_req + room for struct hci_conn_info
		req[0:6] = _packMac(peerMac)
		req[6]   = 0x01							# ACL_LINK
		try:
			fcntl.ioctl(hciSock.fileno(), HCIGETCONNINFO, req, True)
		except OSError as e:
			if pageAnswered:
				_log("HCIGETCONNINFO: no ACL link ({}) but the page WAS answered -> seen, no reading".format(e))
				return b""						# phone is there, link just dropped - caller keeps the previous state
			_log("HCIGETCONNINFO: no ACL link ({}) -> away".format(e))
			return None							# no ACL link = device not here - normal away case
		handle = struct.unpack_from("<H", bytes(req), 8)[0]
		if handle > 0x0EFF:						# HCI handles are 12 bit - a still-PENDING page (e.g. timed out
			_log("ACL handle 0x{:04x} invalid (connection still pending) -> {}".format(handle, "seen, no reading" if pageAnswered else "away"))
			return b"" if pageAnswered else None	# ...mid-setup) leaves garbage in the conn-info struct
		_log("ACL link up, handle:0x{:04x} - sending Read-RSSI".format(handle))
		flt = bytearray(16)						# all-events filter; sizeof(struct hci_ufilter)=16 (new kernels reject less)
		struct.pack_into("<L", flt, 0, 1 << HCI_EVENT_PKT)
		struct.pack_into("<LL", flt, 4, 0xFFFFFFFF, 0xFFFFFFFF)
		hciSock.setsockopt(SOL_HCI, HCI_FILTER, bytes(flt))
		hciSock.settimeout(3.)
		opcode = (0x05 << 10) | 0x0005			# OGF status parameters / OCF Read RSSI
		hciSock.send(struct.pack("<BHB", HCI_COMMAND_PKT, opcode, 2) + struct.pack("<H", handle))
		end     = time.time() + 3.
		nEvents = 0
		while time.time() < end:
			try:	pkt = hciSock.recv(255)
			except _socket.timeout:	break
			nEvents += 1
			if len(pkt) >= 10 and pkt[0] == HCI_EVENT_PKT and pkt[1] == 0x0E and (pkt[4] | (pkt[5] << 8)) == opcode:
				_log("Read-RSSI answer: {}".format("".join("{:02x}".format(bb) for bb in bytearray(pkt[6:10]))))
				if pkt[6] != 0:					# error status (e.g. 0x02 unknown handle): no usable reading
					return b"" if pageAnswered else None
				return pkt[6:10]				# status, handle lo, handle hi, rssi
		_log("Read-RSSI: NO answer within 3s ({} other events seen) -> seen, no reading".format(nEvents))
		return b""								# link existed, answer got lost - phone is there, caller keeps previous state
	finally:
		for ss in (btSock, hciSock):
			try:
				if ss is not None: ss.close()
			except Exception:
				pass


#################################
class GattSession(object):
	"""One connected beacon tag / BLE device. connect() -> True/False (lastError
	holds the errno text on False - feeds BLEconnect's adapter-wedge detection).
	All values are raw bytes; notifications collect in self.notifications."""

	def __init__(self, peerMac, randomAddr=False, adapterMac="", connectTimeout=12., mtu=23):
		self.peerMac		= peerMac.upper()
		self.peerType		= BDADDR_LE_RANDOM if randomAddr else BDADDR_LE_PUBLIC
		self.adapterMac		= adapterMac		# "" = kernel default adapter; else pins the dongle
		self.connectTimeout	= float(connectTimeout)
		self.mtu			= mtu
		self.sock			= None
		self.notifications	= []				# collected (handle, bytes) notifications/indications
		self.lastError		= ""

	def connect(self):
		s = None
		try:
			s = _socket.socket(_socket.AF_BLUETOOTH, _socket.SOCK_SEQPACKET, BTPROTO_L2CAP)
			if self.adapterMac != "":
				sa = _sockaddrL2(self.adapterMac, BDADDR_LE_PUBLIC)
				if _libc.bind(s.fileno(), sa, len(sa)) != 0:
					self.lastError = "bind {}: {}".format(self.adapterMac, errno.errorcode.get(ctypes.get_errno(), "?"))
					s.close()
					return False
			s.setblocking(False)
			sa  = _sockaddrL2(self.peerMac, self.peerType)
			ret = _libc.connect(s.fileno(), sa, len(sa))
			if ret != 0:
				err = ctypes.get_errno()
				if err not in (errno.EINPROGRESS, errno.EAGAIN):
					self.lastError = "connect():{}({})".format(errno.errorcode.get(err, "?"), err)
					s.close()
					return False
				rl, wl, xl = select.select([], [s], [], self.connectTimeout)
				if not wl:
					self.lastError = "connect timeout"
					s.close()
					return False
				err = s.getsockopt(_socket.SOL_SOCKET, _socket.SO_ERROR)
				if err != 0:
					# SO_ERROR after the kernel's own scan+create-connection: the controller
					# refused/failed the LE connection (ENOSYS/EIO here usually = adapter can't
					# create-connection right now: busy scanning, out of slots, or a weak/onboard
					# BT controller). Stage is tagged so the log distinguishes it from connect().
					self.lastError = "SO_ERROR:{}({})".format(errno.errorcode.get(err, "?"), err)
					s.close()
					return False
			s.setblocking(True)
			self.sock = s
			return True
		except Exception as e:
			self.lastError = "{}".format(e)
			try:
				if s is not None: s.close()
			except Exception:
				pass
			return False

	def _recvPDU(self, timeout):
		"""Next non-housekeeping PDU or None on timeout/disconnect. Notifications and
		indications are queued (indications confirmed), MTU requests answered."""
		end = time.time() + timeout
		while True:
			left = end - time.time()
			if left <= 0:
				return None
			rl, wl, xl = select.select([self.sock], [], [], left)
			if not rl:
				return None
			pdu = self.sock.recv(64)
			if not pdu:
				self.lastError = "disconnected"
				return None
			op = pdu[0]
			if op == ATT_MTU_REQ:
				try:	self.sock.send(struct.pack("<BH", ATT_MTU_RSP, self.mtu))
				except Exception:	pass
				continue
			if op == ATT_NOTIFY and len(pdu) >= 3:
				self.notifications.append((struct.unpack("<H", pdu[1:3])[0], pdu[3:]))
				continue
			if op == ATT_INDICATE and len(pdu) >= 3:
				self.notifications.append((struct.unpack("<H", pdu[1:3])[0], pdu[3:]))
				try:	self.sock.send(struct.pack("<B", ATT_CONFIRM))
				except Exception:	pass
				continue
			return pdu

	def _request(self, pdu, expectOp, timeout):
		"""Sends a request PDU and returns the matching response, or None (lastError set)."""
		try:
			self.sock.send(pdu)
		except Exception as e:
			self.lastError = "{}".format(e)
			return None
		end = time.time() + timeout
		while True:
			left = end - time.time()
			if left <= 0:
				self.lastError = "response timeout"
				return None
			rsp = self._recvPDU(left)
			if rsp is None:
				if self.lastError == "":	self.lastError = "response timeout"
				return None
			if rsp[0] == expectOp:
				return rsp
			if rsp[0] == ATT_ERROR_RSP and len(rsp) >= 5 and rsp[1] == pdu[0]:
				self.lastError = "ATT error 0x{:02x} on op 0x{:02x} handle 0x{:04x}".format(
									rsp[4], rsp[1], struct.unpack("<H", rsp[2:4])[0])
				return None
			# unrelated pdu (e.g. a late response) - keep waiting within the timeout

	def writeReq(self, handle, data, timeout=5.):
		"""Write Request (gatttool char-write-req): True once the tag confirmed."""
		rsp = self._request(struct.pack("<BH", ATT_WRITE_REQ, handle) + data, ATT_WRITE_RSP, timeout)
		return rsp is not None

	def writeCmd(self, handle, data):
		"""Write Command (gatttool char-write-cmd): no response defined."""
		try:
			self.sock.send(struct.pack("<BH", ATT_WRITE_CMD, handle) + data)
			return True
		except Exception as e:
			self.lastError = "{}".format(e)
			return False

	def readHnd(self, handle, timeout=5.):
		"""Read by handle (gatttool char-read-hnd): value bytes or None."""
		rsp = self._request(struct.pack("<BH", ATT_READ_REQ, handle), ATT_READ_RSP, timeout)
		if rsp is None:
			return None
		return rsp[1:]

	def readUUID(self, uuid16, timeout=5.):
		"""Read by 16-bit uuid (gatttool char-read-uuid, e.g. 0x2A19 battery):
		(handle, value bytes) of the first match or None."""
		req = struct.pack("<BHHH", ATT_READ_BY_TYPE_REQ, 0x0001, 0xFFFF, uuid16)
		rsp = self._request(req, ATT_READ_BY_TYPE_RSP, timeout)
		if rsp is None or len(rsp) < 4:
			return None
		entryLen = rsp[1]
		if entryLen < 2 or len(rsp) < 2 + entryLen:
			return None
		return struct.unpack("<H", rsp[2:4])[0], rsp[4:2 + entryLen]

	def waitNotify(self, handle=None, timeout=15.):
		"""Waits for a notification/indication (any handle, or a specific one):
		(handle, value bytes) or None on timeout."""
		end = time.time() + timeout
		while True:
			for ii in range(len(self.notifications)):
				hh, vv = self.notifications[ii]
				if handle is None or hh == handle:
					return self.notifications.pop(ii)
			left = end - time.time()
			if left <= 0:
				return None
			pdu = self._recvPDU(left)		# queues notifications; unrelated pdus are dropped here
			if pdu is None and self.lastError == "disconnected":
				return None

	def close(self):
		try:
			if self.sock is not None:	self.sock.close()
		except Exception:
			pass
		self.sock = None
