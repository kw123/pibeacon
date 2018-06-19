# pibeacon
this plugin can 
1. track ibeacons on multiple Raspberry Pis. 
2. BLE phone tracking
3. read many different types of sensors (temp, humidity. ADC, airquality, DOF, movement, ultarsound, microwave ...)
4. send output from the plugin to a variety of output devices, DOC, GPIO, displays etc 

Devices supported:  
   
supported device types:    
===RPI server   
rPI   
rPI-Sensor   
   
===iBeacon   
beacon   
   
===BLECONNECT for phones   
BLEconnect   
   
===BLE temp sensor    
BLEsensor   tenmp sensor through BLE
   
===Temp Pressure humidity, air quality ..
Wire18B20   
DHTxx   T,H
DHT11   T,H
TMP102   T
MCP9808  T
LM35A   T
T5403   T
MS5803 T
BMPxx   T,P
BMP280   T,H,P
SHT21   T
AM2320   T,H
BMExx    T,H,PP
bme680   T,H,P, VOC
pmairquality   measures concentration of particles in the air
sgp30   CO2
ccs811 Co2, VOC
MHZ-xxx serial and i2c  Infrared absoption CO2 measurement

   
===light: white, RGB infrared, ultraviolet ..    
TCS34725   
as726x   
IS1145   
OPT3001   
VEML7700   
VEML6030   
VEML6040   
VEML6070   
VEML6075   
TSL2561   
mlx90614   

===Lightning
as3935  frankling type sensor that detect lighning stickes  up to 30Km away. best is to use 2 to suppress miss identification of local electrical disturbances

===Infrared Camera    
amg88xx    8x8 infrared temperature camera
   
===Movements, gyroscopes, Magetometers   
l3g4200   
mag3110   
hmc5883L   
bno055   
mpu9255   
mpu6050   
lsm303   
   
===ADC    
ADC121   
ina219   
ina3221   
ADS1x15-1   
ADS1x15   
spiMCP3008   
spiMCP3008-1   
PCF8591-1   
PCF8591   
   
===Pulse sensors    
INPUTpulse   
   
===Capacitouch sensors   
INPUTtouch-1   
INPUTtouch-4   
INPUTtouch-12   
INPUTtouch-16   
   
GPIO inoputs    
INPUTgpio-1   
INPUTgpio-4   
INPUTgpio-8   
INPUTgpio-26   
   
===Distance, prximity    
ultrasoundDistance   
vl503l0xDistance   
vcnl4010Distance   
vl6180xDistance   
apds9960   
   
===special programs for you to design    
mysensors   
myprogram   
   
===GPIO outpu   
OUTPUTgpio-1-ONoff   
OUTPUTgpio-1   
OUTPUTgpio-4   
OUTPUTgpio-10   
OUTPUTgpio-26   
   
===Radio   
setTEA5767   
   
===DAC   
setMCP4725   
setPCF8591dac   
   
===various display types   
display   
neopixel   
neopixel-dimmer   
neopixelClock   
   
===sprinkler   
   
===car   
