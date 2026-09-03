#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
# greeIR  version 1.1
#
# Encodes Gree air-conditioner IR remote frames and transmits them through an IR led on a gpio
# pin, using pigpio's hardware-timed waveforms for the 38 kHz carrier - the same transmitter
# toshibaIR.py uses, a completely different frame.
#
# THE FRAME, as recorded off a real Gree remote with irRecord.py (states below are measured, not
# taken from a datasheet):
#     header 9000 us mark / 4500 us space
#     BLOCK 1: 32 data bits, then a 3 bit footer 010
#     ~19980 us gap
#     BLOCK 2: 32 data bits
#     ~40 ms before the whole message repeats
#
# BITS ARE SENT LSB FIRST inside every byte - the opposite of toshiba. The 8 byte state:
#     byte0  bits0-2 mode, bit3 power, bits4-5 fan, bit6 swing-auto, bit7 sleep
#     byte1  bits0-3 temperature - 16 (16..30 C), bits4-7 timer
#            IN DRY MODE that nibble is the HUMIDITY setting, not a temperature: the humidity
#            button does nothing at all in cool mode (every capture came back identical) and in
#            dry mode it steps byte1 low nibble - recorded 6 <-> 0 with nothing else moving
#     byte2  bits0-3 timer hours, bit4 turbo, bit5 light, bit6 health, bit7 xfan
#            (the reference calls bit6 "ModelA"; on the recorded remote it is the HEALTH button -
#             every capture before it was pressed had byte2 = 0x20, after it 0x60)
#     byte3  bit2 extra degree F, bit3 use fahrenheit, bits4-7 fixed 0101
#     byte4  bits0-3 swing vertical, bits4-6 swing horizontal
#     byte5  bits0-1 display temp, bit2 ifeel, bit6 wifi
#     byte6  nothing
#     byte7  bit2 econo, bits4-7 checksum: low nibbles of bytes 0-3 + high nibbles of 4-6 + 10, & 0xF
#
# Every state below was RECORDED from the remote and every checksum verified; the self
# test at the bottom rebuilds each one byte for byte:
#     01 04 20 50 44 C0 00 F0   off,  cool, 20 C, fan auto, swing middle/middle
#     09 04 20 50 44 C0 00 70   on,   cool, 20 C, fan auto
#     19 04 20 50 44 C0 00 70   on,   cool, 20 C, fan 1
#     09 05 20 50 44 C0 00 80   on,   cool, 21 C, fan auto
#     21 05 20 50 44 C0 00 00   off,  cool, 21 C, fan 2
#     39 05 20 50 44 C0 00 80   on,   cool, 21 C, fan 3
#     1A 06 20 50 00 C0 00 60   on,   DRY,  22 C, fan 1, swing back to last-position/off
#     0B 09 20 50 00 C0 00 A0   on,   FAN only, 25 C
#     0C 03 20 50 55 C0 00 A0   on,   HEAT, 19 C, swing middle-down / right
#     0B 09 60 50 00 C0 00 A0   on,   fan only, 25 C, HEALTH pressed (byte2 20 -> 60)
#     9C 03 60 50 61 C0 00 B0   on,   heat, 19 C, SLEEP on - and the remote set fan 1 with it
#     0C 03 60 50 61 C0 00 B0   on,   the same with sleep off, fan back to auto
#
# py2 AND py3 compatible - like every other program in this directory, see checkForIncl-py2.py.
####################
from __future__ import print_function
import time

try:
	import pigpio
except Exception:
	pigpio = None

VERSION = "1.1"

# ---- timings in microseconds. The published values; a real remote measured 9100/4390/745/1562/463
# through a receiver that lengthens marks and shortens spaces by ~100 us, which is the same bias
# toshiba showed. Receivers accept +-20%, so the published numbers are what gets sent.
HDRMARK		= 9000
HDRSPACE	= 4500
BITMARK		= 620
ONESPACE	= 1600
ZEROSPACE	= 540
BLOCKGAP	= 19980		# between block 1 and block 2 of ONE message
MSGGAP		= 40000		# between repeats of the whole message
CARRIERHZ	= 38000		# 30000 was left here from the carrier hunt and it is what every caller
						# that does NOT pass a frequency was sending - receiveCommands included,
						# since the explicit carrier came out of the send path. The unit answers
						# at 38 kHz: "irTest.sh c 38000" passes it and works, irDemo relied on
						# this default and did nothing. Same frames, different carrier
