#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# irScan  version 1.0
#
# Walks the IR CARRIER FREQUENCY in small steps and sends a real command at every one, so an AC
# that ignores a frame known to be correct can be asked which frequency it is actually listening
# at. 25 to 48 kHz in 1 kHz steps by default: 24 sends, five seconds apart, two minutes in all.
#
# WHY THE FREQUENCY IS THE THING LEFT: an ir receiver demodulates the carrier and reports only
# the envelope, so a recording of the unit's own remote, a byte-perfect loopback and a
# pulse-by-pulse diff against that remote can ALL pass while the carrier is completely wrong.
# The receiver inside the AC is a narrow band filter, and a few kHz off is read fine by a
# receiver held at 20 cm and ignored by the unit across the room. Nothing we can record measures
# it - only trying it, or a photodiode on a scope.
#
# HOW TO READ IT: the temperature ALTERNATES, 19 / 21 / 19 / 21 ... So every send that reaches
# the unit changes its display, and a frequency that works cannot hide behind the state already
# being right. Watch the AC and note the step: each one is printed with its frequency and the
# time before it goes out.
#
# The frames go through greeIR/toshibaIR, not through a replay, so ONE MESSAGE = ONE WAVE holds
# and nothing is split. Every frequency in the default range fits: the biggest wave is 5075
# pigpio pulses at 48 kHz against the 5400 one wave can carry.
#
# usage:
#    python3 irScan.py                        25..48 kHz, 1 kHz steps, 5 s apart, gpio 18, gree
#    python3 irScan.py 30 40                  30..40 kHz
#    python3 irScan.py 30 40 2 8              ... 2 kHz steps, 8 s apart
#    python3 irScan.py 25 48 1 5 18 toshiba   ... on gpio 18, toshiba frames
#
# NO sudo: it reaches the gpios through the pigpiod socket and needs no root, and killSudos
# (master, every 10th loop) kills anything whose command line holds "python" and "sudo".
#
# python2 AND python3 compatible, like every other program in this directory.
####################
from __future__ import print_function
import os
import sys
import time

try:
	import pigpio
except Exception:
	pigpio = None
try:
	import greeIR
except Exception:
	greeIR = None
try:
	import toshibaIR
except Exception:
	toshibaIR = None

VERSION		= "1.0"
FIRSTKHZ	= 25
LASTKHZ		= 48
STEPKHZ		= 1
SECS		= 5.
GPIO		= 18
BRAND		= "gree"
TEMPS		= [19, 21]		# alternating, so every send that lands changes the display
MAXWAVE		= 5400			# pulses one wave_add_generic call can carry


####-------------------------------------------------------------------------####
def sendOne(pi, pin, brand, temperature, carrierHz, dutyCycle=0.5):
	"""Sends one cool/auto command at the given carrier.

	Inputs:
	    pi (pigpio.pi): connected pigpio client
	    pin (int): gpio the ir led driver is on
	    brand (str): gree or toshiba
	    temperature (int): setpoint to ask for
	    carrierHz (int): the frequency under test
	    dutyCycle (float): carrier duty
	Outputs:
	    str: the frame in hex, for the log
	"""
	if brand == "gree":
		state = greeIR.buildState("cool", temperature, "auto", True)
		greeIR.sendState(pi, pin, state, carrierHz=carrierHz, dutyCycle=dutyCycle)
		return greeIR.stateToHex(state)
	frame = toshibaIR.modeFanTemp(mode="cool", temperature=temperature, fan="auto")
	toshibaIR.sendFrame(pi, pin, frame, carrierHz=carrierHz, dutyCycle=dutyCycle)
	return toshibaIR.frameToHex(frame)


####-------------------------------------------------------------------------####
def leadIn():
	"""Waits before the first send, so the run can be started here and watched at the ac.

	Seconds come from the IRLEADIN environment variable, 15 by default. irTest.sh does its own
	countdown and then sets IRLEADIN=0, so starting through it does not wait twice.

	Inputs:
	    none
	Outputs:
	    None
	"""
	try:	secs = float(os.environ.get("IRLEADIN", 15))
	except Exception:	secs = 15.
	if secs <= 0:	return
	print("== starting in {:.0f} s - go to the ac now".format(secs))
	while secs > 0:
		print("   ... {:.0f} s".format(secs))
		nap = 5. if secs > 5 else secs
		time.sleep(nap)
		secs -= nap
	print("== go")
	print("")


