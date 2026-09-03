#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# toshibaIR  version 1.1
#
# Encodes Toshiba air-conditioner IR remote frames and transmits them through an IR led
# on a gpio pin, using pigpio's hardware-timed waveforms for the 38 kHz carrier.
#
# Frame: 9 bytes / 72 bits, MSB first
#     F2 0D <cmd> <hdrChecksum>   <state 4 bytes>   <endByte>
# sent twice with a ~7.4 ms gap. Encoding follows the published Toshiba remote decoding
# (github.com/k3a/toshiba-ac), timings cross-checked against IRremoteESP8266 ir_Toshiba.cpp.
#
# py2 AND py3 compatible - like every other program in this directory, see
# checkForIncl-py2.py. No f-strings, no enum, no int.to_bytes.

import time

# imported once, at module load. Guarded so the encoder half of this file still works where there
# is no pigpio - the __main__ self test below runs on any machine, rpi or not.
try:
	import pigpio
except Exception:
	pigpio = None

VERSION = "1.1"

# ---- timings in microseconds --------------------------------------------------------
HDRMARK		= 4400
HDRSPACE	= 4300
BITMARK		= 580
ONESPACE	= 1600
ZEROSPACE	= 490
TAILMARK	= 580
GAP			= 7400		# inter-frame gap. a few remotes (WH-UB03NJ) use 4600 instead
CARRIERHZ	= 38000
REPEATS		= 2			# total number of transmissions, not extra ones

# pigpiod LIMITS, and why this file cares. One mark of the 38 kHz carrier is 2 pulses per 26 us,
# so a single 9 byte frame is ~3770 pulses and two of them ~7500.
#   CMD_MAX_EXTENSION (pigpio.h) = 1<<16 = 65536 bytes per socket command = 5461 pulses of 12
#     bytes. wave_add_generic sends the WHOLE list in one command, so one call with the complete
#     burst (~90 kB) is over the limit and pigpiod ANSWERS BY CLOSING THE SOCKET: the client sees
#     "ConnectionResetError 104" inside wave_add_generic, and every later command on that dead
#     socket dies with "BrokenPipeError 32" somewhere else entirely (live-seen as a set_mode
#     traceback). Successive wave_add_generic calls APPEND to the wave being built, so the fix is
#     to add the pulses in chunks.
#   PI_WAVE_MAX_PULSES = 12000 pulses per WAVE, whatever the chunking. Above that the frames are
#     sent as one wave each with the gap slept in software.
CHUNKPULSES		= 4000		# per wave_add_generic call, well under the 5461 the socket allows
MAXWAVEPULSES	= 11000		# per wave, headroom under pigpiod's 12000

MINTEMP		= 17
MAXTEMP		= 30
NOCHECKSUM	= 0x60

# ---- code tables. plain dicts, py2 has no enum ---------------------------------------
UNITS	= {"a":0, "b":1}
MODES	= {"auto":0, "cool":1, "dry":2, "heat":3, "off":7}
# fan: 0 = auto, then the five speeds as RAW 2..6. IRremoteESP8266 names its constants FanMin 1 /
# FanMed 3 / FanMax 5, which reads like 1..5 - but those are the USER scale, and its setFan()
# increments a non-auto speed before storing it. The published frame decodings agree: heat 21C
# fan 1 is F20D03FC 01404300 02, ie raw 2. Changed to 1..5 once and it broke both fan test
# vectors below, which is why the table says 2..6 and this comment exists.
FANS	= {"auto":0, "1":2, "2":3, "3":4, "4":5, "5":6}
SPECIALS= {"none":0, "hipower":1, "eco":3}

CMDFIXSWING		= 1
CMDMODEFANTEMP	= 3