REPEATS		= 1			# the remote sends the message once per press; raise only if commands get lost

BLOCKFOOTER	= [0, 1, 0]	# the 3 bits that close block 1
MARKER		= 0x05		# byte3 high nibble of the FIRST message. Not a constant marker, despite the
						# name: it is the MESSAGE INDEX inside one press. Every recording that
						# established it showed 0x50 only because every one was a first message
INDEXES		= [0x5, 0x6, 0x7, 0xA]
						# CORROBORATED: IRremoteESP8266 issue #1724 reaches the same reading from a
						# different remote - byte3's nibble is a PACKET NUMBER, 0x5 on the first
						# packet and 0x6 on the second, and the later packet carries different
						# content in bytes 4-6. It documents TWO packets, and only for the timer
						# button. Four packets on every press, stepping 5/6/7/A, is not in it or in
						# anything else published that we could find - so the sequence below is
						# measured here and nowhere else
						# one button press is FOUR messages, ~40 ms apart, and this ac ignores
						# anything less. Measured: one frame is ignored at every carrier from 26
						# to 40 kHz, four identical repeats of it are ignored too, and the first
						# two messages alone are ignored - only the whole sequence works
TERMINATOR	= 0xA		# the last message carries NO command: its first 28 bits are zero. It is
						# the same after every button, which is what makes it an end of
						# transmission marker rather than a command
						# byte 6 of message 3 is the real fan position - see FANS above. It
						# cannot be recovered from byte 0, which saturates, so buildSequence
						# takes the fan index it was built with
MINTEMP		= 16
MAXTEMP		= 30

# A plain number is accepted as a mode as well, for a unit that turns out to use a value this
# file has no name for. It is NOT a licence to guess: a "mode 6" seen twice in recordings - with
# a valid checksum both times - turned out to be a single bit error off heat (0x0C -> 0x0E), and
# the remote and the gree app both only ever show five modes. Gree's 4 bit checksum passes one
# corrupted frame in sixteen, so a state needs a CLEAN capture and a plausible reading, not just
# a checksum.
MODES	= {"auto":0, "cool":1, "dry":2, "fan":3, "heat":4, "econo":5}
# The remote's fan button cycles: silent, 1, 2, 3, 4, full, auto. That is FIVE speeds plus auto,
# and byte 0 only has TWO BITS for the fan - it saturates at 3. The real position lives in the
# high nibble of byte 6 of MESSAGE 3, which counts 8,9,A,B,C,D right through the cycle while
# byte 0 sticks at 3 for the top three speeds. Measured over a full cycle of ten presses.
# "full" is not a fan position at all: it is the turbo bit in byte 2, and pressing it left byte 6
# exactly where it was.
FANS	= {"auto":0, "silent":1, "1":2, "2":3, "3":4, "4":5}
BYTE6BASE	= 0x8	# byte6 high nibble of message 3 = this + the fan index
BYTE6FIXED	= 0xD0	# what message 3 carried before the fan cycle was measured
BYTE6FROMFAN	= True
					# WHICH ONE TO SEND. The measured answer is BYTE6BASE + the fan index: that is
					# what the remote does, ten presses of a full fan cycle say so, and the field
					# map agrees byte 6 is otherwise unused. The unit obeyed us with the FIXED
					# 0xD0 though - that was the state when "irTest.sh c 38000 6" worked - and it
					# stopped obeying after this became fan-dependent - but that was never the
					# reason: the walk that failed was transmitting at the wrong CARRIER, see
					# CARRIERHZ. With the carrier right, the unit answers, and its FAN does not
					# move while this is False - byte 0's two bits are not what it reads. So the
					# measured value is the correct one and True is the setting.

# swing vertical, byte 4 bits 0-3. "last" leaves the louver where it is, which is what a
# thermostat that only sets mode/temp/fan should do
SWINGV	= {"last":0x0, "auto":0x1, "up":0x2, "middleUp":0x3, "middle":0x4,
			"middleDown":0x5, "down":0x6, "downAuto":0x7}
# swing horizontal, byte 4 bits 4-6.
#
# LEFT AND RIGHT ARE THE VIEWER'S, verified at the unit: "maxLeft" sends the vane to the left as
# seen by someone FACING the ac. From the ac's own point of view - looking out into the room -
# that is its right, so the two frames of reference are mirrored. The names here follow the
# person, because that is who reads them in indigo.
SWINGH	= {"off":0x0, "auto":0x1, "maxLeft":0x2, "left":0x3, "middle":0x4,
			"right":0x5, "maxRight":0x6}

