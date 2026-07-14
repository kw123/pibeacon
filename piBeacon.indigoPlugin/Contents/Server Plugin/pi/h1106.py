#!/usr/bin/env python


import bluetooth
import select

class MyDiscoverer(bluetooth.DeviceDiscoverer):

	def pre_inquiry(self):
		"""Bluetooth discovery callback invoked before an inquiry begins; resets the done flag to False so the scan can run.

		Inputs:
		    None.
		Outputs:
		    None: sets self.done to False
		"""
		self.done = False

	def device_discovered(self, address, device_class, name):
		"""Bluetooth discovery callback for each device found during inquiry; currently a no-op stub that ignores the discovered device.

		Inputs:
		    address (str): Bluetooth MAC address of the discovered device
		    device_class (int): Bluetooth class-of-device code
		    name (str): device friendly name
		Outputs:
		    None: no operation; returns immediately
		"""
		return 

	def inquiry_complete(self):
		"""Bluetooth discovery callback invoked when an inquiry finishes; sets the done flag to True to signal completion.

		Inputs:
		    None.
		Outputs:
		    None: sets self.done to True
		"""
		self.done = True

d = MyDiscoverer()
d.find_devices(lookup_names = True, duration =20)

readfiles = [ d, ]

while True:
	rfds = select.select( readfiles, [], [] )[0]

	if d in rfds:
		d.process_event()

	if d.done: break
