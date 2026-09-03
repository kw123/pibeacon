#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# irReplay  version 1.3
#
# Transmits a RECORDED pulse list - the mark/space microseconds irRecord.py prints - through the
# IR led. Nothing is encoded or decoded here: what went in comes out.
#
# WHY: when a receiver reads a real remote perfectly and the same receiver cannot read what this
# rpi sends, the question is whether the fault is in the FRAME we build or in the CHAIN that emits
# it. Replaying the remote's own recording answers it with no theory involved:
#    replay decodes cleanly  -> the chain is fine, the difference is in the frame we generate
#    replay garbles too      -> the chain distorts anything, and the frame was never the problem
#
# usage:
#    sudo python3 irReplay.py 18 /tmp/pulses.txt              send the list in that file on gpio 18
#    sudo python3 irReplay.py 18 /tmp/pulses.txt 0.33         ... with a 1/3 duty carrier
#    sudo python3 irReplay.py 18 /tmp/pulses.txt 0.5 36000    ... modulated at 36 kHz
#
# WHAT A REPLAY DOES AND DOES NOT REPRODUCE: the pulse list is the ENVELOPE - how long the light
# is on and off. The CARRIER inside those on-times is generated here and is not part of the
# recording, because the receiver that made the recording demodulated it away. So a replay of a
# real remote's capture sends the remote's timing with OUR carrier. When the envelope has already
# been shown to match and the ac still ignores it, the frequency is what is left to vary - which
# is what the last argument is for.
#
# The file is just the numbers irRecord printed, separated by commas and/or whitespace, starting
# with a MARK. Line breaks and trailing commas do not matter.
#
# python2 AND python3 compatible, like every other program in this directory.
####################
from __future__ import print_function
import sys
import time

try:
	import pigpio
except Exception:
	pigpio = None

VERSION = "1.3"
CARRIERHZ	= 38000
# NEVER split one wave across several wave_add_generic calls: pigpio builds a wave by absolute
# time offset, so a second call starts again at time 0 and MERGES instead of appending. See the
# long note in toshibaIR.py. One wave per call, and the call must stay under the 64 kB socket
# command limit = 5461 pulses.
MAXSOCKETPULSES = 5400


####-------------------------------------------------------------------------####
def readPulses(fname):
	"""Reads a pulse list from a file: numbers separated by commas, spaces or newlines.

	Inputs:
	    fname (str): file written by hand or pasted from an irRecord report
	Outputs:
	    list: integer microsecond durations, mark first
	"""
	raw = open(fname).read()
	for ch in ("\n", "\r", "\t", ";"):
		raw = raw.replace(ch, ",")
	out = []
	for part in raw.split(","):
		part = part.strip()
		if part == "":	continue
		try:	out.append(int(float(part)))
		except Exception:	pass
	return out


####-------------------------------------------------------------------------####
def splitMessages(pulses):
	"""Cuts a capture into its separate MESSAGES, keeping the gap that followed each one.

	A remote press is often several messages, 40 ms apart, and they are not always identical -
	this gree remote sends four and only the first carries the full state. Replaying them means
	reproducing that structure: each message is its own wave (one message = one wave, always),
	and the recorded gap is slept between them. Splitting anywhere else - at a pulse count, say -
	drops a socket round trip into the middle of a frame and breaks it.

	Inputs:
	    pulses (list): the whole capture, mark first
	Outputs:
	    list: [(messagePulses, gapAfterInUsec), ...]
	"""
	starts = [ii for ii in range(0, len(pulses) - 1, 2) if pulses[ii] > 2500]
	if len(starts) < 2:
		one = list(pulses)
		gap = 0
		if len(one) % 2 == 0 and one[-1] > 25000:
			gap = one[-1]
			one = one[:-1]
		return [(one, gap)]
	out = []
	for kk in range(len(starts)):
		end = starts[kk + 1] if kk + 1 < len(starts) else len(pulses)
		seg = list(pulses[starts[kk]:end])
		gap = 0
		if len(seg) % 2 == 0 and seg[-1] > 25000:
			gap = seg[-1]
			seg = seg[:-1]
		out.append((seg, gap))
	return out


