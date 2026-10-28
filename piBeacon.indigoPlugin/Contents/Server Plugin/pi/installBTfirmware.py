#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# installBTfirmware.py - put the bluetooth PATCH RAM firmware we ship into /lib/firmware/brcm/
#
# WHY: a BCM20702 without its patch runs on ROM firmware and falls off the usb bus whenever it is
# reset. Measured on rpi-2: ~1 re-enumeration per qualifyDongle run, the radio coming back under a
# NEW hci number each time, and in between the exact symptoms of dead hardware - every scan command
# accepted with status 0 and not one report delivered, "adapter does not come up properly -
# unusable", and roles landing on the wrong radio because the numbering had moved underneath them.
# With the patch installed: 10 down/up cycles, same hci number, UP RUNNING every time, 0
# re-enumerations.
#
# WHAT IT DOES - and deliberately does NOT do:
#   - installs ONLY files shipped in pibeacon/firmware/. It never downloads anything.
#   - acts only when the kernel actually asked for that file and did not find it, so a pi whose
#     firmware is already in place (the normal case after the first run) does nothing at all.
#   - re-probes just the one usb device the file belongs to, identified by the vid-pid in its name.
#
# usage:
#    sudo python3 installBTfirmware.py           install what is missing, re-probe, report
#    sudo python3 installBTfirmware.py check     report only, change nothing
#
# Called from master.py at startup. Safe to run at any time: it is idempotent.

from __future__ import print_function
VERSION = "1.1"			# printed at startup by U.setLogging() -> U.versionLine()
import os
import re
import sys
import glob
import time
import shutil
import hashlib
import subprocess

FWSRC = "/home/pi/pibeacon/firmware/"		# one sub directory per chip family, e.g. firmware/BCM20702A1/
FWDST = "/lib/firmware/brcm/"


def shell(cmd):
	try:
		out = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()[0]
		if not isinstance(out, str):	out = out.decode("utf-8", "replace")
		return out
	except Exception:
		return ""


def sha256(path):
	try:
		h = hashlib.sha256()
		f = open(path, "rb")
		while True:
			b = f.read(65536)
			if not b:	break
			h.update(b)
		f.close()
		return h.hexdigest()
	except Exception:
		return ""


# NOTE on how "does this pi need it?" is decided.
# NOT from dmesg. The obvious test - look for "Patch file not found" - is wrong, because dmesg keeps
# the whole boot: once the patch has been installed and the device re-probed, the OLD "not found"
# block is still sitting there above the new successful one, so a dmesg-driven script would re-probe
# a perfectly patched radio on every single master start, taking the scan radio down each time for
# nothing. The decision here is made from facts that have no history: is that usb id plugged in, and
# is our file already in /lib/firmware/brcm/ byte for byte. dmesg is used afterwards, to CONFIRM.


def usbPortOf(vid, pid):
	"""the usb port name (e.g. "1-1.2") of the device with this vid:pid, "" if it is not plugged in"""
	for d in sorted(glob.glob("/sys/bus/usb/devices/*")):
		try:
			v = open(os.path.join(d, "idVendor")).read().strip().lower()
			p = open(os.path.join(d, "idProduct")).read().strip().lower()
		except Exception:
			continue
		if v == vid and p == pid:	return os.path.basename(d)
	return ""


def patchIsLoaded(fn):
	"""is this patch actually in the controller right now, judged by the LAST probe in dmesg?

	Compares the position of the last successful load against the last failure: a patch that was
	installed but never re-probed shows "Patch file not found" AFTER the last success (or no success
	at all). Needed so the installer can SELF-HEAL - without it, a pi where the file is in place but
	the load did not take reports "already installed - nothing to do" for ever and stays unpatched.
	"""
	txt  = shell("dmesg 2>/dev/null")
	iOk  = txt.rfind("'brcm/{}' Patch".format(fn))
	iBad = txt.rfind("Patch file not found")
	if iOk < 0:	return False
	return iOk > iBad