# byte 5 as the recorded remote sends it: the wifi bit and the spare top bit are BOTH set. The
# reference calls the top one padding, but toshiba taught us what a "spare" bit an AC actually
# checks costs - so what the real remote sends is what gets sent
BYTE5		= 0xC0


# THE FIELD MAP, cross-checked 2026-09-03 against the IRremoteESP8266 gree spreadsheet. Every
# field below was measured here first; the sheet agrees on all of them and named three we had
# not. Bit numbering is within each byte, block 2 following the 3 bit footer.
#
#   byte0  mode 0-2, power 3, fan 4-5, swingAuto 6, sleep 7
#   byte1  temperature 0-3, timer half-hour 4, timer tens 5-6, timer enabled 7
#   byte2  timer hours 0-3, turbo 4, light 5, "ModelA" 6, xfan 7
#          - bit 6 is what the health/ioniser button moves on THIS remote; the sheet calls it
#            ModelA, so the name is theirs and the behaviour is ours
#   byte3  unused 0-1, extra degree F 2, use fahrenheit 3, PACKET NUMBER 4-7
#          - the packet number is the "unkown1" of the sheet and the INDEXES above
#   footer the 3 bits the sheet calls "Marker" - our BLOCKFOOTER, 010
#   byte4  swingV 0-3, swingH 4-6, NOT USED 7
#          - swingH is 3 bits, not 4. Bit 7 carries nothing, which is why it wandered
#   byte5  displayTemp 0-1, iFeel 2, unknown 3-5, wifi 6, unknown 7
#          - our constant 0xC0 is those top two bits, and only the first packet carries them
#   byte6  NOT USED in the first packet - which is exactly why packet 7 is free to put the real
#          fan position there, see BYTE6BASE
#   byte7  unused 0-1, econo 2, unused 3, CHECKSUM 4-7
####-------------------------------------------------------------------------####
def checksum(state):
	"""Gree's checksum nibble: low nibbles of bytes 0-3, high nibbles of 4-6, plus 10.

	Inputs:
	    state (bytearray): the 8 byte state; byte 7 is ignored
	Outputs:
	    int: the value that belongs in the high nibble of byte 7
	"""
	total = 10
	for ii in range(4):
		total += state[ii] & 0x0F
	for ii in range(4, 7):
		total += (state[ii] >> 4) & 0x0F
	return total & 0x0F


####-------------------------------------------------------------------------####
def buildState(mode="cool", temperature=22, fan="auto", power=True, swingAuto=0, sleep=0,
				swingV="last", swingH="off", light=1, turbo=0, xfan=0, econo=0, health=0):
	"""The 8 byte Gree state. One frame carries everything, like toshiba - but gree has a real
	POWER bit, so switching off is power=False and the mode stays whatever it was.

	Inputs:
	    mode (str): auto / cool / dry / fan / heat
	    temperature (int): setpoint in degrees celsius, 16..30
	    fan (str): auto / 1 / 2 / 3
	    power (bool): True switches the unit on, False off
	    swingAuto (int): swing-auto bit of byte 0. INDEPENDENT of swingV, however much it looks
	                  otherwise: the UD button set SwingV 1 and this bit together (byte0 0C -> 4C),
	                  but the LR presses that followed kept SwingV 1 with the bit CLEAR. Tying
	                  them to each other was wrong on one capture and the next four disproved it.
	    sleep (int): sleep bit of byte 0
	    swingV (str): louver position, "last" leaves it alone - see SWINGV
	    swingH (str): horizontal louver, "off" leaves it alone - see SWINGH
	    light (int): the display light on the indoor unit, the recorded remote sends it ON
	    turbo (int), xfan (int), econo (int): the matching bits, off by default
	    health (int): the health / ioniser button, byte 2 bit 6
	Outputs:
	    bytearray: the 8 byte state, checksum included
	"""
	mode = "{}".format(mode).strip().lower()
	fan  = "{}".format(fan).strip().lower()
	if mode in MODES:
		modeVal = MODES[mode]
	else:
		try:	modeVal = int(mode)			# a raw number, for a mode this file has no name for
		except Exception:	raise ValueError("greeIR: unknown mode:{}".format(mode))
		if modeVal < 0 or modeVal > 7:
			raise ValueError("greeIR: mode must fit in 3 bits, got:{}".format(modeVal))
	if fan  not in FANS:	raise ValueError("greeIR: unknown fan:{}".format(fan))

	temperature = int(round(float(temperature)))
	if temperature < MINTEMP or temperature > MAXTEMP:
		raise ValueError("greeIR: temperature must be in [{}, {}], got:{}".format(MINTEMP, MAXTEMP, temperature))

	state = bytearray(8)
	state[0] = ((modeVal & 0x07)
				| ((1 if power else 0) << 3)
				| ((min(FANS[fan], 3) & 0x03) << 4)		# byte 0 saturates at 3, see FANS
				| ((int(swingAuto) & 0x01) << 6)
				| ((int(sleep) & 0x01) << 7))
	state[1] = (temperature - MINTEMP) & 0x0F
	state[2] = (((int(turbo) & 1) << 4) | ((int(light) & 1) << 5)
				| ((int(health) & 1) << 6) | ((int(xfan) & 1) << 7))
	state[3] = (MARKER << 4)
	state[4] = ((SWINGV.get("{}".format(swingV).strip(), 0) & 0x0F)
				| ((SWINGH.get("{}".format(swingH).strip(), 0) & 0x07) << 4))
	state[5] = BYTE5
	state[6] = 0x00
	state[7] = ((int(econo) & 1) << 2) | (checksum(state) << 4)
	return state