# MESSAGE LENGTH. Toshiba ACs use the same timings and the same header for three message
# lengths - 7, 9 and 10 bytes (56/72/80 bits) - and a unit only answers the one ITS remote
# sends. Everything else being provably correct, this is the knob to turn when the AC ignores
# a well formed frame. Values checked against IRremoteESP8266 ir_Toshiba (kToshibaACStateLength
# 9, ...Short 7, ...Long 10) and its bitfield layout:
#   byte0/1   fixed F2 0D
#   byte2     low nibble = length - 6, high nibble = model (unit a=0, b=1)
#   byte3     ~byte2
#   byte4     0x01 base, bit3 = LongMsg (10 byte), bit5 = ShortMsg (7 byte)
#   byte5     bits 4-7 temperature - 17, bits 0-2 swing
#   byte6     bits 0-2 mode, bits 5-7 fan
#   byte7     bit 4 filter
#   byte8     eco/turbo, LONG message only
#   last byte XOR of every byte before it
# The 7 byte form has no room for mode/fan/temperature (byte 6 is already its checksum), so it
# is the swing/step message, not a state message.
MINLENGTH		= 6			# the length nibble in byte 2 counts from here
LENGTHNORMAL	= 9
LENGTHLONG		= 10
LENGTHSHORT		= 7
LENGTHS			= {"normal": LENGTHNORMAL, "long": LENGTHLONG}

BITLONGMSG		= 0x08
BITSHORTMSG		= 0x20
BYTE4BASE		= 0x01		# the bits every captured remote frame has set here

ECOTURBO		= {"none":0, "hipower":1, "eco":3}	# kToshibaAcTurboOn / kToshibaAcEconoOn

# BYTE 7, BIT 7. IRremoteESP8266 has byte 7 as ":4, Filter:1, :3" - bit 7 is padding there and its
# encoder leaves the whole byte at 0. A RECORDED Toshiba remote (RAS-xxG2KVP series, read with
# irRecord.py) sets it: for cool 18 C fan auto it sends
#     F2 0D 03 FC 01 10 01 80 90     while this file used to build
#     F2 0D 03 FC 01 10 01 00 10
# - the same frame except that bit, with the checksum following it (10 xor 80 = 90). An AC that
# checks the byte ignores the frame without it, which is exactly the symptom that led to the
# recording. Selectable, because the two published sources disagree and neither is wrong for
# every unit: "remote" = as the real remote sends it, "zero" = as IRremoteESP8266 builds it.
BYTE7		= {"remote": 0x80, "zero": 0x00}


####-------------------------------------------------------------------------####
def buildFrame(cmd, state, endByte):
	"""Assembles the 9 raw bytes of one Toshiba frame, including the header checksum.

	Inputs:
	    cmd (int): command byte, (unit << 4) | commandType
	    state (int): the 32 bit state word
	    endByte (int): trailing checksum / special-mode byte
	Outputs:
	    bytearray: the 9 bytes to transmit
	"""
	if cmd < 0 or cmd > 0xFF:
		raise ValueError("toshibaIR: cmd must be in [0, 0xFF], got:{}".format(cmd))
	prefix = 0xF20D0000 | ((cmd & 0xFF) << 8)
	prefix |= ((prefix >> 24) & 0xFF) ^ ((prefix >> 16) & 0xFF) ^ ((prefix >> 8) & 0xFF)

	frame = bytearray()
	for shift in (24, 16, 8, 0):
		frame.append((prefix >> shift) & 0xFF)
	for shift in (24, 16, 8, 0):
		frame.append((state >> shift) & 0xFF)
	frame.append(endByte & 0xFF)
	return frame


