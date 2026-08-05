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
"""
import socket as _socket
import struct
import sys as _sys

if _sys.version_info < (3, 5):
	raise ImportError("python >= 3.5 required for the socket backend (this is python {}.{})".format(_sys.version_info[0], _sys.version_info[1]))
if not hasattr(_socket, "AF_BLUETOOTH"):
	raise ImportError("no AF_BLUETOOTH raw socket support (needs Linux with a bluetooth-enabled python build)")

# constants from BlueZ hci.h (stable kernel ABI)
SOL_HCI			= getattr(_socket, "SOL_HCI", 0)
HCI_FILTER		= getattr(_socket, "HCI_FILTER", 2)
HCI_COMMAND_PKT	= 0x01
HCI_EVENT_PKT	= 0x04


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