def confirmPatch(fn, maxWait=30.):
	"""WAIT for the kernel to confirm the patch loaded, and read the build number from AFTER it.

	The probe prints three lines, SECONDS apart:
	    BCM20702A1 (001.002.014) build 0000      <- ROM, before the patch
	    BCM20702A1 'brcm/<fn>' Patch             <- the patch is being sent
	    BCM20702A1 (001.002.014) build 1764      <- after it, the number CHANGES
	Looking once, right after the bind, and taking the last "build NNNN" in the window reports the
	ROM build as if it were the result. In the fleet rollout that produced "PATCH LOADED, firmware
	build now 0000" on two rpis - 0000 being precisely the unpatched state - and "has not confirmed
	the patch yet" on two more that were simply slower than the fixed wait. So: find the Patch line,
	read only what comes AFTER it, and keep looking until it appears.

	Outputs:
	    tuple: (patchLineSeen (bool), build (str, "" if the kernel has not printed one yet))
	"""
	t0 = time.time()
	while True:
		tail = shell("dmesg 2>/dev/null | tail -120")
		idx  = tail.rfind("'brcm/{}' Patch".format(fn))
		if idx >= 0:
			after = re.findall(r"build (\d+)", tail[idx:])
			if after:	return True, after[-1]
		if time.time() - t0 > maxWait:
			return (idx >= 0), ""
		time.sleep(1.0)


def reprobe(port):
	"""unbind + bind the usb device so btusb probes it again and loads the firmware we just put in.

	A down/up on the hci interface is NOT enough - the patch is loaded by the driver at PROBE time,
	so the device has to go through the driver core again."""
	try:
		f = open("/sys/bus/usb/drivers/usb/unbind", "w")
		f.write(port)
		f.close()
	except Exception as e:
		print("   could not unbind {}: {}".format(port, e))
		return False
	time.sleep(2.0)
	try:
		f = open("/sys/bus/usb/drivers/usb/bind", "w")
		f.write(port)
		f.close()
	except Exception as e:
		print("   could not bind {} again: {} - the dongle is now DETACHED, replug it".format(port, e))
		return False
	time.sleep(6.0)					# the probe + patch load takes a couple of seconds
	return True


