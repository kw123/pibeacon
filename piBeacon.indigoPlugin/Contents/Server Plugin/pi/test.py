#!/usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess


dprint ("start")

subprocess.call("sh /home/pi/pibeacon/forceReboot.sh &",shell=True)