####-------------------------------------------------------------------------####
def stateToBits(state):
	"""The state as the two blocks of bits that go on the wire, LSB first per byte.

	Inputs:
	    state (bytearray): the 8 byte state
	Outputs:
	    list: [block1 bits (32 data + 3 footer), block2 bits (32)]
	"""
	def bitsOf(chunk):
		out = []
		for byte in bytearray(chunk):
			for jj in range(8):
				out.append((byte >> jj) & 1)		# LSB first
		return out
	return [bitsOf(state[0:4]) + list(BLOCKFOOTER), bitsOf(state[4:8])]


####-------------------------------------------------------------------------####
def toPulses(state, blockGap=BLOCKGAP):
	"""Turns a state into the alternating mark/space durations of the whole IR message.

	Inputs:
	    state (bytearray): the 8 byte state
	    blockGap (int): microseconds between block 1 and block 2
	Outputs:
	    list: durations in microseconds, starting with a mark, ending with a mark
	"""
	blocks = stateToBits(state)
	pulses = [HDRMARK, HDRSPACE]
	for nn in range(len(blocks)):
		for bit in blocks[nn]:
			pulses.append(BITMARK)
			pulses.append(ONESPACE if bit else ZEROSPACE)
		# the mark that closes a block, then the gap - except after the last block, where the
		# closing mark simply ends the message
		if nn < len(blocks) - 1:
			pulses.append(BITMARK)
			pulses.append(blockGap)
	pulses.append(BITMARK)
	return pulses


####-------------------------------------------------------------------------####
def stateToHex(state):
	"""Readable "09 04 20 50 44 C0 00 70" form of a state, for the log."""
	return " ".join("{:02X}".format(b) for b in bytearray(state))


####-------------------------------------------------------------------------####
def buildSequence(state, fan=None):
	"""Returns the FOUR messages this remote sends for one button press.

	The unit does not act on a single frame. What the remote sends is a sequence: the state, two
	continuation messages carrying the command bytes and nothing else, and a terminator carrying
	no command at all. They are told apart by byte3's high nibble - the message index - stepping
	5, 6, 7, A. Messages 1-3 share their first 28 bits exactly; only the index and the second
	block differ.

	Measured from the remote, one press of power-off / cool / 20 C / fan 3:
	    31 04 20 50 44 C0 00 F0     index 5, the full state
	    31 04 20 60 00 00 00 F0     index 6, bytes 0-2 only
	    31 04 20 70 00 00 D0 C0     index 7, bytes 0-2 and byte 6
	    00 00 00 A8 00 00 00 20     index A, no command at all
	All four verify against checksum(), which is what says they are frames and not noise.

	Held over five more presses covering a temperature step, a turbo step, a fan step and a
	louver step: messages 2 and 3 carry bytes 0-2 and nothing else of the command - byte 4, the
	louvers, stays in message 1 even when it is what changed - the terminator never varies, and
	byte 6 of message 3 follows the fan.

	Inputs:
	    state (bytearray): the 8 byte state from buildState()
	    fan (str or int): the fan the state was built with. NEEDED: byte 6 of message 3 carries
	                      the real fan position and byte 0 saturates at 3, so the top three
	                      speeds cannot be told apart from the state alone. Left out, the lowest
	                      position consistent with byte 0 is used
	Outputs:
	    list: four bytearrays, in the order they go out
	"""
	first = bytearray(state)

	second = bytearray(8)
	second[0:3] = first[0:3]				# the command bytes, unchanged
	second[3]   = (INDEXES[1] << 4)
	second[7]   = checksum(second) << 4

	third = bytearray(8)
	third[0:3] = first[0:3]
	third[3]   = (INDEXES[2] << 4)
	if fan is None:		fanIndex = (first[0] >> 4) & 0x03
	elif fan in FANS:	fanIndex = FANS[fan]
	else:
		try:	fanIndex = max(0, min(5, int(fan)))
		except Exception:	fanIndex = (first[0] >> 4) & 0x03
	if BYTE6FROMFAN:	third[6] = ((BYTE6BASE + fanIndex) & 0x0F) << 4
	else:				third[6] = BYTE6FIXED
	third[7]   = checksum(third) << 4

	last = bytearray(8)
	last[3] = (TERMINATOR << 4) | 0x08		# 0xA8: index A, and the low nibble the remote sets
	last[7] = checksum(last) << 4

	return [first, second, third, last]


