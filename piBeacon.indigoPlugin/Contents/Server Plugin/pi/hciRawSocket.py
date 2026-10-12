#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""stdlib replacement for the small subset of pybluez (bluetooth._bluetooth) that
beaconloop.py uses for the "socket" data acquisition method.

Needs python 3.3+ on Linux (AF_BLUETOOTH raw HCI socket support in the socket module).
Import raises ImportError on any other platform/python, so the caller can fall back:
	try:	import bluetooth._bluetooth as bluez        # pybluez (works on py2)
	except:
		try:	import hciRawSocket as bluez            # this module (py3, no extra libs)
		except:	bluezPresent = False                    # -> hcidump method

API provided (pybluez compatible):
	hci_open_dev(dev_id)                  -> bound raw HCI socket
	hci_send_cmd(sock, ogf, ocf, params)  -> send an HCI command packet
	hci_filter_new / hci_filter_all_events / hci_filter_set_ptype
	SOL_HCI, HCI_FILTER, HCI_EVENT_PKT

Also, beyond pybluez's API, the three adapter controls hciconfig provides:
	hci_dev_up / hci_dev_down / hci_dev_reset   (ioctl, no /bin/hciconfig needed)
	hci_connections                             (the list behind "hcitool con")
"""
import socket as _socket
import struct
import sys as _sys
import fcntl as _fcntl
import errno as _errno

if _sys.version_info < (3, 5):
	raise ImportError("python >= 3.5 required for the socket backend (this is python {}.{})".format(_sys.version_info[0], _sys.version_info[1]))
if not hasattr(_socket, "AF_BLUETOOTH"):
	raise ImportError("no AF_BLUETOOTH raw socket support (needs Linux with a bluetooth-enabled python build)")

VERSION = 1.1	# 1.0 pybluez subset for the socket scan method (hci_open_dev / hci_send_cmd / filters)
				# 1.1 adapter ioctls: hci_dev_up / hci_dev_down / hci_dev_reset / hci_connections
# A VERSION because this file now carries code OTHER programs depend on, and a partial file send to
# an rpi has left a stale copy three times already. Consumers that need the 1.1 ioctls check it and
# say so in the log, the way BLEconnect checks ATTCLIENT_MINVERSION for gattAttClient.

# constants from BlueZ hci.h (stable kernel ABI)
SOL_HCI			= getattr(_socket, "SOL_HCI", 0)
HCI_FILTER		= getattr(_socket, "HCI_FILTER", 2)
HCI_COMMAND_PKT	= 0x01
HCI_EVENT_PKT	= 0x04

# adapter up/down/reset ioctls, the three hciconfig does. _IOW('H', nr, int):
#   (1 << 30) | (sizeof(int) << 16) | (ord('H') << 8) | nr
# Derived rather than copied from a header, and spelled out so the numbers can be checked.
HCIDEVUP		= 0x400448c9	# _IOW('H', 201, int)
HCIDEVDOWN		= 0x400448ca	# _IOW('H', 202, int)
HCIDEVRESET		= 0x400448cb	# _IOW('H', 203, int)
HCIGETCONNLIST	= 0x800448d4	# _IOR('H', 212, int) - the list behind "hcitool con"


def hci_open_dev(dev_id=0):
	"""Opens a raw HCI socket bound to the given adapter number (0 = hci0).

	Inputs:
	    dev_id (int): HCI adapter index
	Outputs:
	    socket.socket: bound raw Bluetooth HCI socket
	"""
	sock = _socket.socket(_socket.AF_BLUETOOTH, _socket.SOCK_RAW, _socket.BTPROTO_HCI)
	sock.bind((dev_id,))
	return sock


def hci_send_cmd(sock, ogf, ocf, params=b""):
	"""Sends an HCI command packet: [0x01][opcode LE 16][len][params].
	opcode = (ogf << 10) | ocf, same wire format pybluez produces.

	Inputs:
	    sock (socket.socket): open raw HCI socket
	    ogf (int): opcode group field (e.g. 0x08 = LE controller commands)
	    ocf (int): opcode command field (e.g. 0x000C = LE set scan enable)
	    params (bytes): command parameter bytes
	Outputs:
	    int: number of bytes sent
	"""
	if isinstance(params, str):
		params = params.encode("latin-1")
	opcode = (ogf << 10) | ocf
	pkt = struct.pack("<BHB", HCI_COMMAND_PKT, opcode, len(params)) + params
	return sock.send(pkt)


def hci_filter_new():
	"""Returns a zeroed 16-byte HCI socket filter (struct hci_ufilter: u32 type_mask,
	u32 event_mask[2], u16 opcode = 14 data bytes + 2 alignment-padding bytes).
	Kernels with the 2024 setsockopt-validation fix (>= 6.1.91 / 6.6.30, e.g. updated
	bookworm) reject the classic 14-byte buffer with EINVAL because sizeof(struct
	hci_ufilter) is 16; old kernels accept 16 bytes identically."""
	return bytearray(16)


def hci_filter_set_ptype(flt, ptype):
	"""Enables the given HCI packet type (e.g. HCI_EVENT_PKT) in the filter's type mask."""
	bit = 0 if ptype == 0xFF else (ptype & 31)
	tm = struct.unpack_from("<L", flt, 0)[0] | (1 << bit)
	struct.pack_into("<L", flt, 0, tm)


