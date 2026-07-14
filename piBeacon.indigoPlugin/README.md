# piBeacon

Indigo plugin that uses Raspberry Pis to track iBeacons / BLE devices and to read a wide range of
sensors attached to the Pis. The Pis report to the Indigo server over the network; the plugin manages
device states, triggers, and the sensor programs running on each Pi.

- **Current version:** 2022.191.171 (2026-07-13) — maintenance releases .169–.171: fixed format-string
  errors in log messages, undefined-variable (NameError) bugs, missing imports, and removed all
  Python-2 leftovers (u"" prefixes, unicode(), raw_input, long) across plugin.py and the pi/ sensor
  programs. No new features. See `Contents/changelist.txt` for the full history.
- **Author:** Karl Wachs
- **Forum / support:** http://forums.indigodomo.com/viewforum.php?f=164

## Setup

Setup is automatic. All you need is a working Raspberry Pi on the network with a known IP number
(and its login credentials). Enter the IP in the plugin's setup menu ("Initial BASIC setup of rPi
servers") — the plugin connects via SSH/FTP and pushes everything to the rPi: all program files,
required libraries, and the configuration. It creates the Indigo devices and keeps the rPi's files
up to date automatically after plugin upgrades. Whenever you change sensors or outputs in Indigo,
the updated config and any needed files are pushed to the rPi again — no manual editing on the Pi
is required.

**Note:** if you replace the plugin bundle in Indigo's Plugins folder manually or via a sync tool
(instead of double-clicking the .indigoPlugin, which does this for you), always **reload the plugin
in Indigo afterwards**. A running plugin whose folder was replaced underneath it keeps working, but
every command it spawns logs harmless `shell-init: getcwd` warnings until it is restarted.

## How the communication works

```
                             INDIGO SERVER (Mac)
   +-------------------------------------------------------------------+
   |   Indigo  <------------->  plugin.py (piBeacon)                   |
   |   devices, states,          - creates/updates Indigo devices      |
   |   triggers, actions         - listens on a TCP socket for Pi data |
   |                             - sends config/commands to the Pis    |
   +---------------+------------------------------^--------------------+
                   |                              |
     config, files, commands, programs       sensor data, beacon reports,
     via  SSH / FTP / TCP socket             status (JSON via TCP socket)
                   |                              |
        +----------+---------------+--------------+------+
        v          v               v                     v
   +---------+ +---------+    +---------+          +---------+
   | RPi #0  | | RPi #1  |    | RPi #2  |   ...    | RPi #n  |
   +----+----+ +---------+    +---------+          +---------+
        |
        |  master.py - supervisor: starts/watches all programs below
        |  receiveCommands.py - executes commands from the Indigo server
        |  beaconloop.py / BLEconnect.py - BLE scanning + GATT connections
        |  one program per sensor type (e.g. bme680.py, INPUTgpio.py, ...)
        |  output programs (display.py, neopixel3.py, setStepperMotor.py, ...)
        |
        +-- i2c / SPI / GPIO / 1-wire / serial -->  wired sensors & outputs
        |
        +-- BLE dongle(s) <~~~ BLE advertisements ~~~<  iBeacons, BLE sensors,
                          ~~~> GATT connections    ~~~>  switchbot devices

   Beacon tracking: every Pi reports RSSI per beacon; the plugin combines the
   reports, estimates distance, sets the beacon device to up/down, tracks the
   "closest rPi", and drives the home/away group triggers.
```

## Supported iBeacon types

Any tag that broadcasts standard **iBeacon / Eddystone** advertisements works. The file
`Contents/beaconTypes.txt` contains a detailed comparison (form factor, battery, beep support,
battery-level reporting). Highlights:

- **Musegear iTrack (EU)** — top pick: beep, battery reading, button press detectable; regular / mini / card
- Rechargeable with beep + battery: Nonda Aiko, Nonda iHere, Smart Tracker
- CR2032 with beep + battery: NutFind 3 / Nutale / Nut Pro, Vozni iTrack, SpotyPal, Rinex / Njoii iTrack
- Beep, no battery reading: Innway Tag / Chip / Card, Cube, Orbit, Safedome (card)
- Beacon + sensor combos: ruuviTag (T/H/P/accel), myBlueT (temp)
- Pure iBeacon/Eddystone: BlueCharm BC011, MiniBeacon, Feasy (USB + triangle), SocialRetail, Radius,
  and most generic ~$5 iBeacon tags
- Fun extras: anything that advertises — e.g. Tovala oven, Oral-B toothbrush
- Not recommended: Tile (post-2018), XY4, swiftFind/ZenLife, iSearching-type tags

The plugin can auto-accept new beacons, beep beacons that support it, read battery levels, and
track cars (dedicated *Car* device with per-car beacon assignment).

## Supported BLE sensors (no pairing — data via broadcast or GATT)

Reaction time for buttons is < 0.4 s; battery friendly. Full details in `Contents/BLE-sensorTypes.txt`.

- **ruuvi**: RuuviTag (T/H/P/accel), RuuviAir (T/H/P/CO2…)
- **INGICS iBS01/02/03/04**: on/off button, magnet contact, IR/PIR motion, temp, probe temp, XYZ accel
- **Xiaomi MiJia**: LYWSD02 clock, LYWSDCGQ round, LYWSD03MMC square, formaldehyde MJHFD1,
  VegTrug / Flower Care (moisture + conductivity)