####-------------------------------------------------------------------------####
def sendSequence(pigpioHandle, pin, state, fan=None, carrierHz=CARRIERHZ, dutyCycle=0.5,
					blockGap=BLOCKGAP, msgGap=MSGGAP):
	"""Sends one button press: all four messages, one wave each, msgGap between them.

	Inputs:
	    pigpioHandle (pigpio.pi): connected client
	    pin (int): gpio the ir led driver is on
	    state (bytearray): the state to command
	    fan (str or int): the fan it was built with - see buildSequence
	    carrierHz (int), dutyCycle (float): carrier
	    blockGap (int), msgGap (int): microseconds
	Outputs:
	    float: seconds the whole press took
	"""
	start = time.time()
	msgs  = buildSequence(state, fan=fan)
	for nn in range(len(msgs)):
		sendState(pigpioHandle, pin, msgs[nn], repeats=1, carrierHz=carrierHz,
					dutyCycle=dutyCycle, blockGap=blockGap, msgGap=msgGap)
		if nn < len(msgs) - 1:
			time.sleep(msgGap / 1000000.)
	return time.time() - start


####-------------------------------------------------------------------------####
def sendState(pigpioHandle, pin, state, repeats=REPEATS, carrierHz=CARRIERHZ, dutyCycle=0.5,
				blockGap=BLOCKGAP, msgGap=MSGGAP):
	"""Transmits a state on `pin` as a pigpio waveform.

	ONE MESSAGE = ONE WAVE = ONE wave_add_generic CALL. pigpio builds a wave by absolute time
	offset, so a second call does not continue where the first ended, it starts at time 0 and
	MERGES - splitting a burst across calls silently ORs the pieces together. See the long note
	in toshibaIR.py; it cost an evening there.

	Inputs:
	    pigpioHandle: a connected pigpio.pi()
	    pin (int): BCM gpio number the IR led is on
	    state (bytearray): the 8 byte state
	    repeats (int): how often the whole message is sent
	    carrierHz (int): carrier frequency, 38000
	    dutyCycle (float): carrier duty cycle
	    blockGap (int): microseconds between the two blocks
	    msgGap (int): microseconds between repeats
	Outputs:
	    float: seconds the burst took on the wire
	"""
	if pigpio is None:
		raise IOError("greeIR: the pigpio module is not installed on this rpi")
	if pigpioHandle is None:
		raise IOError("greeIR: no pigpio connection - is pigpiod running?")

	pin		= int(pin)
	mask	= 1 << pin
	period	= 1000000. / float(carrierHz)
	onUsec	= int(round(period * dutyCycle))
	offUsec	= int(round(period)) - onUsec
	MAXSOCKETPULSES = 5400		# 65536 byte socket command / 12 bytes per pulse, with a margin

	def markPulses(usec):
		out		= []
		elapsed	= 0.
		while elapsed < usec:
			out.append(pigpio.pulse(mask, 0, onUsec))
			out.append(pigpio.pulse(0, mask, offUsec))
			elapsed += period
		return out

	pulses = toPulses(state, blockGap=blockGap)
	wave   = []
	for ii in range(len(pulses)):
		if ii % 2 == 0:	wave += markPulses(pulses[ii])
		else:			wave += [pigpio.pulse(0, mask, int(pulses[ii]))]

	if len(wave) > MAXSOCKETPULSES:
		raise IOError("greeIR: {} pulses is more than one wave can take ({})".format(len(wave), MAXSOCKETPULSES))

	pigpioHandle.set_mode(pin, pigpio.OUTPUT)
	pigpioHandle.write(pin, 0)

	start = time.time()
	try:
		for nn in range(max(1, int(repeats))):
			pigpioHandle.wave_add_new()
			added = pigpioHandle.wave_add_generic(wave)
			if added < 0:
				raise IOError("greeIR: pigpio refused {} pulses, error:{}".format(len(wave), added))
			waveId = pigpioHandle.wave_create()
			if waveId < 0:
				raise IOError("greeIR: could not create the waveform, id:{}".format(waveId))
			doneAt = time.time()		# bound before the try: the gap calculation below reads it
			try:
				pigpioHandle.wave_send_once(waveId)
				while pigpioHandle.wave_tx_busy():
					time.sleep(0.002)
				doneAt = time.time()
			finally:
				try:	pigpioHandle.wave_delete(waveId)
				except Exception:	pass
			if nn < int(repeats) - 1:
				# the gap is measured from the END of the burst, but wave_delete and the socket
				# round trip have already eaten part of it. Sleeping the full msgGap on top made
				# the measured spacing 56 ms where the remote sends 40 ms - close the difference
				# instead of adding to it
				rest = msgGap / 1000000. - (time.time() - doneAt)
				if rest > 0:	time.sleep(rest)
	finally:
		try:	pigpioHandle.write(pin, 0)
		except Exception:	pass
	return time.time() - start