####-------------------------------------------------------------------------####
def main():
	"""Command line entry point: first kHz, last kHz, step kHz, seconds, gpio, brand."""
	args = sys.argv[1:]
	def arg(nn, default, cast):
		if len(args) > nn:
			try:	return cast(args[nn])
			except Exception:	pass
		return default

	firstKHz = arg(0, FIRSTKHZ, int)
	lastKHz  = arg(1, LASTKHZ,  int)
	stepKHz  = max(1, arg(2, STEPKHZ, int))
	secs     = arg(3, SECS,  float)
	pin      = arg(4, GPIO,  int)
	brand    = arg(5, BRAND, str).strip().lower()
	duty     = arg(6, 0.5,   float)

	if pigpio is None:
		print("ERROR: the pigpio module is not installed on this rpi")
		return 1
	if brand not in ("gree", "toshiba"):
		print("ERROR: brand must be gree or toshiba, not '{}'".format(brand))
		return 1
	if brand == "gree" and greeIR is None:
		print("ERROR: greeIR.py is not on this rpi - send the plugin files to the rpis")
		return 1
	if brand == "toshiba" and toshibaIR is None:
		print("ERROR: toshibaIR.py is not on this rpi - send the plugin files to the rpis")
		return 1
	if not (0 < pin < 28):
		print("ERROR: {} is not a gpio number".format(pin))
		return 1

	freqs = list(range(firstKHz * 1000, lastKHz * 1000 + 1, stepKHz * 1000))
	if not freqs:
		print("ERROR: {}..{} kHz in {} kHz steps is an empty range".format(firstKHz, lastKHz, stepKHz))
		return 1

	print("irScan v{}: {} on gpio {}, {} to {} kHz in {} kHz steps, {:.0f} s apart".format(
			VERSION, brand, pin, firstKHz, lastKHz, stepKHz, secs))
	print("   {} sends, about {:.0f} s. The temperature alternates {} - every send that reaches".format(
			len(freqs), len(freqs) * secs, " / ".join("{} C".format(t) for t in TEMPS)))
	print("   the unit changes its display, so WATCH THE AC and note which step moves it.")
	print("")
	leadIn()

	pi = pigpio.pi()
	if not pi.connected:
		print("ERROR: cannot reach pigpiod - is it running?")
		return 1
	sent = []
	try:
		for ii in range(len(freqs)):
			carrier     = freqs[ii]
			temperature = TEMPS[ii % len(TEMPS)]
			try:
				hexF = sendOne(pi, pin, brand, temperature, carrier, duty)
			except Exception as e:
				# a wave that does not fit is the one failure that is ours, not the ac's
				print("   {:2d}/{:<2d}  {:5d} Hz   NOT SENT: {}".format(ii + 1, len(freqs), carrier, e))
				continue
			print("   {:2d}/{:<2d}  {:5d} Hz   {} C   {}   {}".format(
					ii + 1, len(freqs), carrier, temperature, hexF, time.strftime("%H:%M:%S")))
			sent.append((carrier, temperature))
			if ii < len(freqs) - 1:
				time.sleep(secs)
	except KeyboardInterrupt:
		print("\n   stopped")
	finally:
		try:	pi.stop()
		except Exception:	pass

	print("")
	print("{} frequencies sent. If the ac moved on one of them, that step's frequency is the".format(len(sent)))
	print("answer - put it in the device dialog. Run it again from further away to confirm: the")
	print("first frequency that works up close is not always the one with margin across the room.")
	print("If NOTHING moved, the carrier is not the problem and the light is not arriving - hold")
	print("the led 10 cm from the unit's ir window and try one command there.")
	return 0


if __name__ == "__main__":
	sys.exit(main())