####-------------------------------------------------------------------------####
def modeFanTemp(mode="cool", temperature=22, fan="auto", special="none", unit="a",
				length="normal", swingPos=0, airFilter=0, byte7="remote"):
	"""The main remote command: hvac mode + fan speed + setpoint in ONE frame.

	The Toshiba remote has no separate on/off command - mode "off" IS the off command, and
	every other frame implicitly switches the unit on. So the plugin must always send the
	complete state, it cannot send "just the temperature".

	`length` picks the message FORM, not its content: "normal" is the 9 byte / 72 bit message,
	"long" the 10 byte / 80 bit one that carries the eco+turbo byte. Both say exactly the same
	thing about mode, fan and temperature - a unit simply answers the form its own remote uses,
	so this is what to try when a correctly built frame is ignored. eco/hipower need the long
	form: in the 9 byte message that byte IS the checksum.

	Inputs:
	    mode (str): auto / cool / dry / heat / off
	    temperature (int): setpoint in degrees celsius, 17..30
	    fan (str): auto / 1..5
	    special (str): none / hipower / eco - forces the long message
	    unit (str): a or b, for two ACs in range of one led
	    length (str): normal (9 byte) or long (10 byte)
	    swingPos (int): swing field of byte 5, 0 = leave alone
	    airFilter (int): filter bit of byte 7
	    byte7 (str): "remote" sets bit 7 of byte 7 the way a real remote does, "zero" leaves it 0
	                 the way IRremoteESP8266 does - see BYTE7 above
	Outputs:
	    bytearray: the 9 or 10 byte frame
	"""
	mode	= "{}".format(mode).strip().lower()
	fan		= "{}".format(fan).strip().lower()
	special	= "{}".format(special).strip().lower()
	unit	= "{}".format(unit).strip().lower()
	length	= "{}".format(length).strip().lower()

	if mode		not in MODES:		raise ValueError("toshibaIR: unknown mode:{}".format(mode))
	if fan		not in FANS:		raise ValueError("toshibaIR: unknown fan:{}".format(fan))
	if special	not in ECOTURBO:	raise ValueError("toshibaIR: unknown special mode:{}".format(special))
	if unit		not in UNITS:		raise ValueError("toshibaIR: unknown unit:{}".format(unit))
	if length	not in LENGTHS:		raise ValueError("toshibaIR: unknown message length:{}".format(length))
	byte7 = "{}".format(byte7).strip().lower()
	if byte7	not in BYTE7:		raise ValueError("toshibaIR: unknown byte7 style:{}".format(byte7))

	temperature = int(round(float(temperature)))
	if temperature < MINTEMP or temperature > MAXTEMP:
		raise ValueError("toshibaIR: temperature must be in [{}, {}], got:{}".format(MINTEMP, MAXTEMP, temperature))

	stateLength = LENGTHS[length]
	# eco and hipower live in byte 8, which only exists in the long message
	if ECOTURBO[special] != 0:	stateLength = LENGTHLONG

	raw		= bytearray(stateLength)
	raw[0]	= 0xF2
	raw[1]	= 0x0D
	raw[2]	= ((UNITS[unit] & 0x0F) << 4) | ((stateLength - MINLENGTH) & 0x0F)
	raw[3]	= (~raw[2]) & 0xFF
	raw[4]	= BYTE4BASE
	if stateLength == LENGTHLONG:	raw[4] |= BITLONGMSG
	if stateLength == LENGTHSHORT:	raw[4] |= BITSHORTMSG
	raw[5]	= (((temperature - MINTEMP) & 0x0F) << 4) | (int(swingPos) & 0x07)
	raw[6]	= (MODES[mode] & 0x07) | ((FANS[fan] & 0x07) << 5)
	raw[7]	= ((int(airFilter) & 0x01) << 4) | BYTE7[byte7]
	if stateLength >= LENGTHLONG:
		raw[8] = ECOTURBO[special] & 0xFF

	raw[stateLength - 1] = checksum(raw)
	return raw


####-------------------------------------------------------------------------####
def checksum(frame):
	"""XOR of every byte of `frame` except the last one - the trailing checksum byte.

	Inputs:
	    frame (bytearray): the frame, its last byte ignored
	Outputs:
	    int: the checksum byte
	"""
	out = 0
	for byte in bytearray(frame)[:-1]:
		out ^= byte
	return out & 0xFF


####-------------------------------------------------------------------------####
def swing(unit="a"):
	"""Frame that starts the louver swinging."""
	unit = "{}".format(unit).strip().lower()
	if unit not in UNITS: raise ValueError("toshibaIR: unknown unit:{}".format(unit))
	return buildFrame((UNITS[unit] << 4) | CMDFIXSWING, 0x21042500, NOCHECKSUM)