####-------------------------------------------------------------------------####
def send(pi, pin, pulses, carrierHz=CARRIERHZ, dutyCycle=0.5):
	"""Puts `pulses` on the led: even entries are marks (carrier), odd ones are spaces (dark).

	Inputs:
	    pi (pigpio.pi): connected pigpio client
	    pin (int): BCM gpio the led driver is on
	    pulses (list): alternating mark/space microseconds
	    carrierHz (int): carrier frequency
	    dutyCycle (float): carrier duty
	Outputs:
	    float: seconds the burst took
	"""
	mask	= 1 << int(pin)
	period	= 1000000. / float(carrierHz)
	onUsec	= int(round(period * dutyCycle))
	offUsec	= int(round(period)) - onUsec

	def buildWave(msg):
		out = []
		for ii in range(len(msg)):
			usec = msg[ii]
			if ii % 2 == 0:
				elapsed = 0.
				while elapsed < usec:
					out.append(pigpio.pulse(mask, 0, onUsec))
					out.append(pigpio.pulse(0, mask, offUsec))
					elapsed += period
			else:
				out.append(pigpio.pulse(0, mask, int(usec)))
		return out

	messages = splitMessages(pulses)
	waves    = [(buildWave(msg), gap) for msg, gap in messages]

	pi.set_mode(pin, pigpio.OUTPUT)
	pi.write(pin, 0)

	# ONE WAVE, NEVER SPLIT. Splitting was the original sin here and it hides well: chopping the
	# list into several wave_add_generic calls MERGES them, because pigpio builds a wave by
	# absolute time offset and a second call restarts at t=0. Sending the chunks as separate
	# WAVES instead is no better for a single transmission - each wave costs a socket round trip,
	# so a gap of milliseconds lands in the middle of a frame and the receiver sees two broken
	# ones. The only correct answer is to refuse.
	#
	# It fits in one wave as long as the pulse list is ONE message: a gree frame is about 3100
	# pigpio pulses at 30 kHz and 3900 at 38 kHz. A whole 4-repeat capture is 12000 to 22000 -
	# over the socket limit AND over the 12000 the hardware holds - which is why irRecord now
	# prints the first message on its own and irTest.sh replays that.
	for wave, gap in waves:
		if len(wave) > MAXSOCKETPULSES:
			raise IOError(
				"irReplay: one message needs {} pigpio pulses at {} Hz, more than a single wave "
				"can hold ({}). A higher carrier costs more pulses for the same timing - this "
				"message fits at 38 kHz but not at 56.".format(len(wave), carrierHz, MAXSOCKETPULSES))

	start = time.time()
	try:
		for nn in range(len(waves)):
			wave, gap = waves[nn]
			pi.wave_add_new()
			if pi.wave_add_generic(wave) < 0:
				raise IOError("irReplay: pigpio refused {} pulses".format(len(wave)))
			wid = pi.wave_create()
			if wid < 0:
				raise IOError("irReplay: could not create the wave, id:{}".format(wid))
			pi.wave_send_once(wid)
			while pi.wave_tx_busy():
				time.sleep(0.002)
			pi.wave_delete(wid)
			# the gap the remote left before its next message, measured from the end of this one
			if gap > 0 and nn < len(waves) - 1:
				time.sleep(gap / 1000000.)
	finally:
		try:	pi.write(pin, 0)
		except Exception:	pass
	sent = time.time() - start
	return sent


####-------------------------------------------------------------------------####
def main():
	"""Command line entry point: gpio, pulse file, optional duty."""
	if pigpio is None:
		print("ERROR: the pigpio module is not installed on this rpi")
		return 1
	args = sys.argv[1:]
	if len(args) < 2:
		print("usage: sudo python3 irReplay.py <gpio> <pulsefile> [duty] [carrierHz]")
		return 1
	pin     = int(args[0])
	fname   = args[1]
	duty    = 0.5
	carrier = CARRIERHZ
	if len(args) > 2:
		try:	duty = float(args[2])
		except Exception:	pass
	if len(args) > 3:
		try:	carrier = int(float(args[3]))
		except Exception:	pass
	if duty < 0.1 or duty > 0.9:		duty = 0.5
	if carrier < 25000 or carrier > 60000:	carrier = CARRIERHZ

	pulses = readPulses(fname)
	if len(pulses) < 4:
		print("ERROR: {} holds {} numbers - that is not a pulse list".format(fname, len(pulses)))
		return 1

	print("irReplay v{}: {} pulses, {:.1f} ms, gpio {}, carrier {} Hz duty {:.2f}".format(
			VERSION, len(pulses), sum(pulses) / 1000., pin, carrier, duty))
	msgs = splitMessages(pulses)
	print("   {} message(s): {}".format(
			len(msgs), ", ".join("{} pulses".format(len(m)) + ("" if g == 0 else " +{} us gap".format(g))
									for m, g in msgs)))
	pi = pigpio.pi()
	if not pi.connected:
		print("ERROR: cannot reach pigpiod")
		return 1
	try:
		took = send(pi, pin, pulses, carrierHz=carrier, dutyCycle=duty)
		print("sent in {:.3f} s (the list is {:.3f} s)".format(took, sum(pulses) / 1000000.))
	finally:
		pi.stop()
	return 0


if __name__ == "__main__":
	sys.exit(main())