def hci_filter_all_events(flt):
	"""Enables all HCI events in the filter's event mask."""
	struct.pack_into("<LL", flt, 4, 0xFFFFFFFF, 0xFFFFFFFF)


def hciDevId(hci):
	"""Turns "hci0" (or 0, or "0") into the integer adapter index the ioctls take.

	Inputs:
	    hci (str or int): adapter name or index
	Outputs:
	    int: the adapter index, or -1 when it cannot be read
	"""
	try:
		if isinstance(hci, int):	return hci
		return int("{}".format(hci).strip().lower().replace("hci", ""))
	except Exception:
		return -1


def _devCtl(hci, request):
	"""ioctl on an UNBOUND raw HCI socket - bind() wants a live adapter, these three calls do not,
	which is the whole point of HCIDEVUP.

	Inputs:
	    hci (str or int): adapter name or index
	    request (int): HCIDEVUP / HCIDEVDOWN / HCIDEVRESET
	Outputs:
	    int: 0 on success, otherwise the errno (or -1 when there is none)
	"""
	devId = hciDevId(hci)
	if devId < 0: return _errno.ENODEV
	sock = None
	try:
		sock = _socket.socket(_socket.AF_BLUETOOTH, _socket.SOCK_RAW, _socket.BTPROTO_HCI)
		_fcntl.ioctl(sock.fileno(), request, devId)
		return 0
	except OSError as e:					# py3: IOError is OSError
		return e.errno if e.errno else -1
	except Exception:
		return -1
	finally:
		if sock is not None:
			try:	sock.close()
			except Exception:	pass


def hci_dev_up(hci):
	"""Brings an adapter up - the ioctl behind "hciconfig hciX up".

	EALREADY counts as success: the caller wants the adapter UP, and it already is. That is also
	what hciconfig does with it.

	Inputs:
	    hci (str or int): adapter name or index
	Outputs:
	    tuple: (ok bool, errno int) - errno 0 on success
	"""
	err = _devCtl(hci, HCIDEVUP)
	return (err in [0, _errno.EALREADY]), err


def hci_dev_down(hci):
	"""Takes an adapter down - the ioctl behind "hciconfig hciX down".

	Inputs:
	    hci (str or int): adapter name or index
	Outputs:
	    tuple: (ok bool, errno int) - errno 0 on success
	"""
	err = _devCtl(hci, HCIDEVDOWN)
	return (err == 0), err


def hci_dev_reset(hci):
	"""Resets an adapter - the ioctl behind "hciconfig hciX reset".

	A reset needs the adapter UP; on a down one the kernel answers ENETDOWN. hciconfig hides that,
	so the errno is handed back rather than swallowed and the caller can bring it up first.

	Inputs:
	    hci (str or int): adapter name or index
	Outputs:
	    tuple: (ok bool, errno int) - errno 0 on success
	"""
	err = _devCtl(hci, HCIDEVRESET)
	return (err == 0), err


def hci_connections(hci, maxConn=16):
	"""Returns the adapter's current links - what "hcitool con" prints, without the process.

	struct hci_conn_list_req { __u16 dev_id; __u16 conn_num; struct hci_conn_info conn_info[0]; }
	struct hci_conn_info     { __u16 handle; bdaddr_t bdaddr[6]; __u8 type; __u8 out; __u16 state;
	                           __u32 link_mode; }  = 16 bytes, checked with struct.calcsize.
	conn_num is set to the capacity going in and comes back as the count actually written.

	Inputs:
	    hci (str or int): adapter name or index
	    maxConn (int): how many entries to make room for
	Outputs:
	    list: [{"handle","mac","type","out","state"}, ...]; empty when there are none or on error
	"""
	devId = hciDevId(hci)
	if devId < 0: return []
	sock = None
	try:
		sock = _socket.socket(_socket.AF_BLUETOOTH, _socket.SOCK_RAW, _socket.BTPROTO_HCI)
		buf  = bytearray(struct.pack("<HH", devId, maxConn) + bytes(16 * maxConn))
		_fcntl.ioctl(sock.fileno(), HCIGETCONNLIST, buf, True)
		nConn = struct.unpack_from("<H", buf, 2)[0]
		out   = []
		for ii in range(min(nConn, maxConn)):
			handle, mac, cType, cOut, state, _mode = struct.unpack_from("<H6sBBHI", buf, 4 + ii*16)
			out.append({"handle": handle,
						"mac":    ":".join("{:02X}".format(bb) for bb in bytearray(mac)[::-1]),
						"type":   "ACL" if cType == 1 else ("LE" if cType == 128 else "{}".format(cType)),
						"out":    bool(cOut),
						"state":  state})
		return out
	except Exception:
		return []
	finally:
		if sock is not None:
			try:	sock.close()
			except Exception:	pass
