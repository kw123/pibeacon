#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

# rrb3.py Library

import RPi.GPIO as GPIO
import time


class RRB3:

	MOTOR_DELAY = 0.2
	stepsBits =[[1, 0, 1, 0],[1, 0, 1, 1],[1, 1, 1, 1],[1, 1, 1, 0]]

	RIGHT_PWM_PIN = 14
	RIGHT_1_PIN = 10
	RIGHT_2_PIN = 25
	LEFT_PWM_PIN = 24
	LEFT_1_PIN = 17
	LEFT_2_PIN = 4
	SW1_PIN = 11
	SW2_PIN = 9
	LED1_PIN = 8
	LED2_PIN = 7
	OC1_PIN = 22
	OC2_PIN = 27
	OC2_PIN_R1 = 21
	OC2_PIN_R2 = 27
	TRIGGER_PIN = 18
	ECHO_PIN = 23
	left_pwm = 0
	right_pwm = 0
	pwm_scale = 0

	old_left_dir = -1
	old_right_dir = -1

	def __init__(self, battery_voltage=9.0, motor_voltage=6.0, revision=2):

		self.pwm_scale = float(motor_voltage) / float(battery_voltage)

		if self.pwm_scale > 1:
			print("WARNING: Motor voltage is higher than battery votage. Motor may run slow.")

		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)

		GPIO.setup(self.LEFT_PWM_PIN, GPIO.OUT)
		self.left_pwm = GPIO.PWM(self.LEFT_PWM_PIN, 500)
		self.left_pwm.start(0)
		GPIO.setup(self.LEFT_1_PIN, GPIO.OUT)
		GPIO.setup(self.LEFT_2_PIN, GPIO.OUT)

		GPIO.setup(self.RIGHT_PWM_PIN, GPIO.OUT)
		self.right_pwm = GPIO.PWM(self.RIGHT_PWM_PIN, 500)
		self.right_pwm.start(0)
		GPIO.setup(self.RIGHT_1_PIN, GPIO.OUT)
		GPIO.setup(self.RIGHT_2_PIN, GPIO.OUT)

		GPIO.setup(self.LED1_PIN, GPIO.OUT)
		GPIO.setup(self.LED2_PIN, GPIO.OUT)

		GPIO.setup(self.OC1_PIN, GPIO.OUT)
		if revision == 1:
			self.OC2_PIN = self.OC2_PIN_R1
		else:
			self.OC2_PIN = self.OC2_PIN_R2

		GPIO.setup(self.OC2_PIN_R2, GPIO.OUT)

		GPIO.setup(self.SW1_PIN, GPIO.IN)
		GPIO.setup(self.SW2_PIN, GPIO.IN)
		GPIO.setup(self.TRIGGER_PIN, GPIO.OUT)
		GPIO.setup(self.ECHO_PIN, GPIO.IN)
		self.lastStep = 0

	def set_motors(self, left_pwm, left_dir, right_pwm, right_dir):
		if self.old_left_dir != left_dir or self.old_right_dir != right_dir:
			self.set_driver_pins([0, 0, 0, 0])	# stop motors between sudden changes of direction
			time.sleep(self.MOTOR_DELAY)
		self.set_driver_pins([left_pwm, left_dir, right_pwm, right_dir])
		self.old_left_dir = left_dir
		self.old_right_dir = right_dir

	def set_driver_pins(self, p, scale =1.):
		left_pwm = p[0]; left_dir = p[1]; right_pwm = p[2]; right_dir = p[3]
		self.left_pwm.ChangeDutyCycle(left_pwm * 100 * self.pwm_scale*scale)
		GPIO.output(self.LEFT_1_PIN, left_dir)
		GPIO.output(self.LEFT_2_PIN, not left_dir)
		self.right_pwm.ChangeDutyCycle(right_pwm * 100 * self.pwm_scale*scale)
		GPIO.output(self.RIGHT_1_PIN, right_dir)
		GPIO.output(self.RIGHT_2_PIN, not right_dir)

	def forward(self, seconds=0, speed=1.0):
		self.set_motors(speed, 0, speed, 0)
		if seconds > 0:
			time.sleep(seconds)
			self.stop()

	def stop(self):
		self.set_motors(0, 0, 0, 0)

	def reverse(self, seconds=0, speed=1.0):
		self.set_motors(speed, 1, speed, 1)
		if seconds > 0:
			time.sleep(seconds)
			self.stop()

	def left(self, seconds=0, speed=0.5):
		self.set_motors(speed, 0, speed, 1)
		if seconds > 0:
			time.sleep(seconds)
			self.stop()

	def right(self, seconds=0, speed=0.5):
		self.set_motors(speed, 1, speed, 0)
		if seconds > 0:
			time.sleep(seconds)
			self.stop()

	def step_forward(self, delay, num_steps):
		i =  self.lastStep
		for n in range(num_steps):
			#self.set_driver_pins(self.stepsBits[i][0],self.stepsBits[i][1],self.stepsBits[i][2],self.stepsBits[i][3])
			#time.sleep(0.1)
			i -= 1
			if i<0: i=3
			for ii in range(8,10):
				self.set_driver_pins(self.stepsBits[i],scale = 1)
				time.sleep(0.005)
			for ii in range(10,8,-1):
				self.set_driver_pins(self.stepsBits[i],scale = 1 )
				time.sleep(0.005)
			#self.set_driver_pins([0, 0, 0, 0],0.)#
			time.sleep(delay)
		self.set_driver_pins([0, 0, 0, 0],0.)
		self.lastStep = i

	def step_reverse(self, delay, num_steps):
		i =  self.lastStep
		for n in range( num_steps):
			#self.set_driver_pins(self.stepsBits[i][0],self.stepsBits[i][1],self.stepsBits[i][2],self.stepsBits[i][3])
			#time.sleep(0.1)
			i+=1
			if i>3: i=0
			for ii in range(9,10):
				self.set_driver_pins(self.stepsBits[i],scale = 1 )
				time.sleep(0.005)
			for ii in range(10,8,-1):
				self.set_driver_pins(self.stepsBits[i],scale = 1 )
				time.sleep(0.005)
			#self.set_driver_pins([0, 0, 0, 0],0.)
			time.sleep(delay)
		self.set_driver_pins([0, 0, 0, 0],0.)
		self.lastStep = i

	def sw1_closed(self):
		return not GPIO.input(self.SW1_PIN)

	def sw2_closed(self):
		return not GPIO.input(self.SW2_PIN)

	def set_led1(self, state):
		GPIO.output(self.LED1_PIN, state)

	def set_led2(self, state):
		GPIO.output(self.LED2_PIN, state)

	def set_oc1(self, state):
		GPIO.output(self.OC1_PIN, state)

	def set_oc2(self, state):
		GPIO.output(self.OC2_PIN, state)

	def _send_trigger_pulse(self):
		GPIO.output(self.TRIGGER_PIN, True)
		time.sleep(0.0001)
		GPIO.output(self.TRIGGER_PIN, False)

	def _wait_for_echo(self, value, timeout):
		count = timeout
		while GPIO.input(self.ECHO_PIN) != value and count > 0:
			count -= 1

	def get_distance(self):
		self._send_trigger_pulse()
		self._wait_for_echo(True, 10000)
		start = time.time()
		self._wait_for_echo(False, 10000)
		finish = time.time()
		pulse_len = finish - start
		distance_cm = pulse_len / 0.000058
		return distance_cm

	def cleanup(self):
		GPIO.cleanup()

import time
rr=RRB3(battery_voltage=12.0, motor_voltage=12.0, revision=2) # battery, motor

try: 
	while True:
		delay = raw_input("Delay (milliseconds)?")
		stepsf = raw_input("How many steps forward? ")
		stepsb = raw_input("How many steps backwards? ")
		rr.step_forward(int(delay) / 1000.0, int(stepsf))
		rr.step_reverse(int(delay) / 1000.0, int(stepsb))

finally:
	GPIO.cleanup()