####-------------------------------------------------------------------------####
def fix(unit="a"):
	"""Frame that stops the louver at its current position."""
	unit = "{}".format(unit).strip().lower()
	if unit not in UNITS: raise ValueError("toshibaIR: unknown unit:{}".format(unit))
	return buildFrame((UNITS[unit] << 4) | CMDFIXSWING, 0x21002100, NOCHECKSUM)


####-------------------------------------------------------------------------####
def toPulses(frame):
	"""Turns a frame into the alternating mark/space durations of the IR burst.

	Inputs:
	    frame (bytearray): 9 bytes from modeFanTemp / swing / fix
	Outputs:
	    list: durations in microseconds, starting with a mark, ending with a mark
	"""
	pulses = [HDRMARK, HDRSPACE]
	for byte in bytearray(frame):
		for bit in range(7, -1, -1):
			pulses.append(BITMARK)
			if byte & (1 << bit):	pulses.append(ONESPACE)
			else:					pulses.append(ZEROSPACE)
	pulses.append(TAILMARK)
	return pulses


####-------------------------------------------------------------------------####
def frameToHex(frame):
	"""Readable "F20D03FC 01404300 02" form of a frame, for the log. Any length."""
	hexed = ""
	for byte in bytearray(frame):
		hexed += "{:02X}".format(byte)
	return "{} {} {}".format(hexed[0:8], hexed[8:16], hexed[16:]).strip()


####-------------------------------------------------------------------------####
def sendFrame(pigpioHandle, pin, frame, repeats=REPEATS, carrierHz=CARRIERHZ, dutyCycle=0.5, gap=GAP):
	"""Transmits one frame on `pin` as a pigpio waveform.

	pigpio, not gpiozero/RPi.GPIO: the carrier needs 13 us half-cycles held to a few
	microseconds over ~150 ms. Only pigpio's DMA waveforms do that while python is
	scheduled out - a software loop produces a burst the AC ignores.

	The waveform is built completely before it is sent, so the caller's timing does not
	matter; wave_send_once then runs it from DMA.

	Inputs:
	    pigpioHandle: a connected pigpio.pi(), from receiveCommands.getPigpio()
	    pin (int): BCM gpio number the IR led is on
	    frame (bytearray): 9 bytes to send
	    repeats (int): total transmissions, the remote itself sends 2
	    carrierHz (int): carrier frequency, 38000 for Toshiba
	    dutyCycle (float): carrier duty cycle, 0.5 is what the remote uses
	    gap (int): microseconds between repeats
	Outputs:
	    float: seconds the burst took on the wire
	"""
	if pigpio is None:
		raise IOError("toshibaIR: the pigpio module is not installed on this rpi")
	if pigpioHandle is None:
		raise IOError("toshibaIR: no pigpio connection - is pigpiod running?")

	pin			= int(pin)
	mask		= 1 << pin
	period		= 1000000. / float(carrierHz)
	onUsec		= int(round(period * dutyCycle))
	offUsec		= int(round(period)) - onUsec

	def markPulses(usec):
		out		= []
		elapsed	= 0.
		while elapsed < usec:
			out.append(pigpio.pulse(mask, 0, onUsec))
			out.append(pigpio.pulse(0, mask, offUsec))
			elapsed += period
		return out

	def spacePulses(usec):
		return [pigpio.pulse(0, mask, int(usec))]

	def sendPulses(pulseList):
		"""Builds ONE wave from pulseList and runs it to the end. Blocks until the DMA is done."""
		pigpioHandle.wave_add_new()
		# CHUNKED on purpose - see CHUNKPULSES above. One call with the whole list is bigger than
		# the socket command pigpiod accepts, and it answers by dropping the connection.
		for ii in range(0, len(pulseList), CHUNKPULSES):
			added = pigpioHandle.wave_add_generic(pulseList[ii:ii + CHUNKPULSES])
			if added < 0:
				raise IOError("toshibaIR: pigpio refused the pulses at {}/{}, error:{}".format(ii, len(pulseList), added))
		waveId = pigpioHandle.wave_create()
		if waveId < 0:
			raise IOError("toshibaIR: pigpio could not create the waveform, id:{}, pulses:{}".format(waveId, len(pulseList)))
		try:
			pigpioHandle.wave_send_once(waveId)
			# the wave runs from DMA; wait for it so the caller can release the pin afterwards
			while pigpioHandle.wave_tx_busy():
				time.sleep(0.002)
		finally:
			try:	pigpioHandle.wave_delete(waveId)
			except Exception:	pass

	pigpioHandle.set_mode(pin, pigpio.OUTPUT)
	pigpioHandle.write(pin, 0)

	oneFrame = []
	pulses   = toPulses(frame)
	for ii in range(len(pulses)):
		if ii % 2 == 0:	oneFrame += markPulses(pulses[ii])
		else:			oneFrame += spacePulses(pulses[ii])

	nRepeats = max(1, int(repeats))
	gapPulse = spacePulses(gap)

	start = time.time()
	try:
		if len(oneFrame) * nRepeats + len(gapPulse) * (nRepeats - 1) <= MAXWAVEPULSES:
			# the normal case (2 frames): ONE wave, so the gap between the frames is DMA timed
			waveform = []
			for n in range(nRepeats):
				waveform += oneFrame
				if n < nRepeats - 1:
					waveform += gapPulse
			sendPulses(waveform)
		else:
			# too many pulses for one wave: one wave per frame, gap slept in software. Less exact
			# than DMA, but the inter-frame gap is the one timing the receiver is relaxed about.
			for n in range(nRepeats):
				sendPulses(oneFrame)
				if n < nRepeats - 1:
					time.sleep(gap / 1000000.)
	finally:
		try:	pigpioHandle.write(pin, 0)
		except Exception:	pass
	return time.time() - start


