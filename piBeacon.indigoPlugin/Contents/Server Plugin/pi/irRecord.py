#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# irRecord  version 1.1
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
# usage:  sudo python3 irRecord.py [gpio] [wait] [count] [ledGpio] [duty]
#
# All five are optional and POSITIONAL - to reach the fourth you have to give the first three.
#    1  gpio      the gpio the TSOP receiver output is on        default 24
#    2  wait      seconds to wait for a button press             default 15
#    3  count     how many presses to record in a row            default 1
#    4  ledGpio   gpio of the IR LED. 0 = no echo, record only   default 0
#    5  duty      carrier duty for the echo                      default 0.5
#
# JUST RECORDING is the first two:
#    sudo python3 irRecord.py 10 30           receiver on gpio 10, wait 30 s, print the report
#    sudo python3 irRecord.py 10 30 2         the same, two presses, with a diff between them
#    sudo python3 irRecord.py                 receiver on gpio 24, wait 15 s
#
# The ECHO only happens when a led gpio is given as the FOURTH argument:
#    sudo python3 irRecord.py 10 30 1 18              record, then replay it on gpio 18
#
#    sudo python3 irRecord.py -h              print this list
#
# ECHO MODE is the test that settles an AC which ignores a frame the receiver reads perfectly.
# It records the unit's OWN remote and immediately retransmits that exact pulse list on the ir
# led. Nothing is decoded, rebuilt or assumed in between - a waveform that is known to work goes
# back out through our emitter.
#
# THE ONE THING THAT MAKES THIS A TEST: the ac must not already be in the state the echo asks
# for, or a reaction cannot be told apart from the unit still obeying the button press it heard a
# moment ago. Hence the 15 second pause after the recording - use it:
#    1  record an ON command, say cool 21 C. The ac hears the remote and switches on. Expected.
#    2  the pause starts. Press OFF on the remote. The unit switches off.
#    3  the pause ends and the recording goes back out through our led, still asking for ON 21 C.
# Now only our emitter can turn that unit on, and there are two outcomes, both conclusive:
#    the AC reacts   -> the emitter, the carrier and the aim are all fine, so whatever we build
#                       differs from the remote in some bit or timing the AC checks
#    the AC ignores  -> the frame was never the problem. The light is not reaching the unit with
#                       enough power, or not at all: aim, distance, or the led driver
# Each capture is echoed TWICE, a few seconds apart, so one press answers both halves:
#    RAW       - exactly what was recorded, receiver bias and all
#    DE-BIASED - marks shortened and spaces lengthened by DEBIASUS, which undoes the mark
#                stretching every TSOP-class receiver adds and puts the timings back to what the
#                remote actually emitted
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
try:
	import irReplay			# only needed for the echo mode, and it owns the one-wave-per-call
except Exception:			# rule that the transmission depends on - never re-implement it here
	irReplay = None

VERSION = "1.1"

USAGE = """usage:  sudo python3 irRecord.py [gpio] [wait] [count] [ledGpio] [duty]

All five are optional and POSITIONAL - to reach the fourth you have to give the first three.
   1  gpio      the gpio the TSOP receiver output is on        default 24
   2  wait      seconds to wait for a button press             default 15
   3  count     how many presses to record in a row            default 1
   4  ledGpio   gpio of the IR LED. 0 = no echo, record only   default 0
   5  duty      carrier duty for the echo                      default 0.5

just recording, which is the normal case:
   sudo python3 irRecord.py 10 30           receiver on gpio 10, wait 30 s, print the report
   sudo python3 irRecord.py 10 30 2         the same, two presses, with a diff between them

record AND echo it back out - only when a led gpio is given as the fourth argument:
   sudo python3 irRecord.py 10 30 1 18              record, then replay it on gpio 18"""

DEFAULTGPIO		= 24
DEFAULTWAIT		= 15.		# seconds to wait for the first edge
ENDGAP			= 60000		# us of silence that ends a recording. The inter-FRAME gap is only
							# 4600-7400 us, so this must be well above it or a two frame
							# transmission is cut in half and reported as one frame
GLITCH			= 100		# us: pigpio ignores edges shorter than this. Kills receiver noise
							# without touching the shortest real pulse (a 490 us space)
MAXPULSES		= 2000
ECHOWAIT		= 15.		# s between the recording and the echo. This pause is the whole test:
							# it is when the remote is used to put the ac into a DIFFERENT state,
							# so that the replay has something to change and a reaction cannot be
							# confused with the ac still obeying the button press it just heard
