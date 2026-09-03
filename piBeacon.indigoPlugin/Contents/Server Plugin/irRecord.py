#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# irRecord  version 1.0
#
# Records what an IR REMOTE sends, using a TSOP38238 (or any 38 kHz IR receiver module), and
# decodes it far enough to say whether piBeacon's toshibaIR encoder speaks the same language.
#
# WHY: an AC that ignores a correctly built frame tells you nothing about WHICH part is wrong -
# the protocol variant, the bit layout, the frame length or the aim. The unit's own remote is the
# only authority. This reads it.
#
# The TSOP does the hard part: it demodulates the 38 kHz carrier and hands over a clean digital
# envelope. Its output IDLES HIGH and pulls LOW while a carrier burst arrives, so a LOW period is
# a "mark" and a HIGH period a "space" - which is the same alternating list toshibaIR.toPulses()
# produces, and can be compared with it directly.
#
# wiring (TSOP38238 seen from the FRONT, the domed side, legs down): 1 OUT | 2 GND | 3 VS
#     OUT -> a free gpio (3.3 V logic, the module has its own pull-up)
#     GND -> ground
#     VS  -> 3.3 V, with 100 ohm in series and 4.7 uF from VS to ground (vishay's own
#            recommendation - it keeps supply noise out of a very sensitive receiver)
#
# usage:
#    sudo python3 irRecord.py                 gpio 24, wait 15 s for a button press
#    sudo python3 irRecord.py 24 30           gpio 24, wait 30 s
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

VERSION = "1.0"

DEFAULTGPIO		= 24
DEFAULTWAIT		= 15.		# seconds to wait for the first edge
ENDGAP			= 60000		# us of silence that ends a recording. The inter-FRAME gap is only
							# 4600-7400 us, so this must be well above it or a two frame
							# transmission is cut in half and reported as one frame
GLITCH			= 100		# us: pigpio ignores edges shorter than this. Kills receiver noise
							# without touching the shortest real pulse (a 490 us space)
MAXPULSES		= 2000

# what toshibaIR sends, for the comparison at the end
REFERENCE = {"header mark":4400, "header space":4300, "bit mark":580, "one space":1600, "zero space":490}


####-------------------------------------------------------------------------####
def record(gpio, waitSecs):
	"""Waits for a remote and returns the mark/space list it sent, in microseconds.

	Inputs:
	    gpio (int): the gpio the TSOP output is on
	    waitSecs (float): how long to wait for the first edge
	Outputs:
	    list: alternating durations, starting with a mark, or [] when nothing arrived
	"""
	pi = pigpio.pi()
	if not pi.connected:
		raise IOError("irRecord: cannot reach pigpiod - is it running?")

	edges = []			# (tick, level)
	def cbf(g, level, tick):
		if len(edges) < MAXPULSES * 2:
			edges.append((tick, level))

	pi.set_mode(gpio, pigpio.INPUT)
	pi.set_pull_up_down(gpio, pigpio.PUD_OFF)		# the TSOP drives its output itself
	pi.set_glitch_filter(gpio, GLITCH)
	cb = pi.callback(gpio, pigpio.EITHER_EDGE, cbf)

	try:
		idle = pi.read(gpio)
		if idle != 1:
			print("WARNING: gpio {} reads {} while idle - a TSOP idles HIGH. Wrong pin, no power, or OUT and GND swapped?".format(gpio, idle))

		# AMBIENT NOISE FIRST. A TSOP is a very sensitive receiver and mains lit rooms are full of
		# infrared: lamps flicker at twice the mains frequency (100 Hz here) and LED/CFL drivers
		# switch near 38 kHz, which is exactly what this part is tuned to. Measuring it takes a
		# second and turns "the recording is garbage" into a number with a remedy.
		del edges[:]
		time.sleep(1.)
		noise = len(edges)
		del edges[:]
		if noise > 4:
			print("AMBIENT NOISE: {} edges in 1 s with no remote sending.".format(noise))
			print("   Infrared from lamps. Switch the room lights off for the recording, or shield the")
			print("   receiver: point it away from every lamp, or sink it into a dark tube. Also check the")
			print("   100 ohm + 4.7 uF on VS - without them supply ripple reads as bursts too.")
		else:
			print("ambient noise: {} edges in 1 s - quiet enough".format(noise))

		print("waiting up to {:.0f} s - point the remote at the receiver and press ONE button ...".format(waitSecs))
		tEnd = time.time() + waitSecs
		while time.time() < tEnd:
			# wait for something to start
			while time.time() < tEnd and len(edges) == 0:
				time.sleep(0.02)
			if len(edges) == 0:
				return []

			# let it finish: nothing new for ENDGAP means the transmission is over
			lastCount = -1
			while lastCount != len(edges):
				lastCount = len(edges)
				time.sleep(ENDGAP / 1000000. * 1.5)

			# REAL remote, or another flicker from a lamp? A remote starts with a header mark far
			# longer than any bit, and sends a lot of edges. Noise has neither. Discarding it here
			# instead of reporting it means the recording can be started with the lights on and it
			# simply waits for the button press.
			raw = [pigpio.tickDiff(edges[ii][0], edges[ii + 1][0]) for ii in range(len(edges) - 1)]
			if len(raw) >= 30 and max(raw) > 2500:
				break
			print("   ignored {} edges of noise, still waiting ...".format(len(edges)))
			del edges[:]
		if len(edges) == 0:
			return []
	finally:
		try:	cb.cancel()
		except Exception:	pass
		try:	pi.set_glitch_filter(gpio, 0)
		except Exception:	pass
		try:	pi.stop()
		except Exception:	pass

	# LOW = carrier present = mark. The first edge of a transmission is the falling one, so the
	# duration between edge n and n+1 is a mark when the level AT edge n is 0.
	pulses = []
	for ii in range(len(edges) - 1):
		dur = pigpio.tickDiff(edges[ii][0], edges[ii + 1][0])
		pulses.append(dur)
	if pulses and edges[0][1] != 0:
		# started on a rising edge: the leading fragment is not a mark, drop it
		pulses = pulses[1:]
	return pulses


