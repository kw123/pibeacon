#!/usr/bin/env python
# -*- coding: utf-8 -*-


import pigpio, time

PIGPIO = pigpio.pi()
print "enter pwmRange eg 8000" 
pwmRange = int(input())
print "enter freq eg 1000" 
freq = int(input())

for pin in [26,19,13]:
			PIGPIO.set_PWM_frequency(pin, freq)
			PIGPIO.set_PWM_range(pin, pwmRange)
			PIGPIO.set_PWM_dutycycle(pin, 0)
pins = [26,19,13]

while True:
	rgb = input()
	print rgb
	for p in range(3):
				PIGPIO.set_PWM_dutycycle( pins[p], int(pwmRange*float(rgb[p])/100.) )
