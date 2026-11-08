#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# encrypts / decrypts passwords that are stored in the indigo plugin prefs
# standard library only: HMAC-SHA256 as keystream (counter mode) + HMAC-SHA256 tag (encrypt then authenticate)
# the key is derived from the hardware UUID of this Mac, so a copy of the prefs is useless on another Mac
# (and a prefs file restored on a new Mac needs the passwords entered again)
# no indigo dependency

import base64, hashlib, hmac, os, subprocess

PREFIX = "enc1:"


####-------------------------------------------------------------------------####
def hardwareUUID():
	try:
		out = subprocess.run(["/usr/sbin/ioreg", "-rd1", "-c", "IOPlatformExpertDevice"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=20).stdout.decode("utf_8", "replace")
		for line in out.split("\n"):
			if line.find("IOPlatformUUID") > -1:
				return line.split("=", 1)[1].strip().strip('"')
	except Exception:
		pass
	return ""


####-------------------------------------------------------------------------####
class PwCrypt(object):

	def __init__(self, context="com.karlwachs.utilities"):
		self.context = context
		self.keyEnc  = None
		self.keyMac  = None

	####-----------------  the key is made on first use, it needs one ioreg call ---------
	def available(self):
		if self.keyEnc is not None: return True
		uuid = hardwareUUID()
		if uuid == "": return False
		master      = hashlib.pbkdf2_hmac("sha256", uuid.encode("utf_8"), (self.context + "|password|v1").encode("utf_8"), 100000, 32)
		self.keyEnc = hmac.new(master, b"encrypt", hashlib.sha256).digest()
		self.keyMac = hmac.new(master, b"authenticate", hashlib.sha256).digest()
		return True

	####-----------------  is this text something encrypt() made (it still can be a password that just looks like it) ---------
	def isToken(self, text):
		return isinstance(text, str) and text.startswith(PREFIX)

	def _stream(self, nonce, length):
		out = b""
		n   = 0
		while len(out) < length:
			out += hmac.new(self.keyEnc, nonce + n.to_bytes(4, "big"), hashlib.sha256).digest()
			n   += 1
		return out[:length]

	####-----------------  plain text -> "enc1:...", empty stays empty, None if no key is available ---------
	def encrypt(self, plain):
		if plain == "": return ""
		if not self.available(): return None
		data  = plain.encode("utf_8")
		nonce = os.urandom(16)
		body  = bytes(a ^ b for a, b in zip(data, self._stream(nonce, len(data))))
		tag   = hmac.new(self.keyMac, nonce + body, hashlib.sha256).digest()[:16]
		return PREFIX + base64.urlsafe_b64encode(nonce + body + tag).decode("ascii")

	####-----------------  "enc1:..." -> plain text, None if it is not a valid token for this Mac ---------
	def decrypt(self, token):
		if not self.isToken(token): return None
		if not self.available(): return None
		try:
			raw = base64.urlsafe_b64decode(token[len(PREFIX):].encode("ascii"))
			if len(raw) < 32: return None
			nonce, body, tag = raw[:16], raw[16:-16], raw[-16:]
			if not hmac.compare_digest(tag, hmac.new(self.keyMac, nonce + body, hashlib.sha256).digest()[:16]): return None
			return bytes(a ^ b for a, b in zip(body, self._stream(nonce, len(body)))).decode("utf_8")
		except Exception:
			return None