####-------------------------------------------------------------------------####
def cluster(values, tolerance=0.35):
	"""Groups similar durations, so "the bit mark is 580 us" can be said instead of listing 72 of them.

	Inputs:
	    values (list): durations in microseconds
	    tolerance (float): relative width of a group
	Outputs:
	    list: [[average, count], ...] biggest group first
	"""
	groups = []
	for val in values:
		for grp in groups:
			if abs(val - grp[0]) <= grp[0] * tolerance:
				grp[0] = (grp[0] * grp[1] + val) / (grp[1] + 1.)
				grp[1] += 1
				break
		else:
			groups.append([float(val), 1])
	groups.sort(key=lambda g: -g[1])
	return groups


####-------------------------------------------------------------------------####
def decode(pulses):
	"""Turns the mark/space list into frames of bytes, the way toshibaIR builds them.

	A space longer than 3 ms after the data has started is an inter-frame gap, not a bit - that is
	what separates the repeats. Bits are MSB first, a long space is a 1.

	Inputs:
	    pulses (list): alternating mark/space durations
	Outputs:
	    tuple: (frames, header) - frames is a list of bytearrays, header is (mark, space) or None
	"""
	if len(pulses) < 4:
		return [], None

	header = (pulses[0], pulses[1])
	# the split between a "0" and a "1" space: halfway between the two clusters, or 1000 us when
	# only one kind was sent
	spaces = [pulses[ii] for ii in range(3, len(pulses), 2) if pulses[ii] < 3000]
	grps   = cluster(spaces)
	if len(grps) >= 2:
		lo, hi = sorted([grps[0][0], grps[1][0]])
		split  = (lo + hi) / 2.
	else:
		split = 1000.

	frames = []
	bits   = []
	ii     = 2
	while ii < len(pulses):
		mark = pulses[ii]
		if ii + 1 >= len(pulses):
			break							# the trailing mark that closes a frame, not a bit
		space = pulses[ii + 1]
		if mark > 3000:						# a new header: the previous frame ended
			if bits:
				frames.append(bits)
				bits = []
			ii += 2
			continue
		if space > 3000:					# tail mark + inter-frame gap: the frame is complete,
			if bits:						# and this mark is the TAIL mark, not a data bit
				frames.append(bits)
				bits = []
			ii += 2
			continue
		bits.append(1 if space > split else 0)
		ii += 2
	if bits:
		frames.append(bits)

	out = []
	for bitList in frames:
		frame = bytearray()
		for start in range(0, len(bitList) - 7, 8):
			byte = 0
			for bit in bitList[start:start + 8]:
				byte = (byte << 1) | bit
			frame.append(byte)
		if len(frame) > 0:
			out.append((frame, len(bitList)))
	return out, header