ECHOGAP			= 15.		# s before the second echo, same purpose - time to switch the unit back
DEBIASUS		= 80		# us: a TSOP reports every mark about this much too long and every space
							# the same amount too short - measured here as 620->704 and 540->460
							# against a remote whose real timings we know. Replaying the recording
							# unchanged therefore sends marks that are already stretched once, and
							# the AC's own receiver stretches them a second time

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
			# ambient light can trigger the capture a moment BEFORE the remote starts, so the
			# recording begins in the middle of a message and decodes to nonsense. The header is
			# the longest mark there is: drop everything in front of the first one.
			for jj in range(0, len(raw) - 1, 2):
				if raw[jj] > 2500:
					if jj > 0:
						print("   dropped {} pulses of noise before the header".format(jj))
						del edges[:jj]
					break
			raw = [pigpio.tickDiff(edges[ii][0], edges[ii + 1][0]) for ii in range(len(edges) - 1)]
			if len(raw) >= 30 and max(raw) > 2500 and raw[0] > 2500:
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
def firstMessage(pulses):
	"""Returns just the FIRST message of a capture - header to the pulse before the next header.

	A capture holds 2 to 4 repeats and it is the LATER ones that come out corrupted: the receiver
	has been sitting in a strong signal by then, its agc has wound the gain down, and its output
	degenerates towards a uniform train of short bit cells that decodes to near zeros. The remote
	sends every repeat identically, so those are reception artefacts, not data.

	A replay wants one clean message. Sending the whole degraded train instead means the good
	frame is followed by three malformed ones, which is not what the remote does and not a test
	of anything.

	Inputs:
	    pulses (list): the full capture, mark first
	Outputs:
	    list: the first message alone, trailing inter-message gap removed
	"""
	starts = [ii for ii in range(0, len(pulses) - 1, 2) if pulses[ii] > 2500]
	if len(starts) < 2:	out = list(pulses)
	else:				out = list(pulses[starts[0]:starts[1]])
	while len(out) > 2 and len(out) % 2 == 0 and out[-1] > 25000:
		out = out[:-1]			# the gap that leads to the next repeat is not part of this one
	return out


####-------------------------------------------------------------------------####
def countdown(secs, step=5.):
	"""Sleeps, printing how long is left, so the pause can be used rather than waited out.

	Over ssh with python -u these appear as they happen. Through the plugin menu the whole report
	arrives at the end, which is why the dialog states the timing in advance.

	Inputs:
	    secs (float): how long to wait
	    step (float): how often to print
	Outputs:
	    None
	"""
	left = float(secs)
	while left > 0:
		print("   ... {:.0f} s".format(left))
		nap   = min(step, left)
		time.sleep(nap)
		left -= nap


####-------------------------------------------------------------------------####
def deBias(pulses, usec=DEBIASUS):
	"""Undoes the receiver's mark stretching, so a recording can be retransmitted as it was SENT.

	Inputs:
	    pulses (list): alternating mark/space microseconds as recorded
	    usec (int): how much the receiver adds to a mark and takes off a space
	Outputs:
	    list: the corrected pulse list, same length
	"""
	out = []
	for ii in range(len(pulses)):
		if ii % 2 == 0:	out.append(max(60, pulses[ii] - usec))		# mark
		else:			out.append(pulses[ii] + usec)				# space
	return out


