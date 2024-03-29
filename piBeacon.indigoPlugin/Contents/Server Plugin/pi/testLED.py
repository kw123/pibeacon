#!/usr/bin/env python
# -*- coding: utf-8 -*-


import pigpio, time

PIGPIO = pigpio.pi()
inp = input()
if len(inp) !=2: exit()
pwmRange = int(inp[0])
freq 	 = int(inp[1])

pins = [22,19,13]
for pin in pins:
	PIGPIO.set_mode(pin, pigpio.OUTPUT)
	PIGPIO.set_PWM_frequency(pin, freq)
	PIGPIO.set_PWM_frequency(pin, freq)
	PIGPIO.set_PWM_range(pin, pwmRange)
	PIGPIO.set_PWM_dutycycle(pin, 0)

while True:
	rgb = input()
	if len(rgb) != 3: continue
	for p in range(3):
		PIGPIO.set_PWM_dutycycle( pins[p], int(rgb[p]) )