####-------------------------------------------------------------------------####
def describe(frame):
	"""Reads a decoded frame with piBeacon's toshiba layout and says what it would mean.

	Inputs:
	    frame (bytearray): one decoded frame
	Outputs:
	    list: lines of text
	"""
	MODES = {0:"auto", 1:"cool", 2:"dry", 3:"heat", 4:"fan", 7:"off"}
	lines = []
	if len(frame) < 6 or frame[0] != 0xF2 or frame[1] != 0x0D:
		lines.append("      does NOT start with F2 0D - this is not the toshiba protocol piBeacon sends")
		return lines

	xorAll = 0
	for byte in frame[:-1]:
		xorAll ^= byte
	lines.append("      prefix F2 0D ok, length nibble {} -> {} bytes (frame really is {}), model/unit {}".format(
					frame[2] & 0x0F, (frame[2] & 0x0F) + 6, len(frame), frame[2] >> 4))
	lines.append("      byte3 {}= ~byte2      checksum {}= xor of the rest ({:02X} vs {:02X})".format(
					"" if frame[3] == ((~frame[2]) & 0xFF) else "!", "" if frame[-1] == xorAll else "!",
					frame[-1], xorAll))
	if len(frame) >= 7:
		lines.append("      byte4 {:02X}  long-msg bit {}  short-msg bit {}".format(
						frame[4], (frame[4] >> 3) & 1, (frame[4] >> 5) & 1))
		lines.append("      temperature {} C   swing {}".format(17 + (frame[5] >> 4), frame[5] & 0x07))
		lines.append("      mode {}   fan raw {}".format(MODES.get(frame[6] & 0x07, frame[6] & 0x07), frame[6] >> 5))
	return lines


####-------------------------------------------------------------------------####
def report(pulses):
	"""Prints everything worth knowing about one recording.

	Inputs:
	    pulses (list): alternating mark/space durations
	Outputs:
	    None
	"""
	total = sum(pulses) / 1000.
	print("")
	print("=" * 78)
	print("captured {} pulses, {:.1f} ms total".format(len(pulses), total))
	print("=" * 78)

	marks  = [pulses[ii] for ii in range(0, len(pulses), 2)]
	spaces = [pulses[ii] for ii in range(1, len(pulses), 2)]
	print("\nmark lengths (us, biggest group first):")
	for avg, cnt in cluster(marks)[:5]:
		print("   {:8.0f} us  x{}".format(avg, cnt))
	print("space lengths (us):")
	for avg, cnt in cluster(spaces)[:5]:
		print("   {:8.0f} us  x{}".format(avg, cnt))

	frames, header = decode(pulses)
	if header is not None:
		print("\nheader: mark {:.0f} us, space {:.0f} us".format(header[0], header[1]))
		print("piBeacon sends:  mark {} us, space {} us".format(REFERENCE["header mark"], REFERENCE["header space"]))
		diffM = abs(header[0] - REFERENCE["header mark"]) / float(REFERENCE["header mark"]) * 100.
		diffS = abs(header[1] - REFERENCE["header space"]) / float(REFERENCE["header space"]) * 100.
		print("difference:      {:.0f} % / {:.0f} %  {}".format(diffM, diffS,
				"-> SAME header" if diffM < 20 and diffS < 20 else "-> DIFFERENT header, this is another protocol"))

	print("\n{} frame(s):".format(len(frames)))
	for ii in range(len(frames)):
		frame, nBits = frames[ii]
		hexed = "".join("{:02X}".format(b) for b in frame)
		print("   frame {}: {} bits -> {} bytes   {}".format(ii + 1, nBits, len(frame), hexed))
		for line in describe(frame):
			print(line)

	print("\nraw pulse list (paste this back to indigo/claude - mark, space, mark, space ...):")
	line = "   "
	for ii in range(len(pulses)):
		line += "{}, ".format(int(pulses[ii]))
		if len(line) > 100:
			print(line)
			line = "   "
	if line.strip() != "":
		print(line)
	print("")