####-------------------------------------------------------------------------####
def echo(ledGpio, pulses, carrierHz=38000, dutyCycle=0.5):
	"""Retransmits a recorded pulse list on the ir led, once raw and once de-biased.

	Nothing here decodes or rebuilds anything: this is the recording itself going back out, which
	is what makes the outcome mean something. See the ECHO MODE note at the top of the file.

	Inputs:
	    ledGpio (int): the gpio the ir led driver is on
	    pulses (list): what record() returned
	    carrierHz (int): carrier for the retransmission. NOT part of the recording - a receiver
	                     demodulates it away, so it has to be generated here. Nothing varies it
	                     any more: on both units tested the frequency turned out not to matter,
	                     and irScan.py is where to look if a future one disagrees
	    dutyCycle (float): carrier duty for the retransmission
	Outputs:
	    None
	"""
	if irReplay is None:
		print("   ECHO: irReplay.py is not on this rpi - send the plugin files to the rpis first")
		return
	pi = pigpio.pi()
	if not pi.connected:
		print("   ECHO: cannot reach pigpiod - nothing sent")
		return
	try:
		print("")
		print("   ECHO: this recording goes back out on gpio {} at {} Hz, duty {:.2f}".format(
				ledGpio, carrierHz, dutyCycle))
		print("   >>> NOW: press OFF on the remote, so the ac is NOT in the state above <<<")
		countdown(ECHOWAIT)
		took = irReplay.send(pi, ledGpio, pulses, carrierHz=carrierHz, dutyCycle=dutyCycle)
		print("   ECHO 1/2 RAW sent at {}: {} pulses, {:.1f} ms, in {:.3f} s  -  WATCH THE AC".format(
				time.strftime("%H:%M:%S"), len(pulses), sum(pulses) / 1000., took))
		print("   >>> press OFF again if it came on, the de-biased version follows <<<")
		countdown(ECHOGAP)
		fixed = deBias(pulses)
		took  = irReplay.send(pi, ledGpio, fixed, carrierHz=carrierHz, dutyCycle=dutyCycle)
		print("   ECHO 2/2 DE-BIASED sent at {} (marks -{} us, spaces +{} us): {:.1f} ms, in {:.3f} s".format(
				time.strftime("%H:%M:%S"), DEBIASUS, DEBIASUS, sum(fixed) / 1000., took))
		print("")
		print("   did the ac come back on, on either send?")
		print("      yes -> the emitter, the aim and the carrier are all fine, so what differs is")
		print("             the frame we BUILD - and the recording above says what it should be")
		print("      no  -> the frame was never the problem. The remote's own waveform out of our")
		print("             led does nothing, so it is the carrier frequency or the light itself")
		print("      (if the ac was left ON when the echo fired, this run says nothing - repeat it)")
	except Exception as e:
		print("   ECHO failed: {}".format(e))
	finally:
		try:	pi.stop()
		except Exception:	pass


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

	# A long space ends a BLOCK; a HEADER ends a message. Gree sends 32 bits, a 3 bit footer, a
	# ~20 ms gap, 32 more bits, and repeats the whole thing after ~40 ms - with a fresh header
	# each time. Splitting on gap LENGTH needs two different gaps to compare and fails on a
	# single message; splitting on the header is structural and works for one repeat or ten.
	frames  = []		# one entry per MESSAGE, each a list of blocks, each block a list of bits
	message = []
	bits    = []
	ii      = 2
	while ii < len(pulses):
		mark = pulses[ii]
		if ii + 1 >= len(pulses):
			break							# the trailing mark that closes a block, not a bit
		space = pulses[ii + 1]
		if mark > 3000:						# a new header: the previous message ended
			if bits:	message.append(bits); bits = []
			if message:	frames.append(message); message = []
			ii += 2
			continue
		if space > 3000:					# tail mark + a gap: this mark is the TAIL, not a bit,
			if bits:	message.append(bits); bits = []		# and the block it closed is done
			ii += 2
			continue
		bits.append(1 if space > split else 0)
		ii += 2
	if bits:	message.append(bits)
	if message:	frames.append(message)

	out = []
	for message in frames:
		blocks = []
		for bitList in message:
			blocks.append((msbFirst(bitList), lsbFirst(bitList), bitList))
		if blocks:
			out.append(blocks)
	return out, header


####-------------------------------------------------------------------------####
def msbFirst(bitList):
	"""The bits packed most significant first - toshiba and most others."""
	out = bytearray()
	for start in range(0, len(bitList) - 7, 8):
		byte = 0
		for bit in bitList[start:start + 8]:
			byte = (byte << 1) | bit
		out.append(byte)
	return out


####-------------------------------------------------------------------------####
def lsbFirst(bitList):
	"""The same bits packed LEAST significant first - gree, daikin and others send that way.

	Inputs:
	    bitList (list): the raw bits of one frame
	Outputs:
	    bytearray: the bytes read lsb first
	"""
	out = bytearray()
	for start in range(0, len(bitList) - 7, 8):
		byte = 0
		for jj, bit in enumerate(bitList[start:start + 8]):
			byte |= bit << jj
		out.append(byte)
	return out


####-------------------------------------------------------------------------####
def greeChecksum(state):
	"""Gree's block checksum: the low nibbles of bytes 0-3, the high nibbles of 4-6, plus 10.

	Inputs:
	    state (bytearray): the 8 byte state, blocks joined, lsb first
	Outputs:
	    int: the expected value of the high nibble of byte 7
	"""
	total = 10
	for ii in range(4):
		total += state[ii] & 0x0F
	for ii in range(4, 7):
		total += (state[ii] >> 4) & 0x0F
	return total & 0x0F


