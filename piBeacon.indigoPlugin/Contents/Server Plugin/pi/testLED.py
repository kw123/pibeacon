#!/usr/bin/env python
# -*- coding: utf-8 -*-


import pigpio, time

PIGPIO = pigpio.pi()
print "enter pwmRange,freq eg 8000,100" 
inp = input()
if len(inp) !=2: exit()
pwmRange = int(inp[0])
freq 	 = int(inp[1])

pins = [26,19,13]
for pin in pins:
	PIGPIO.set_PWM_frequency(pin, freq)
	PIGPIO.set_PWM_range(pin, pwmRange)
	PIGPIO.set_PWM_dutycycle(pin, 0)

while True:
	print "enter r,b,g" 
	rgb = input()
	if len(rgb) != 3: continue
	print rgb
	for p in range(3):
		PIGPIO.set_PWM_dutycycle( pins[p], int(rgb[p]) )