####-------------------------------------------------------------------------####
if __name__ == "__main__":
	# self test against the states RECORDED from a real remote - no datasheet involved
	MID = dict(swingV="middle", swingH="middle")	# what the remote had the louvers set to
	# NOTE the fan names here are the REMOTE's, not the old ones: byte 0's fan field saturates at
	# 3, so the 1/2/3 it shows are the remote's silent/1/2. See FANS.
	tests = [
			(dict(mode="cool", temperature=20, fan="auto", power=False, **MID),	"01 04 20 50 44 C0 00 F0"),
			(dict(mode="cool", temperature=20, fan="auto", power=True,  **MID),	"09 04 20 50 44 C0 00 70"),
			(dict(mode="cool", temperature=20, fan="silent",    power=True,  **MID),	"19 04 20 50 44 C0 00 70"),
			(dict(mode="cool", temperature=21, fan="auto", power=True,  **MID),	"09 05 20 50 44 C0 00 80"),
			(dict(mode="cool", temperature=21, fan="1",    power=False, **MID),	"21 05 20 50 44 C0 00 00"),
			(dict(mode="cool", temperature=21, fan="2",    power=True,  **MID),	"39 05 20 50 44 C0 00 80"),
			(dict(mode="dry",  temperature=22, fan="silent",    power=True),			"1A 06 20 50 00 C0 00 60"),
			# the clean mode run: fan-only, heat, and the mode 6 this remote cycles onto
			(dict(mode="fan",  temperature=25, fan="auto", power=True),			"0B 09 20 50 00 C0 00 A0"),
			(dict(mode="heat", temperature=19, fan="auto", power=True,
					swingV="middleDown", swingH="right"),						"0C 03 20 50 55 C0 00 A0"),
			# health pressed: byte2 bit 6 on, everything else as the fan-only state above
			(dict(mode="fan",  temperature=25, fan="auto", power=True, health=1),	"0B 09 60 50 00 C0 00 A0"),
			# the UD swing button, walking the vertical louver. "auto" sets SwingV 1 AND the
			# swing-auto bit in byte 0 - the remote sends them together
			(dict(mode="heat", temperature=19, fan="auto", power=True, health=1,
					swingV="down",     swingH="right"),							"0C 03 60 50 56 C0 00 A0"),
			(dict(mode="heat", temperature=19, fan="auto", power=True, health=1,
					swingV="middleUp", swingH="right"),							"0C 03 60 50 53 C0 00 A0"),
			(dict(mode="heat", temperature=19, fan="auto", power=True, health=1,
					swingV="auto",     swingH="right", swingAuto=1),			"4C 03 60 50 51 C0 00 A0"),
			# the LR button, walking the horizontal louver - and note swingV stays 1 while the
			# swing-auto bit in byte 0 is CLEAR, which is what proves the two are independent
			(dict(mode="heat", temperature=19, fan="auto", power=True, health=1,
					swingV="auto",     swingH="maxRight", swingAuto=1),			"4C 03 60 50 61 C0 00 B0"),
			(dict(mode="heat", temperature=19, fan="auto", power=True, health=1,
					swingV="auto",     swingH="off"),							"0C 03 60 50 01 C0 00 50"),
			(dict(mode="heat", temperature=19, fan="auto", power=True, health=1,
					swingV="auto",     swingH="maxLeft"),						"0C 03 60 50 21 C0 00 70"),
			(dict(mode="heat", temperature=19, fan="auto", power=True, health=1,
					swingV="auto",     swingH="middle"),						"0C 03 60 50 41 C0 00 90"),
			# the sleep button: byte0 bit 7. The remote moves the FAN with it - sleep on took the
			# fan to 1, sleep off put it back to auto, both in the same press
			(dict(mode="heat", temperature=19, fan="silent",    power=True, health=1,
					swingV="auto",     swingH="maxRight", sleep=1),				"9C 03 60 50 61 C0 00 B0"),
			(dict(mode="heat", temperature=19, fan="auto", power=True, health=1,
					swingV="auto",     swingH="maxRight"),						"0C 03 60 50 61 C0 00 B0"),
			# the humidity button, in DRY mode - it steps byte1's low nibble, the one that is a
			# temperature in every other mode. In cool mode the same button sends nothing new.
			(dict(mode="dry",  temperature=22, fan="silent", power=True, health=1),	"1A 06 60 50 00 C0 00 60"),
			(dict(mode="dry",  temperature=16, fan="silent", power=True, health=1),	"1A 00 60 50 00 C0 00 00"),
			# cool, fan 3, both louvers middle - the state the humidity button would not change
			(dict(mode="cool", temperature=21, fan="2", power=True, health=1,
					swingV="middle",   swingH="middle"),						"39 05 60 50 44 C0 00 80"),
			]
	bad = 0
	for kw, expected in tests:
		got = stateToHex(buildState(**kw))
		if got != expected:
			bad += 1
			print("FAIL  {}\n      expected:{}\n      got     :{}".format(kw, expected, got))
		else:
			print("ok    {}   {}".format(got, kw))

	# the FOUR MESSAGE SEQUENCE, against the press recorded from the remote. The unit ignores a
	# single frame and ignores four identical repeats of one; only this sequence drives it
	sequences = [
			# power off, cool, 20 C, fan 3, louvers middle
			(dict(mode="cool", temperature=20, fan="4", power=False,
					swingV="middle", swingH="middle"),
				["31 04 20 50 44 C0 00 F0", "31 04 20 60 00 00 00 F0",
				 "31 04 20 70 00 00 D0 C0", "00 00 00 A8 00 00 00 20"]),
			# on, cool, 20 C, fan 3, health on - byte6 D0 because the fan is 3
			(dict(mode="cool", temperature=20, fan="4", power=True, health=1,
					swingV="middle", swingH="middle"),
				["39 04 60 50 44 C0 00 70", "39 04 60 60 00 00 00 70",
				 "39 04 60 70 00 00 D0 40", "00 00 00 A8 00 00 00 20"]),
			# the same at 21 C, to show only byte1 and the checksums move
			(dict(mode="cool", temperature=21, fan="4", power=True, health=1,
					swingV="middle", swingH="middle"),
				["39 05 60 50 44 C0 00 80", "39 05 60 60 00 00 00 80",
				 "39 05 60 70 00 00 D0 50", "00 00 00 A8 00 00 00 20"]),
			# fan auto - byte6 of message 3 drops to 80, which is what says it follows the fan
			(dict(mode="cool", temperature=21, fan="auto", power=True, health=1,
					swingV="middle", swingH="middle"),
				["09 05 60 50 44 C0 00 80", "09 05 60 60 00 00 00 80",
				 "09 05 60 70 00 00 80 00", "00 00 00 A8 00 00 00 20"]),
			# louver stepped up: byte4 45 in message 1 and NOWHERE else
			(dict(mode="cool", temperature=21, fan="auto", power=True, health=1,
					swingV="middleDown", swingH="middle"),
				["09 05 60 50 45 C0 00 80", "09 05 60 60 00 00 00 80",
				 "09 05 60 70 00 00 80 00", "00 00 00 A8 00 00 00 20"]),
			# THE FAN CYCLE, one press per step, louvers at swingV 6. byte 0's fan field sticks
			# at 3 from "2" upwards while byte 6 of message 3 keeps counting - that is the whole
			# reason the fan needs its own argument
			(dict(mode="cool", temperature=21, fan="silent", power=True, health=1,
					swingV="down", swingH="middle"),
				["19 05 60 50 46 C0 00 80", "19 05 60 60 00 00 00 80",
				 "19 05 60 70 00 00 90 10", "00 00 00 A8 00 00 00 20"]),
			(dict(mode="cool", temperature=21, fan="1", power=True, health=1,
					swingV="down", swingH="middle"),
				["29 05 60 50 46 C0 00 80", "29 05 60 60 00 00 00 80",
				 "29 05 60 70 00 00 A0 20", "00 00 00 A8 00 00 00 20"]),
			(dict(mode="cool", temperature=21, fan="2", power=True, health=1,
					swingV="down", swingH="middle"),
				["39 05 60 50 46 C0 00 80", "39 05 60 60 00 00 00 80",
				 "39 05 60 70 00 00 B0 30", "00 00 00 A8 00 00 00 20"]),
			(dict(mode="cool", temperature=21, fan="3", power=True, health=1,
					swingV="down", swingH="middle"),
				["39 05 60 50 46 C0 00 80", "39 05 60 60 00 00 00 80",
				 "39 05 60 70 00 00 C0 40", "00 00 00 A8 00 00 00 20"]),
			(dict(mode="cool", temperature=21, fan="4", power=True, health=1,
					swingV="down", swingH="middle"),
				["39 05 60 50 46 C0 00 80", "39 05 60 60 00 00 00 80",
				 "39 05 60 70 00 00 D0 50", "00 00 00 A8 00 00 00 20"]),
			# "full" is the TURBO bit, not a fan position - it left byte 6 at D0 where it was
			(dict(mode="cool", temperature=21, fan="4", power=True, health=1, turbo=1,
					swingV="down", swingH="middle"),
				["39 05 70 50 46 C0 00 80", "39 05 70 60 00 00 00 80",
				 "39 05 70 70 00 00 D0 50", "00 00 00 A8 00 00 00 20"]),
			# and auto, which drops byte 6 back to 80
			(dict(mode="cool", temperature=21, fan="auto", power=True, health=1,
					swingV="down", swingH="middle"),
				["09 05 60 50 46 C0 00 80", "09 05 60 60 00 00 00 80",
				 "09 05 60 70 00 00 80 00", "00 00 00 A8 00 00 00 20"]),
			]
	# RESOLVED: byte 4 bit 7 came back set on three presses of ten and clear on the other seven,
	# with the checksum agreeing either way, and nothing visible decided it. The IRremoteESP8266
	# field map settles it - that bit is NOT USED. SwingH is only THREE bits (byte 4 bits 4-6),
	# not the nibble it looks like, so bit 7 carries nothing and may sit either way. Sending 0 is
	# right and the variation was never a signal.
	for kw, want in sequences:
		got = [stateToHex(m) for m in buildSequence(buildState(**kw), fan=kw.get("fan", "auto"))]
		check = list(want)
		if not BYTE6FROMFAN:
			# message 3 carries the fixed byte 6 instead of the measured one, and its checksum
			# follows - so compare those two bytes against what the encoder should now produce and
			# leave the other six asserted against the recording
			g3 = got[2].split()
			w3 = check[2].split()
			w3[6], w3[7] = g3[6], g3[7]
			check[2] = " ".join(w3)
		if got != check:
			bad += 1
			print("FAIL  sequence {}\n      expected:{}\n      got     :{}".format(kw, check, got))
		else:
			print("ok    sequence {}".format(" / ".join(got)))
	if not BYTE6FROMFAN:
		print("note  BYTE6FROMFAN is False: message 3 carries the fixed {:02X}, not the measured".format(BYTE6FIXED))
		print("      per-fan value. Every other byte is still checked against the recordings.")

	st = buildState("cool", 20, "auto", True)
	p  = toPulses(st)
	nBits = len(stateToBits(st)[0]) + len(stateToBits(st)[1])
	if nBits != 67:
		bad += 1
		print("FAIL  expected 67 bits (32+3+32), got:{}".format(nBits))
	else:
		print("ok    {} bits: 32 data + 3 footer + 32 data".format(nBits))
	print("ok    one message: {} pulses, {:.1f} ms".format(len(p), sum(p) / 1000.))
	print("greeIR v{}: {}".format(VERSION, "ALL OK" if bad == 0 else "{} FAILURES".format(bad)))
