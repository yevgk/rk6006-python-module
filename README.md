# Riden RK6006 simple Python module

Very simple Python module for accessing the Riden RK6006 DC-DC module through the Micro USB port and the on-board CH340 USB to UART converter.
As with previous models, the RK6006 uses the Modbus protocol over serial, the registers however are different than the RD and DPS models.

Based on https://github.com/Baldanos/rd6006

RD6006 registries, very similar to RK6006 registries: https://github.com/Baldanos/rd6006/blob/master/registers.md

In RK6006 there are no Battery Charging and Time/Date - these registers are always set to 0.

CH340 drivers: https://www.wch-ic.com/downloads/CH341SER_ZIP.html

Needed Python modules:

pySerial: https://pyserial.readthedocs.io/en/latest/pyserial.html

MinimalModbus: https://minimalmodbus.readthedocs.io/en/stable/readme.html

This module allows to read and control the following options:
 - Switch ON/OFF the output and read the state;
 - V&A set and read Voltage and Current;
 - Output read Voltage, Current and Power;
 - OVP and OCP set and read Voltage and Current;
 - Read the output Capacity(in Ah) and Energy(in Wh) from the switching-on of the module;
 - Read the Internal and External temperature in Celsius and Fahrenheit;
 - Read the Protection Status: Normal, OVP, OCP;
 - Read CV/CC output mode: CV, CC;
 - Switch ON/OFF the Take Out option and read the state;
 - Switch ON/OFF the Boot Power option and read the state;
 - Switch ON/OFF the Buzzer and read the state.

For usage see the example file.

CLI usage:

```bash
python rk6006_cli.py --port COM3 info
python rk6006_cli.py --port COM3 status
python rk6006_cli.py --port COM3 set --set_voltage 12 --set_current 1.5
python rk6006_cli.py --port COM3 on --set_voltage 12 --set_current 1.5
python rk6006_cli.py --port COM3 off --set_current 0.5
python rk6006_cli.py --port COM3 sample --count 10 --interval 0.5
python rk6006_cli.py --port COM3 sample --duration 30 --csv
```

If `--port` is omitted, the CLI tries to use the first CH340 USB serial adapter
(`VID:PID=1A86:7523`). Use `--baudrate`, `--address`, and `--timeout` if the
module settings differ from the defaults.

Tested with Python 3.11.