####-------------------------------------------------------------------------####
def diffFrames(prev, curr):
	"""Which bytes changed between two frames - the whole point of recording a sequence.

	Pressing up/down/up moves exactly one setting at a time, so the bytes that move ARE that
	setting. Anything else that moves is either a counter or something the layout does not
	explain yet, and either way it is worth seeing.

	Inputs:
	    prev (bytearray): the previous capture's first frame, or None
	    curr (bytearray): this capture's first frame
	Outputs:
	    list: lines of text
	"""
	if prev is None:
		return []
	if len(prev) != len(curr):
		return ["      CHANGED vs previous: frame LENGTH {} -> {} bytes".format(len(prev), len(curr))]
	changed = [ii for ii in range(len(curr)) if prev[ii] != curr[ii]]
	if not changed:
		return ["      identical to the previous capture"]
	out = []
	for ii in changed:
		what = ""
		if   ii == 5:	what = "   temperature {} -> {} C".format(17 + (prev[5] >> 4), 17 + (curr[5] >> 4))
		elif ii == 6:	what = "   mode/fan"
		elif ii == len(curr) - 1:	what = "   checksum, follows from the rest"
		out.append("      CHANGED vs previous: byte{} {:02X} -> {:02X}{}".format(ii, prev[ii], curr[ii], what))
	return out


####-------------------------------------------------------------------------####
def main():
	"""Command line entry point: reads gpio and wait time, records once, prints the report."""
	gpio     = DEFAULTGPIO
	waitSecs = DEFAULTWAIT
	count    = 1
	args     = sys.argv[1:]
	if len(args) > 0:
		try:	gpio = int(args[0])
		except Exception:	pass
	if len(args) > 1:
		try:	waitSecs = float(args[1])
		except Exception:	pass
	if len(args) > 2:
		try:	count = max(1, min(10, int(args[2])))
		except Exception:	pass

	print("irRecord v{}  -  gpio {}, IR receiver output expected there".format(VERSION, gpio))
	if pigpio is None:
		print("ERROR: the pigpio module is not installed on this rpi")
		return 1
	if count > 1:
		print("recording {} button presses in a row - press one, wait for the line to appear, press the next.".format(count))
		print("up / down / up / down on the temperature is the most useful sequence: only ONE setting moves per press.")

	prev = None
	got  = 0
	for nn in range(count):
		try:
			pulses = record(gpio, waitSecs)
		except Exception as e:
			print("ERROR: {}".format(e))
			return 1

		if not pulses:
			print("nothing received in {:.0f} s.".format(waitSecs))
			if got == 0:
				print("  - is the receiver on gpio {} and powered (VS 3.3 V, GND, OUT)?".format(gpio))
				print("  - it idles HIGH: check with a meter that the pin sits at 3.3 V with no remote")
				print("  - aim the remote at the domed side from 10-30 cm and press one button")
				return 1
			break
		got += 1

		if count == 1:
			report(pulses)
		else:
			# a sequence: the FULL report for the first one, a compact line + the diff for the rest.
			# Ten raw pulse lists would bury the one thing being looked for.
			frames, header = decode(pulses)
			print("")
			print("---- capture {}/{}:  {} pulses, {:.1f} ms, header {:.0f}/{:.0f} us, {} frame(s)".format(
					nn + 1, count, len(pulses), sum(pulses) / 1000.,
					header[0] if header else 0, header[1] if header else 0, len(frames)))
			if not frames:
				print("      could not decode this one")
				continue
			frame = frames[0][0]
			print("      {}".format("".join("{:02X}".format(b) for b in frame)))
			for line in describe(frame):
				print(line)
			for line in diffFrames(prev, frame):
				print(line)
			if nn == 0:
				report(pulses)
			prev = frame

	if got > 1:
		print("\nrecorded {} presses. The bytes listed as CHANGED are the ones carrying whatever you".format(got))
		print("altered between presses - everything else is fixed for this remote.")
	return 0


if __name__ == "__main__":
	sys.exit(main())