####-------------------------------------------------------------------------####
def testBurst(pigpioHandle, pin, seconds=1.0, cycles=2, carrierHz=CARRIERHZ, dutyCycle=0.5):
	"""on / off / on / off with the 38 kHz carrier, `seconds` each - a VISIBLE hardware test.

	An ordinary command is a 0.17 s burst: far too short to see, and if nothing happens there is no
	way to tell whether the gpio pin, the transistor, the led or the AC is at fault. This drives the
	led for a whole second at a time, which shows up clearly as a flashing white/violet dot in the
	viewfinder of almost any phone camera (940 nm is invisible to the eye but not to the sensor).

	The CARRIER is used, not a steady DC level: it is what the led sees in normal operation, so the
	current through it is the same as during a real command instead of double. It also means a
	receiver module (TSOP38xxx) reacts to the test too, if one is at hand.

	pigpiod cannot hold a 1 s carrier in a single wave - that is ~76000 pulses against a 12000 pulse
	limit - so a short carrier wave is built once and sent in REPEAT mode, then stopped by the clock
	here. The wave loops in DMA, so the length of a phase is as accurate as time.sleep, and the
	carrier inside it stays hardware-timed.

	Inputs:
	    pigpioHandle: a connected pigpio.pi(), from receiveCommands.getPigpio()
	    pin (int): BCM gpio number the IR led is on
	    seconds (float): length of each on and each off phase
	    cycles (int): how many on/off pairs, 2 = on/off/on/off
	    carrierHz (int): carrier frequency, 38000 for Toshiba
	    dutyCycle (float): carrier duty cycle, 0.5 as in a real command
	Outputs:
	    float: seconds the whole test took
	"""
	if pigpio is None:
		raise IOError("toshibaIR: the pigpio module is not installed on this rpi")
	if pigpioHandle is None:
		raise IOError("toshibaIR: no pigpio connection - is pigpiod running?")

	pin		= int(pin)
	mask	= 1 << pin
	period	= 1000000. / float(carrierHz)
	onUsec	= int(round(period * dutyCycle))
	offUsec	= int(round(period)) - onUsec
	# clamped: the test holds the gpio pin and the IR lock while it runs, so it must stay short
	# whatever a hand-built command asks for. Worst case 5 cycles x 2 x 3 s = 30 s.
	seconds	= max(0.1, min(3., float(seconds)))
	cycles	= max(1, min(5, int(cycles)))

	# ~5 ms of carrier: long enough that the repeat has nothing to do with the timing, short
	# enough to stay far under every pigpiod limit (~380 pulses)
	block	= []
	elapsed	= 0.
	while elapsed < 5000.:
		block.append(pigpio.pulse(mask, 0, onUsec))
		block.append(pigpio.pulse(0, mask, offUsec))
		elapsed += period

	pigpioHandle.set_mode(pin, pigpio.OUTPUT)
	pigpioHandle.write(pin, 0)
	pigpioHandle.wave_add_new()
	added = pigpioHandle.wave_add_generic(block)
	if added < 0:
		raise IOError("toshibaIR: pigpio refused the test carrier, error:{}".format(added))
	waveId = pigpioHandle.wave_create()
	if waveId < 0:
		raise IOError("toshibaIR: pigpio could not create the test carrier, id:{}".format(waveId))

	start = time.time()
	try:
		for n in range(cycles):
			pigpioHandle.wave_send_repeat(waveId)
			time.sleep(seconds)
			pigpioHandle.wave_tx_stop()
			pigpioHandle.write(pin, 0)
			time.sleep(seconds)
	finally:
		try:	pigpioHandle.wave_tx_stop()
		except Exception:	pass
		try:	pigpioHandle.wave_delete(waveId)
		except Exception:	pass
		try:	pigpioHandle.write(pin, 0)
		except Exception:	pass
	return time.time() - start