def main():
	checkOnly = "check" in [a.strip().lower() for a in sys.argv[1:]]

	if not os.path.isdir(FWSRC):
		print("installBTfirmware {}: nothing shipped in {} - nothing to do".format(VERSION, FWSRC))
		return
	# one sub directory per chip family (firmware/BCM20702A1/...), so walk instead of globbing one
	# level - the chip name is only a label for us, what identifies the dongle is the vid-pid in
	# the FILE name, which has to keep the kernel's own spelling.
	shipped = {}
	for _root, _dirs, _files in os.walk(FWSRC):
		for _f in _files:
			if _f.endswith(".hcd"):	shipped[_f] = os.path.join(_root, _f)
	if not shipped:
		print("installBTfirmware {}: no .hcd in {} - nothing to do".format(VERSION, FWSRC))
		return

	# Lines worth telling INDIGO about. Only real events go in here - an install, a load, a failure.
	# The quiet "already installed" case must NOT report: this runs at every master start, and a
	# level-30 line in the indigo log on every boot of every rpi is noise that trains you to ignore
	# the one time it matters.
	report = []

	did = 0
	for fn in sorted(shipped):
		src = shipped[fn]
		dst = FWDST + fn
		# the vid-pid in the kernel's own file name says which dongle this patch is for
		m = re.search(r"-([0-9a-fA-F]{4})-([0-9a-fA-F]{4})\.hcd$", fn)
		if not m:
			print("installBTfirmware {}: {} has no usb id in its name - skipped".format(VERSION, fn))
			continue
		vid, pid = m.group(1).lower(), m.group(2).lower()
		# The FILE goes on EVERY rpi, whether that dongle is plugged in here or not. It costs 36 kB,
		# it has no effect until a matching controller is probed, and it means moving a dongle to
		# another pi - or plugging in a spare - just works: the kernel finds the patch at probe time
		# instead of coming up on ROM firmware and dropping off the bus on the first reset, with
		# nothing to tell you why. Only the RE-PROBE is conditional, because only a dongle that is
		# actually here can be re-probed.
		port = usbPortOf(vid, pid)			# "" = no such dongle on this pi right now
		did += 1
		# TWO separate questions, and they were tangled together before: is the FILE in place, and is
		# the patch actually IN the controller. A re-probe that did not take leaves the file installed
		# and the radio still on rom firmware, which the old "already installed - nothing to do" would
		# have accepted for ever.
		needInstall = not (os.path.isfile(dst) and sha256(src) == sha256(dst))
		needProbe   = (port != "")
		if not needInstall:
			if needProbe and not patchIsLoaded(fn):
				print("installBTfirmware {}: {} is installed but NOT loaded into {}:{} - re-probing".format(
						VERSION, fn, vid, pid))
			else:
				print("installBTfirmware {}: {} already installed{} - nothing to do".format(
						VERSION, fn, " and loaded into {}:{}".format(vid, pid) if needProbe else ""))
				continue					# in place and in the controller - leave the radio alone
		if checkOnly:
			print("installBTfirmware {}: {} {} - would {}".format(VERSION, fn,
					"is MISSING" if needInstall else "is installed but not loaded",
					("install it and re-probe {}:{}".format(vid, pid)) if needProbe else "install it (no such dongle here, file only)"))
			continue
		if needInstall:
			print("installBTfirmware {}: {} is missing - installing".format(VERSION, fn))
			try:
				if not os.path.isdir(FWDST):	os.makedirs(FWDST)
				shutil.copyfile(src, dst)
				os.chmod(dst, 0o644)
				print("   installed {} bytes -> {}  sha256 {}".format(os.path.getsize(dst), dst, sha256(dst)[:16]))
			except Exception as e:
				print("   COULD NOT install {}: {} (run with sudo?)".format(dst, e))
				report.append((30, "{} could NOT be installed: {}".format(fn, e)))
				continue
		if port == "":
			# Staged, nothing to re-probe. This IS reported to indigo, because it happens exactly ONCE
			# per rpi - the next start finds the file in place and says nothing at all - and because
			# without it there is no way to confirm "the firmware is on every rpi" short of logging
			# into each one by hand, which needs the password once per pi. One line per rpi on the
			# rollout, never again, is worth that.
			print("   no {}:{} dongle on this pi - the patch is now in place for whenever one is plugged in".format(vid, pid))
			report.append((30, "staged {} - no {}:{} dongle on this rpi, so nothing was re-probed; the patch "
						"is in place for whenever one is plugged in".format(fn, vid, pid)))
			continue
		print("   re-probing {}:{} on usb port {} so the driver loads it".format(vid, pid, port))
		if not reprobe(port):	continue

		# did it actually take? The build number changes when the patch RAM image is loaded, and it
		# is printed a couple of seconds AFTER the "Patch" line - so wait for it, and read it from
		# after that line only. ROM is build 0000; anything still reporting 0000 did NOT load.
		seen, bld = confirmPatch(fn)
		if seen and bld not in ("", "0000"):
			print("   PATCH LOADED - firmware build now {}".format(bld))
			# LEVEL 10, not 30. This is the SUCCESS case - the patch loaded and the radio now works -
			# and a success is not a warning. It is still in the rpi's own log at level 20 either
			# way; only whether it interrupts the indigo log changes.
			report.append((10, "{} {} for the {}:{} dongle and re-probed it - PATCH LOADED, firmware "
						"build now {}. Without it this controller runs on ROM firmware and drops off "
						"the usb bus on every reset".format(
						"installed" if needInstall else "re-applied", fn, vid, pid, bld)))
		elif seen and bld == "0000":
			print("   the kernel sent the patch but the controller still reports build 0000 - NOT loaded")
			report.append((30, "{} was sent to the {}:{} dongle but it still reports firmware build 0000, "
						"which is the UNPATCHED rom - the patch did not take. Check 'dmesg | grep -i "
						"bcm | tail' on this rpi".format(fn, vid, pid)))
		elif seen:
			print("   patch sent, kernel has not printed a new build number yet")
			report.append((30, "{} was sent to the {}:{} dongle but the kernel has not reported a new "
						"firmware build yet - check 'dmesg | grep -i bcm | tail' on this rpi".format(fn, vid, pid)))
		else:
			print("   re-probed, but no 'Patch' line in dmesg - check: dmesg | grep -i bcm | tail")
			report.append((30, "installed {} for {}:{} and re-probed, but the kernel never reported loading "
						"it - check 'dmesg | grep -i bcm | tail' on this rpi".format(fn, vid, pid)))

	if did == 0:
		print("installBTfirmware {}: none of the {} shipped file(s) has a usable usb id in its name"
				" - nothing to do".format(VERSION, len(shipped)))

	# the marker master.py looks for, now carrying the INDIGO log level each line deserves:
	# 10 for "the patch loaded" (a success is not a warning), 30 for anything that needs looking at.
	# Printed only when something actually happened, never on a quiet start.
	for lvl, line in report:
		print("BTFIRMWARE:{}: {}".format(lvl, line))


main()