- **switchbot**: temp/hum, temp/hum/CO2, humidifier, mm-wave motion (occupancy), motion, contact,
  remote button (WoBtn) — can be beeped to locate it
- **Minew**: E8 (XYZ accel), S1 (temp/hum), S1 Plus (accel + T/H)
- **Kaipule iSensor**: on/off, magnet, water, PIR, temp/hum, 4-button remote key fob
- **Shelly**: door, button, motion
- **Govee** temp/hum (H5101/H5075/H5177/H5174), **ThermoBeacon**, **Thermopro**, **InkBird Pool 01B**,
  **TempSpike** meat thermometer, **april Brother** ABN01/ABN03, **blueradio SensorBug**,
  **Satech STixx**, **iTrack / Musegear button**, **Hunter Node BT**, **meeblue**, **myBlueT**
- **BLE-connect**: generic GATT connect device for sensors that need an active connection

## Supported wired sensors (INPUT devices on the Pi)

**Temperature / pressure / humidity**
1-wire DS18B20, DHT, tmp117, TMP102, MCP9808, LM75A/LM35, T5403, MS5803, BMPxx/BMP280, BMP388,
SHT21, AM2320, BME280, BME680 (+air quality), si7021, max31865 (platinum RTD),
tmp006/tmp007 + mlx90614 (remote infrared)

**Air quality / gas**
particulate matter (PM) sensor, sgp30 (CO2/VOC), scd30, scd40 (CO2/T/H), sgp40 (VOC),
MH-Zxx CO2 (i2c + serial), ccs811 (CO2/VOC)

**Light / color / UV**
TCS34725 (lux+RGB), MAX44009, as726x (spectral), OPT3001, VEML7700, VEML6030, VEML6040 (RGBW),
VEML6070 (UV), VEML6075 (UVA/UVB), TSL2561 (ambient+IR)

**Distance / proximity / imaging**
ultrasound, VL53L0X / VL53L1X (time-of-flight), vcnl4010, vl6180 (TOF+lux), apds9960 (proximity),
amg88xx + mlx90640 (IR cameras), 360° lidar

**Motion / orientation**
l3g4200/l3gd20h gyro, mag3110 + hmc5883L (3-axis), lsm303 + mpu6050 (6-axis),
BNO055 + mpu9255 (9-axis)

**Analog (ADC) / power**
ADC121, ina219 + ina3221 (V/A metering), MCP3008 (SPI 8×10bit), ADS1115, PCF8591

**GPIO & switches**
GPIO inputs (1/4/8/26 pins), pulse counter, coincidence detector, touch pads (1/4/12/16),
rotary switch (absolute + incremental)

**Other**
DF2301Q voice recognition, face-gesture sensor, RG11 rain sensor, moisture sensor,
as3935 lightning detector

**Custom**: `mysensors.py` / `myprogram.py` device types run your own code on the Pi;
`SPECIAL-launchpgm.py` starts/supervises any external program.

## Outputs

- **GPIO**: on/off pin, dimmer (PWM)
- **Relays**: i2c relay boards, switchbot bot (press/pulse), switchbot curtain (incl. v3s)
- **Analog / DAC**: MCP4725 (12-bit), PCF8591 (8-bit)
- **Displays**: LCD/OLED/e-ink displays (`display.py`, incl. extra pages sent from Indigo),
  xWindows output, distance display
- **LEDs**: NeoPixel strips/matrices, NeoPixel dimmer, NeoPixel clock, sundial clock
- **Motion**: stepper motors
- **Misc**: FM radio TEA5767, sprinkler controller, garage door, sound playback on the Pi,
  `myoutput.py` for custom output code

## Actions (Indigo action groups / scripts)

- **Pi management**: send config via FTP or socket, reboot / shutdown via SSH or socket
  (incl. hard variants), stop/refresh NTP, set Pi time, send arbitrary unix command,
  play sound file, restart plugin
- **Sensors**: pause / reset / restart a sensor device, request fresh data, calibrate sensors,
  reset GPIO/touch/pulse counters
- **Outputs**: set GPIO pin high/low, set i2c relay, switchbot relay / curtain,
  set DAC value (MCP4725 / PCF8591), FM radio tuning, NeoPixel pixels, display text/graphs,
  extra display pages, stepper motor commands, send text to `myoutput.py`
- **Beacons**: get battery level (one/all), beep a beacon (incl. the SwitchBot remote button)
- **Device utilities**: set/get any device property, set any device state

A parallel set of interactive **menu items** covers setup (create/config/replace Pis, fix IP or
duplicate Pi numbers), beacon management (accept/ignore, replace, battery, beep, fast
beacon→switchbot actions), diagnostics (track MACs, special logging, print configs), and output
testing.

## Trigger events

- Group presence: **Family / Guests / Other1 / Other2 / Other3** × **allHome / oneHome / allAway /
  oneAway** (20 combinations)
- **someStatusHasChanged** — any beacon changed up/down
- **someClosestrPiHasChanged** — any beacon's closest-Pi changed (room-level tracking)

## Layout

- `Contents/Server Plugin/plugin.py` — the Indigo server plugin
- `Contents/Server Plugin/pi/` — programs deployed to and run on the Raspberry Pis
  (`master.py` supervises; one program per sensor type)
- `Contents/changelist.txt` — version history
- `Contents/beaconTypes.txt` — beacon hardware comparison
- `Contents/BLE-sensorTypes.txt` — BLE sensor hardware details