####-------------------------------------------------------------------------####
if __name__ == "__main__":
	# encoder self test, runs anywhere - no pigpio and no rpi needed.
	# expected values are the published reference frames for this protocol.
	# the published decodings are all of the byte7=zero form, so they are checked that way. The
	# byte7="remote" form is checked against the frame irRecord.py read off a real RAS-G2KVP
	# remote - the two differ in exactly that bit and in the checksum that follows from it.
	tests = [
			(modeFanTemp("heat", 21, "1",    byte7="zero"),	"F20D03FC 01404300 02"),
			(modeFanTemp("off",  21, "1",    byte7="zero"),	"F20D03FC 01404700 06"),
			(modeFanTemp("cool", 23, "auto", byte7="zero"),	"F20D03FC 01600100 60"),
			(modeFanTemp("cool", 18, "auto", byte7="remote"),	"F20D03FC 01100180 90"),
			(fix(),								"F20D01FE 21002100 60"),
			(swing(),							"F20D01FE 21042500 60"),
			]
	bad = 0
	for frame, expected in tests:
		got = frameToHex(frame)
		if got != expected:
			bad += 1
			print("FAIL  expected:{}  got:{}".format(expected, got))
		else:
			print("ok    {}".format(got))
	nPulses = len(toPulses(modeFanTemp("heat", 21, "1")))
	if nPulses != 147:
		bad += 1
		print("FAIL  expected 147 pulses, got:{}".format(nPulses))
	else:
		print("ok    {} pulses per frame".format(nPulses))

	# the LONG (10 byte) form: same content, one byte more, and every field where the
	# 9 byte form has it. Checked structurally, there is no published vector for it.
	for kw, wantLen, wantByte2, wantByte4 in (
			({"byte7":"zero"},						9,  0x03, 0x01),
			({"length":"normal"},					9,  0x03, 0x01),
			({"length":"long"},						10, 0x04, 0x09),
			({"special":"eco"},						10, 0x04, 0x09),
			({"special":"hipower"},					10, 0x04, 0x09),
			({"unit":"b", "length":"long"},			10, 0x14, 0x09),
			):
		fr = modeFanTemp("cool", 20, "auto", **kw)
		ok = (len(fr) == wantLen and fr[2] == wantByte2 and fr[3] == ((~wantByte2) & 0xFF)
				and fr[4] == wantByte4 and fr[len(fr)-1] == checksum(fr))
		if not ok:
			bad += 1
			print("FAIL  {}: {}".format(kw, frameToHex(fr)))
		else:
			print("ok    {:32s} {:26s} {} bytes".format("{}".format(kw), frameToHex(fr), len(fr)))
	print("toshibaIR v{}: {}".format(VERSION, "ALL OK" if bad == 0 else "{} FAILURES".format(bad)))