####-------------------------------------------------------------------------####
def describeGree(state):
	"""Reads a gree state and says what it means. Only the fields confirmed against a real
	remote are decoded - the rest of the 8 bytes carry timer, turbo, light, swing and so on,
	and are printed raw rather than guessed at.

	Inputs:
	    state (bytearray): 8 bytes, the two blocks joined, lsb first
	Outputs:
	    list: lines of text
	"""
	MODES = {0:"auto", 1:"cool", 2:"dry", 3:"fan", 4:"heat"}
	FANS  = {0:"auto", 1:"1 (low)", 2:"2 (med)", 3:"3 (high)"}
	lines = []
	if len(state) < 8:
		return ["      only {} bytes - a gree state is 8".format(len(state))]
	mode	= state[0] & 0x07
	power	= (state[0] >> 3) & 0x01
	fan		= (state[0] >> 4) & 0x03
	swingA	= (state[0] >> 6) & 0x01
	sleep	= (state[0] >> 7) & 0x01
	temp	= (state[1] & 0x0F) + 16
	want	= greeChecksum(state)
	got		= (state[7] >> 4) & 0x0F
	# in DRY mode byte1's low nibble is the humidity setting, not a temperature - calling it
	# "16 C" there is simply wrong
	if mode == 2:
		lines.append("      power {}   mode dry   HUMIDITY setting {} (byte1 low nibble, not a temperature)   fan {}".format(
						"ON" if power else "OFF", state[1] & 0x0F, FANS.get(fan, fan)))
		lines.append("      swing V {}  H {}   swing-auto {}   sleep {}   byte3 high nibble {}".format(
						state[4] & 0x0F, (state[4] >> 4) & 0x07, swingA, sleep, (state[3] >> 4) & 0x0F))
		lines.append("      turbo {}  light {}  health {}  xfan {}   (byte2 {:02X})".format(
						(state[2] >> 4) & 1, (state[2] >> 5) & 1, (state[2] >> 6) & 1, (state[2] >> 7) & 1, state[2]))
		want2 = greeChecksum(state)
		got2  = (state[7] >> 4) & 0x0F
		lines.append("      checksum {}".format("ok ({})".format(got2) if got2 == want2
						else "MISMATCH: frame says {}, computed {}".format(got2, want2)))
		return lines
	lines.append("      power {}   mode {}   temperature {} C   fan {}".format(
					"ON" if power else "OFF", MODES.get(mode, "{} (unknown)".format(mode)), temp, FANS.get(fan, fan)))
	MODENAME = MODES.get(mode, "{} - not one this encoder knows".format(mode))
	lines.append("      swing V {}  H {}   swing-auto {}   sleep {}   byte3 high nibble {}".format(
					state[4] & 0x0F, (state[4] >> 4) & 0x07, swingA, sleep, (state[3] >> 4) & 0x0F))
	lines.append("      turbo {}  light {}  health {}  xfan {}   (byte2 {:02X})".format(
					(state[2] >> 4) & 1, (state[2] >> 5) & 1, (state[2] >> 6) & 1, (state[2] >> 7) & 1, state[2]))
	lines.append("      checksum {}{}".format("ok ({})".format(got) if got == want
					else "MISMATCH: frame says {}, computed {}".format(got, want),
					"" if got == want else " - the reading above may be wrong"))
	return lines


