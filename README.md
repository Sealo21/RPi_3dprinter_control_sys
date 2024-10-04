# RPi_3dprinter_control_sys
Environment controller for a 3D printing enclosure using a Raspberry Pi \
Uses a temperature/VOC sensor and a custom PCB controller for the fans and strip LEDs controlled by a Raspberry Pi \
This project is a work-in-progress. It is functional...but still a beta.

# Components
  - Raspberry Pi 4 Model B  
  - [Sensirion Particle, VOC, Humidity, and Temperature Sensor](https://www.sparkfun.com/products/23715)  
  - [waveshare 4 inch HDMI LCD 800x480](https://www.amazon.com/gp/product/B07P5H2315/)  
  - [Geekworm GPIO Extender](https://www.amazon.com/gp/product/B0BDF48FWM/)  
  - [SamIdea 2-Pack 40pin Male to Female IDC GPIO](https://www.amazon.com/gp/product/B07CGM83QL/)  
  - [Micro HDMI Cable](https://www.sparkfun.com/products/15796)  
  - Any 2 or 4 pin PC fan [I am using Noctua NF-A8 PWM](https://noctua.at/en/nf-a8-pwm)  
  - Any SMD5050 strip LED [Led Strip Lights](https://www.amazon.com/gp/product/B08JSQVBDQ/)

# Software Installation

[Install the latest version of Raspian OS](https://projects.raspberrypi.org/en/projects/raspberry-pi-setting-up) on your Raspberry Pi \
[Edit your configuration](https://www.raspberrypi.com/documentation/computers/configuration.html) to enable 'I2C' and 'Remote GPIO' under the interfaces tab \
Save and restart your RPi 

1. Download the files marked "RPi_3dprinter_control_sys_main" 
2. Locate the file 'main' in the folder 'dist' 
3. Edit the properties of 'main' to open with the program 'Terminal' 
4. Set the permission "Execute" to 'Anyone' 
5. If you run the program without modifying these settings a pop-up may occur asking to run the executable with an application 
6. Once these settings are confirmed the program should start with a terminal followed by a window

# Hardware Setup

There are a few options for the hardware of your controller \
A breadboard using the design schematics from the file 'LED_FAN_CONTROLLER.kicad_sch' \
You may need to download and install Kicad to view this schematic.

Here are the design requirements to breadboard this project:



# Installing the Sen55 Sensor

The sensors I recieved do not have a standard coloring scheme. \

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

More information about this installation can be found [here](https://github.com/Sensirion/raspberry-pi-i2c-sen5x)
