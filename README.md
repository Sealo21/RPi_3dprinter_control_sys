# RPi_3dprinter_control_sys
Environment controller for a 3D printing enclosure using a Raspberry Pi. \
Uses a temperature/VOC sensor and a custom PCB controller for the fans and strip LEDs controlled by a Raspberry Pi. \
This project is a work-in-progress. It is functional...but still a beta.

# Components
  - Raspberry Pi 4 Model B  
  - [Sensirion Particle, VOC, Humidity, and Temperature Sensor](https://www.sparkfun.com/products/23715)  
  - [waveshare 4 inch HDMI LCD 800x480](https://www.amazon.com/gp/product/B07P5H2315/)  
  - [Geekworm GPIO Extender](https://www.amazon.com/gp/product/B0BDF48FWM/)  
  - [SamIdea 2-Pack 40pin Male to Female IDC GPIO](https://www.amazon.com/gp/product/B07CGM83QL/)  
  - [Micro HDMI Cable](https://www.sparkfun.com/products/15796)  
  - Any 2 or 4 pin PC fan [I am using Noctua NF-A8 PWM](https://noctua.at/en/nf-a8-pwm)  
  - Any SMD5050 strip LED [LED Strip Lights](https://www.amazon.com/gp/product/B08JSQVBDQ/)

# Software Installation

[Install the latest version of Raspian OS](https://projects.raspberrypi.org/en/projects/raspberry-pi-setting-up) on your Raspberry Pi \
[Edit your configuration](https://www.raspberrypi.com/documentation/computers/configuration.html) to enable 'I2C' and 'Remote GPIO' under the interfaces tab \
Save and restart your RPi 

Update packages to the latest version:
```command line
sudo apt update
```

1. Download the files marked "RPi_3dprinter_control_sys_main" 
2. Locate the file 'main' in the folder 'dist' 
3. Edit the properties of 'main' to open with the program 'Terminal' 
4. Set the permission "Execute" to 'Anyone' 
5. If you run the program without modifying these settings a pop-up may occur asking to run the executable with an application 
6. Once these settings are confirmed the program should start with a terminal followed by a window

# Hardware Setup

A GPIO Extender will be needed to have the screen and GPIO be plugged in at the same time. 

There are a few options for the hardware of your controller \
A cheap option is to breadboard the design using the design schematics from the file 'LED_FAN_CONTROLLER.kicad_sch' \
You may need to download and install Kicad to view this schematic.

Here are the design requirements to breadboard this project:
- 4 [IRL520](https://www.digikey.com/en/products/detail/vishay-siliconix/IRL520PBF/811718) Mosfets as a substitute for the [IRLL014TRPBF](https://www.digikey.com/en/products/detail/vishay-siliconix/IRLL014TRPBF/811425)
- Wire for connections
- 6 10k Ohm resistors
- 5 1k Ohm resistors
- In testing phase for 3.3V power controller for breadboarding. I have been testing using an ADALM2000
- Using [TC74HC04APF](https://www.digikey.com/en/products/detail/toshiba-semiconductor-and-storage/TC74HC04APF/870457) for PWM operations in breadboard testing

<img src="https://github.com/Sealo21/RPi_3dprinter_control_sys/blob/main/images/schematics.png" width="500" />


The other option is to use the PCB schematics and manufacture the PCB. \
I have not done this yet as I am working on an upgrade to the current version.

# Touchscreen

Your experience may change based on which touchscreen is used. \
Use xinput-calibrator to calibrate the touch screen. 


```
sudo apt-get install xinput-calibrator
```
You will find this program under Menu -> Preferences -> Calibrate Touchscreen. \
Follow the instuctions given in the command line to save the calibration.

If the system does not recognize the touchscreen, check with the manufacturer for driver files. 

# Installing the Sen55 Sensor

The sensors I recieved do not have a standard coloring scheme. \
I have made a table below to list where the pins must go and their color.

<img src="https://github.com/Sealo21/RPi_3dprinter_control_sys/blob/main/images/GPIO-Pinout-Diagram.png" width="750" />
<img src="https://github.com/Sealo21/RPi_3dprinter_control_sys/blob/main/images/SEN5X_pinout.png" width="500" />

|  Pin (On Sensor) |  Name    |  Description    |  Color  |  Pin Placement (On RPi)  |
| ---------------- |:--------:|:-----------------:|:-------:|:------------------------:|
|  1               |  VCC     | Supply Voltage  | Green   |  Pin 2 (5V)              |
|  2               |  GND     | Ground          | Blue    |  Pin 6 (GND)             |
|  3               |  SDA     | I2C: Data       | Yellow  |  Pin 3 (SDA)             |
|  4               |  SCL     | I2C: Clock      | Black   |  Pin 5 (SCL)             |
|  5               |  SEL     | Interface Select| Red     |  Pin 9 (GND)             |
|  6               |  NC      | Do Not Connect  | Brown   |  NC                      |

If the device is not recognized by the system, connect the VCC to 3.3V pin and then back to 5V. \
The device can function on both 3.3V and 5V but 5V is recommended by the manufacturer. \
Use the i2cdetect command to check connected I2C devices.

```command line
i2cdetect -y 1
```

You should see a device listed with a number value.

More information about this installation can be found [here](https://github.com/Sensirion/raspberry-pi-i2c-sen5x)