####-------------------------------------------------------------------------####
def identify(header, blocks):
	"""Which protocol this recording looks like, from its shape alone.

	Inputs:
	    header (tuple): (mark, space) of the header, or None
	    blocks (list): the blocks of ONE message, as decode() returns them
	Outputs:
	    str: "toshiba", "gree" or ""
	"""
	if header is None or not blocks:
		return ""
	hm, hs = header
	nbits  = [len(b[2]) for b in blocks]
	# gree: 9000/4500 header, two blocks, the first with a 3 bit footer after 32 data bits
	if 7500 < hm < 10500 and 3500 < hs < 5500 and len(blocks) == 2 and nbits[0] >= 34 and nbits[1] >= 32:
		state = blocks[0][1][:4] + blocks[1][1][:4]
		# the CHECKSUM is the test, not byte 3. That nibble is "unknown1" in the reference and a
		# real remote was seen sending both 5 and 6 in it, with the checksum valid either way -
		# testing for 5 threw away good recordings.
		if len(state) == 8 and greeChecksum(state) == ((state[7] >> 4) & 0x0F):
			return "gree"
	# toshiba: 4400/4300 header, one block, F2 0D prefix
	if 3500 < hm < 5500 and 3500 < hs < 5500 and len(blocks) == 1:
		msb = blocks[0][0]
		if len(msb) >= 6 and msb[0] == 0xF2 and msb[1] == 0x0D:
			return "toshiba"
	return ""


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
	# the toshiba reading is an EXTRA, only offered when the frame actually is one. Recording any
	# other remote should report what was measured, not what it is not.
	if len(frame) < 6 or frame[0] != 0xF2 or frame[1] != 0x0D:
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
		diffM = abs(header[0] - REFERENCE["header mark"]) / float(REFERENCE["header mark"]) * 100.
		diffS = abs(header[1] - REFERENCE["header space"]) / float(REFERENCE["header space"]) * 100.
		if diffM < 20 and diffS < 20:
			print("        matches the toshiba header piBeacon sends ({} / {} us, {:.0f}% / {:.0f}% off)".format(
					REFERENCE["header mark"], REFERENCE["header space"], diffM, diffS))

	print("\n{} message(s):".format(len(frames)))
	if len(frames) > 1:
		# a remote sends the SAME message several times. When the decoded repeats disagree, the
		# receiver lost or invented bits in the later ones - its AGC settles differently after the
		# first burst. The FIRST message is the one to trust; the rest are shown for comparison.
		joined = []
		for blocks in frames:
			st = bytearray()
			for msb, lsb, bits in blocks:	st += lsb
			joined.append("".join("{:02X}".format(b) for b in st))
		same = len([j for j in joined if j == joined[0]])
		if same != len(joined):
			print("   NOTE: the {} repeats do not all decode the same ({} of {} match the first).".format(
					len(joined), same, len(joined)))
			print("         The remote sends them identically, so the differing ones are reception")
			print("         errors - trust message 1. When the corruption grows message by message")
			print("         and the last one decodes to near zeros, the receiver is saturating: its")
			print("         marks get longer and its spaces shorter until the long spaces that carry")
			print("         the 1 bits are eaten. Hold the remote 30-50 cm away instead of against")
			print("         the dome, and check the 100 ohm + 4.7 uF on VS - without them the supply")
			print("         sags under a strong signal and does the same thing.")
	for ii in range(len(frames)):
		blocks = frames[ii]
		print("   message {}: {} block(s)".format(ii + 1, len(blocks)))
		state = bytearray()
		for jj in range(len(blocks)):
			msb, lsb, bitList = blocks[jj]
			print("      block {}: {:3d} bits   msb {}   lsb {}".format(
					jj + 1, len(bitList),
					"".join("{:02X}".format(b) for b in msb),
					"".join("{:02X}".format(b) for b in lsb)))
			print("               bits {}".format("".join(str(b) for b in bitList)))
			state += lsb
		if len(blocks) > 1:
			# a multi block message is ONE state: the blocks joined, lsb first, which is how
			# gree and its relatives are laid out. Bits past the last whole byte of a block
			# (gree has a 3 bit footer) are not part of it.
			print("      state, blocks joined lsb first: {}".format(" ".join("{:02X}".format(b) for b in state)))

		what = identify(header, blocks)
		if what == "gree":
			print("      DETECTED: GREE message")
			for line in describeGree(blocks[0][1][:4] + blocks[1][1][:4]):
				print(line)
		elif what == "toshiba":
			print("      DETECTED: TOSHIBA message")
			for line in describe(blocks[0][0]):
				print(line)
		else:
			print("      DETECTED: no known protocol - header {}/{} us, {} block(s), {} bits".format(
					int(header[0]) if header else 0, int(header[1]) if header else 0,
					len(blocks), "+".join(str(len(b[2])) for b in blocks)))

	def printList(lst):
		line = "   "
		for ii in range(len(lst)):
			line += "{}, ".format(int(lst[ii]))
			if len(line) > 100:
				print(line)
				line = "   "
		if line.strip() != "":
			print(line)

	print("\nraw pulse list (paste this back to indigo/claude - mark, space, mark, space ...):")
	printList(pulses)

	# and the first message on its own. This is what a replay should send: the later repeats in a
	# capture are the ones that come back corrupted, and replaying them helps nothing
	one = firstMessage(pulses)
	print("\nfirst message only ({} of {} pulses, {:.1f} ms) - THIS is what to replay:".format(
			len(one), len(pulses), sum(one) / 1000.))
	printList(one)
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
	# what a byte MEANS depends on the protocol, and the two differ completely. 8 bytes with the
	# gree marker in byte 3 is a gree state; 9 or 10 with F2 0D is toshiba.
	isGree = (len(curr) == 8 and ((curr[3] >> 4) & 0x0F) == 5)
	out = []
	for ii in changed:
		what = ""
		if isGree:
			if   ii == 0:	what = "   mode / power / fan"
			elif ii == 1:	what = "   temperature {} -> {} C".format(16 + (prev[1] & 0x0F), 16 + (curr[1] & 0x0F))
			elif ii == 7:	what = "   checksum nibble, follows from the rest"
		else:
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
	ledGpio  = 0
	duty     = 0.5
	args     = sys.argv[1:]
	if args and args[0] in ("-h", "--help", "help"):
		print(USAGE)
		return 0
	if len(args) > 0:
		try:	gpio = int(args[0])
		except Exception:	pass
	if len(args) > 1:
		try:	waitSecs = float(args[1])
		except Exception:	pass
	if len(args) > 2:
		try:	count = max(1, min(10, int(args[2])))
		except Exception:	pass
	if len(args) > 3:
		try:	ledGpio = int(args[3])			# 0 = record only, the normal case
		except Exception:	pass
	if len(args) > 4:
		try:	duty = float(args[4])
		except Exception:	pass
	if duty < 0.1 or duty > 0.9:	duty = 0.5

	print("irRecord v{}  -  gpio {}, IR receiver output expected there".format(VERSION, gpio))
	if pigpio is None:
		print("ERROR: the pigpio module is not installed on this rpi")
		return 1
	if ledGpio > 0:
		if not (0 < ledGpio < 28):
			print("ERROR: {} is not a gpio number - the ir led goes on 1..27".format(ledGpio))
			return 1
		if ledGpio == gpio:
			print("ERROR: the ir led and the receiver cannot share gpio {}".format(gpio))
			return 1
		print("ECHO MODE: every recording is retransmitted on gpio {}, duty {:.2f},".format(ledGpio, duty))
		print("   once raw and once de-biased. Point the led at the ac. The run goes:")
		print("      1  record an ON command from the remote - the ac switches on, that is expected")
		print("      2  {:.0f} s pause: press OFF on the remote, the unit switches off".format(ECHOWAIT))
		print("      3  the recording goes back out through our led, still asking for ON")
		print("      4  {:.0f} s pause, then the same thing de-biased".format(ECHOGAP))
		print("   Only our led can turn the unit back on, so switching on IS the result.")
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
			if ledGpio > 0:	echo(ledGpio, pulses, dutyCycle=duty)
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
			blocks = frames[0]
			what   = identify(header, blocks)
			state  = bytearray()
			for msb, lsb, bits in blocks:	state += lsb
			print("      msb {}   lsb {}".format(
					"".join("{:02X}".format(x) for blk in blocks for x in blk[0]),
					"".join("{:02X}".format(x) for x in state)))
			if what == "gree":
				print("      DETECTED: GREE message")
				# EVERY message of the press, not just the first. One press is a sequence and the
				# question a sequence recording is usually asked is how the LATER messages follow
				# the command - reporting only message 1 hides exactly that
				if len(frames) > 1:
					for mm in range(len(frames)):
						blk = frames[mm]
						if len(blk) < 2:	continue
						one = blk[0][1][:4] + blk[1][1][:4]
						print("      msg{}  {}   index {:X}".format(
								mm + 1, " ".join("{:02X}".format(x) for x in one), one[3] >> 4))
				for line in describeGree(blocks[0][1][:4] + blocks[1][1][:4]):	print(line)
				frame = blocks[0][1][:4] + blocks[1][1][:4]
			elif what == "toshiba":
				print("      DETECTED: TOSHIBA message")
				for line in describe(blocks[0][0]):	print(line)
				frame = blocks[0][0]
			else:
				print("      DETECTED: no known protocol")
				frame = blocks[0][0]
			for line in diffFrames(prev, frame):
				print(line)
			if nn == 0:
				report(pulses)
			prev = frame
			if ledGpio > 0:	echo(ledGpio, pulses, dutyCycle=duty)

	if got > 1:
		print("\nrecorded {} presses. The bytes listed as CHANGED are the ones carrying whatever you".format(got))
		print("altered between presses - everything else is fixed for this remote.")
	return 0


if __name__ == "__main__":
	sys.exit(main())
