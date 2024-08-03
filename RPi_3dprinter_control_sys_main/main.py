import PySimpleGUI as gui
import threading, time, subprocess, signal, sys, datetime, requests
from multiprocessing import Process, Pipe, Queue
from CollectData import collectData
import RPi.GPIO as GPIO
from configparser import ConfigParser
import os.path
import subprocess
import pigpio

# Global variables used in interrupts
lights_sig_on = False
light_timer = 0
lights_on = False
fans_on = False

def main():
	
	check_packages()
	config_setup()
	GPIO.setmode(GPIO.BOARD)
	
	# Declaration of variables used
	temperature_F = 0
	VOC = 0
	humidity = 0
	nox = 0
	
	# Interrupt global variables
	global lights_sig_on
	global light_timer
	
	# Config global variables
	global debug
	global fans_pwm
	global manual_timer_set_fans
	global manual_timer_set_lights
	global ntfy_channel
	global mobile_notifications
	global motion_detector
	global color
	
	# GPIO output
	global PI
	
	# Debugging variables
	global lights_on
	global fans_on
	global PWM
	global tach
	global light_color
	
	
	print_on = False
	notification_sent = False
	light_timer_active = False
	lights_manual_set = False
	fans_manual_set = False
	manual_light_timer = 0
	manual_fan_timer = 0
	ntfy_full_request = "https://ntfy.sh/"
	ntfy_on = False
	
	if mobile_notifications == True and ntfy_channel != "":
		ntfy_full_request = ntfy_full_request + ntfy_channel
		print("Notification channel" + ntfy_full_request)
		ntfy_on = True
		print("ntfy_on = " + str(ntfy_on))
	
	# Set keys for window layout
	VOC_safe = "SAFE"
	VOC_unsafe = "UNSAFE"

	key_lights_on = "Turn Lights On"
	key_lights_off = "Turn Lights Off"

	key_fans_on = "Turn Fans On"
	key_fans_off = "Turn Fans Off"
	
	key_print_start = "Start Print"
	key_print_end = "End Print"
	
	# Menu
	menu_def = [['File', ['Options', 'Exit']],
				['Help', 'About'], ]
	
	# Initial window layout
	layout = [
		#[gui.Menu(menu_def, )],
		[gui.Button(key_lights_on, size = (13, 3), button_color='red', font=("Arial", 20)),
		gui.Button(key_fans_on, size = (15, 3), button_color='red', font=("Arial", 20))],
		[gui.Text("Temperature (°F)", text_color="white", key = '-text-', background_color='black', font=("Roboto", 35))],
		[gui.Text(temperature_F, key = "tempF", text_color="blue", background_color='black', font=("Arial", 100)),
		gui.Text("°F", text_color="blue", key = '-text-', background_color='black', font=("Arial", 90))],
		[gui.Text("VOC", text_color="white", key = '-text-', background_color='black', font=("Arial", 45))],
		[gui.Text(VOC_safe,  key = "voc", text_color="green", background_color='black', font=("Arial", 90))],
		[gui.Text(VOC,  key = "voc_val", text_color="green", background_color='black', font=("Arial", 90))],
		[gui.Button(key_print_start, size = 8, button_color='green',  font=("Arial", 36)), gui.Button("Options", font=("Arial", 36))]
	]

	# Create the window
	gui.theme_background_color('black')
	window = gui.Window("Control Panel", layout, size=(480, 640),  element_justification='c').Finalize()
	window.Maximize()

	# Create an event loop
	while True:
		# Button event read
		event, value = window.read(timeout=0)
		backup_event = event
		backup_value = value
		
		# End program if user closes window
		if event == gui.WIN_CLOSED or event == 'Exit':
			if mobile_notifications == True and ntfy_on == True:
				#requests.post(ntfy_full_request, data="Program closing".encode(encoding='utf-8'))
				jim = 1
			break 
		
		if event == "Options":
			options_menu()
		
		# Collect data sent from sensor and parse
		if parent_conn.poll():
			data = parent_conn.recv()
		
			temperature_C = data[0] 
			temperature_F = round((temperature_C * 1.8) + 32) # Convert to Fahrenheit
			VOC = round(data[1])
			humidity = data[2]
			nox = data[3]
		
		# Get current minute of the hour
		current_time = datetime.datetime.now()
		now = current_time.minute
		
		# Send push notifications hourly of temperature/VOC levels
		if now == 0 and notification_sent == False and mobile_notifications == True and ntfy_on == True:
			status_notification(VOC, temperature_F, ntfy_full_request)
			notification_sent = True
		elif now == 1:
			notification_sent = False
		
		# Turn off manual settings when timer runs out
		if now == manual_light_timer:
			lights_manual_set = False
			
		if now == manual_fan_timer:
			fans_manual_set = False
		
			
		# Update data on window
		window["tempF"].update(temperature_F)
		window["voc_val"].update(VOC)
		
		
		# Change VOC display color on window to display safety
		if VOC > 150:
			window["voc"].update(VOC_unsafe, text_color="red")
			window["voc_val"].update(VOC, text_color="red")
		elif VOC < 150:
			window["voc"].update(VOC_safe, text_color="green")
			window["voc_val"].update(VOC, text_color="green")
		
		# Check if events were set manually
		if event == key_lights_on:
			lights_manual_set = True
			manual_light_timer = (now + 10)%60
		elif event == key_fans_on:
			fans_manual_set = True
			manual_fan_timer = (now + 10)%60
		
		# Turn lights off if timer is done
		if now >= light_timer and lights_on == True and lights_manual_set == False and light_timer_active == True:
			event = key_lights_on
			light_timer_active = False
		
		# Turn lights on if motion sensor detects movement
		if lights_sig_on == True and lights_on == False and lights_manual_set == False:
			event = key_lights_on
			lights_sig_on = False
			light_timer_active = True
		
		# Check if manual light button event took place
		if event == key_lights_on:
			if lights_on == True:
				lights_on = False
				change_light_color(light_color, False)
				window[key_lights_on].update(key_lights_on, button_color='red')
			else:
				lights_on = True
				change_light_color(light_color, True)
				window[key_lights_on].update(key_lights_off, button_color='green')
		
		# Restore event if changed earlier
		event = backup_event
		value = backup_value
		
		# Check temperature to change fan status
		if temperature_F < 80 and fans_on == True and fans_manual_set == False:
			event = key_fans_on
			setPWM(1000000) # fan off
		elif temperature_F >= 80 and fans_on == False and fans_manual_set == False:
			event = key_fans_on
			setPWM(750000) # set fan to 25% speed
		elif temperature_F >= 80 and temperature_F < 90 and fans_on == True and fans_pwm == True:
			setPWM(500000) # fans set 50% speed
		elif temperature_F >= 90 and temperature_F < 100 and fans_on == True and fans_pwm == True:
			setPWM(250000) # fans set 75% speed
		elif temperature_F >= 100 and fans_on == True and fans_pwm == True:
			setPWM(0) # fans set 100% speed
		
		# Check for status change from event
		if event == key_fans_on:
			if fans_on == True:
				fans_on = False
				GPIO.output(16, GPIO.LOW)
				window[key_fans_on].update(key_fans_on, button_color='red')
			else:
				fans_on = True
				GPIO.output(16, GPIO.HIGH)
				window[key_fans_on].update(key_fans_off, button_color='green')
			
		# Restore event if changed earlier
		event = backup_event
		value = backup_value	
			
		# Change button color and text when printing done
		if print_on == True and lights_on == False and light_timer_active == False and now >= light_timer + 5:
			event = key_print_start	
		
		# Check for a print event
		if event == key_print_start:
			if print_on == True:
				print_on = False
				if mobile_notifications == True and ntfy_on == True:
					notify()
				#GPIO.output(37, GPIO.LOW)
				window[key_print_start].update(key_print_start, button_color='green')
			else:
				print_on = True
				#GPIO.output(37, GPIO.HIGH)
				window[key_print_start].update(key_print_end, button_color='red')
		
	window.close()
	sys.exit(0)	

	
def notify(ntfy_full_request):
	
	# Function sends notification at the end of a printing cycle
	# Uses ntfy (ntfy.sh) to send push notifications to mobile app
	print("printing ended")
	#requests.post(ntfy_full_request, data="Printing Complete".encode(encoding='utf-8'))

def status_notification(VOC, temperature, ntfy_full_request):
	
	# Function called at beginning of every hour to show 
	# current temperature and VOC levels
	# Uses ntfy (ntfy.sh) to send push notifications to mobile app
	myObj = "VOC level = " + str(VOC) + ", Temperature = " + str(temperature) + "°F"
	requests.post(ntfy_full_request, data=myObj.encode(encoding='utf-8'))
	
def signal_handler(sig, frame):
	
	# Clean exit from program
	GPIO.cleanup()
	sys.exit()
	
def setPWM(dutyCycle):
	global PI
	global PWM
	if dutyCycle == 1000000:
		PI.hardware_PWM(12, 0, dutyCycle)
	else:
		PI.hardware_PWM(12, 25000, dutyCycle)
		
def change_light_color(color, on):
	# To add colors later just mix and match 
	# RGB values, only 8 total combinations
	# currently available
	if color == "white" and on == True:
		GPIO.output(11, GPIO.HIGH)
		GPIO.output(13, GPIO.HIGH)
		GPIO.output(15, GPIO.HIGH)
	elif color == "green" and on == True:
		GPIO.output(11, GPIO.HIGH)
		GPIO.output(13, GPIO.LOW)
		GPIO.output(15, GPIO.LOW)
	elif color == "red" and on == True:
		GPIO.output(11, GPIO.LOW)
		GPIO.output(13, GPIO.HIGH)
		GPIO.output(15, GPIO.LOW)
	elif color == "blue" and on == True:
		GPIO.output(11, GPIO.LOW)
		GPIO.output(13, GPIO.LOW)
		GPIO.output(15, GPIO.HIGH) 
	elif color == "lgreen" and on == True:
		GPIO.output(11, GPIO.HIGH)
		GPIO.output(13, GPIO.HIGH)
		GPIO.output(15, GPIO.LOW)
	elif color == "lblue" and on == True:
		GPIO.output(11, GPIO.HIGH)
		GPIO.output(13, GPIO.LOW)
		GPIO.output(15, GPIO.HIGH)
	elif color == "purple" and on == True:
		GPIO.output(11, GPIO.LOW)
		GPIO.output(13, GPIO.HIGH)
		GPIO.output(15, GPIO.HIGH)
	
	if on == False:
		GPIO.output(11, GPIO.LOW)
		GPIO.output(13, GPIO.LOW)
		GPIO.output(15, GPIO.LOW)         
	
def lights(callback):
	
	# Interrupt function when motion sensor detects motion
	# Sets global variable to True to notify main function that motion was detected
	# Only sets light_sig_on = True if the timer has already ran out
	# resets timer, takes into account hour reset
	global lights_sig_on
	global light_timer
	print("-------Motion Detected-------")
	time_set = datetime.datetime.now()
	if light_timer <= time_set.minute:
		lights_sig_on = True
	light_timer = (time_set.minute + 2)%60
	
def config_setup():
	# initializing global variables
	# if new config item is added, add a global variable
	# This variable will be the same as other later in section
	# global <new_item_name>
	global debug
	global fans_pwm
	global manual_timer_set_fans
	global manual_timer_set_lights
	global ntfy_channel
	global mobile_notifications
	global motion_detector
	global color
	global light_color
	
	dir_path = os.path.dirname(sys.executable)
	if getattr(sys, 'frozen', False):
		dir_path = os.path.dirname(sys.executable)
	elif __file__:
		dir_path = os.path.dirname(__file__)
	config_filepath = dir_path+"/config.ini"
	exists = os.path.exists(config_filepath)
	config = ConfigParser()
	
	if exists:
		print("-------Loading config-------")
		config.read(config_filepath)
	else:
		# When adding new items to config, may require generating new config
		# At the end of the list add items with syntax:
		# '<new_item_name>': "<default item value>",
		# <new_item_name> will be used in other sections
		print("-------Config file not found - generating default config-------")
		config['CONFIG'] = {
			'debug': False,
			'fans_pwm': False,
			'manual_timer_set_fans': 10,
			'manual_timer_set_lights': 10,
			'ntfy_channel': "",
			'mobile_notifications': False,
			'motion_detector': True,
			'color': "white",
		}
		with open("config.ini", "w") as output_file:
			config.write(output_file)
			
	# When adding new item to config, additional line at end required
	# syntax is just
	# <config_var_name> = config_data["<new_item_name>"]
	# <new_item_name> should be the same as the above section
	config_data = config["CONFIG"]
	debug = config_data["debug"]
	fans_pwm = config_data["fans_pwm"]
	manual_timer_set_fans = config_data["manual_timer_set_fans"]
	manual_timer_set_lights = config_data["manual_timer_set_lights"]
	ntfy_channel = config_data["ntfy_channel"]
	mobile_notifications = config_data["mobile_notifications"]
	motion_detector = config_data["motion_detector"]
	color = config_data["color"]
	light_color = config_data["color"]
	
	if debug == "True":
		debug = True
	else:
		debug = False
		
	if fans_pwm == "True":
		fans_pwm = True
	else:
		fans_pwm = False
		
	if mobile_notifications == "True":
		mobile_notifications = True
	else:
		mobile_notifications = False
		
	if motion_detector == "True":
		motion_detector = True
	else:
		motion_detector = False
		
	print("-------Loading Complete-------")
	
		
def options_menu():
	# initializing global variables in function
	# If new config item is added
	# add new global variable here too
	# global <new_item_name>
	global debug
	global fans_pwm
	global manual_timer_set_fans
	global manual_timer_set_lights
	global ntfy_channel
	global mobile_notifications
	global motion_detector
	global color
	global light_color
	
	
	# When adding item to options menu
	# create a key and name variable <new_item_name_layout>
	# fill in any other required info for layouts in pysimplegui
	# https://docs.pysimplegui.com/en/latest/documentation/module/layouts
	debug_layout = gui.Button("Off", key = "-DEBUG-", size = (10, 3),  button_color='red', font=("Arial", 13))
	if debug == True:
		debug_layout = gui.Button("On", key = "-DEBUG-", size = (10, 3),  button_color='green', font=("Arial", 13))
		
	fans_pwm_layout = gui.Button("Off", key = "-PWM-", size = (10, 3),  button_color='red', font=("Arial", 13))
	if fans_pwm == True:
		fans_pwm_layout = gui.Button("On", key = "-PWM-", size = (10, 3),  button_color='green', font=("Arial", 13))
		
	manual_timer_fans_layout = gui.Slider(range=(0, 30), key="-FTIMER-", enable_events=True, default_value = manual_timer_set_fans, orientation='h', s=(10, 15))
	manual_timer_lights_layout = gui.Slider(range=(0, 30), key="-LTIMER-", enable_events=True, default_value = manual_timer_set_lights, orientation='h', s=(10, 15))
	ntfy_channel_layout = gui.Input(ntfy_channel, key="-NTFY-", size = (10, 3))
	ntfy_confirm_layout = gui.Submit("Confirm", size = (10, 3))
	
	mobile_notifications_layout = gui.Button("Off", key = "-NOTIFICATIONS-", size = (10, 3),  button_color='red', font=("Arial", 13))
	if mobile_notifications == True:
		mobile_notifications_layout = gui.Button("On", key = "-NOTIFICATIONS-", size = (10, 3),  button_color='green', font=("Arial", 13))
		
	motion_detector_layout = gui.Button("Off", key = "-MOTION-", size = (10, 3),  button_color='red', font=("Arial", 13))
	if motion_detector== True:
		motion_detector_layout = gui.Button("On", key = "-MOTION-", size = (10, 3),  button_color='green', font=("Arial", 13))
	
	if color == "white":
		color_val = 0
	elif color == "green":
		color_val = 1
	elif color == "lgreen":
		color_val = 2
	elif color == "blue":
		color_val = 3
	elif color == "lblue":
		color_val = 4
	elif color == "purple":
		color_val = 5
	elif color == "red":
		color_val = 6
		
	color_layout = gui.Slider(range=(0, 6), key = "-COLOR-", disable_number_display = True, enable_events=True, default_value = color_val, orientation='h', size = (10, 15))
	
	# if new item added to config,
	# please add a <new_item_name_changed> to end of list
	# and increment range by 1
	changes_dict = {}
	debug_changed, fans_pwm_changed, manual_timer_set_fans_changed, manual_timer_set_lights_changed, ntfy_channel_changed, mobile_notifications_changed, motion_detector_changed, color_changed = (False for i in range(8))
	
	
	# Options layout
	# add new layouts created above here with any necessary text
	options_layout = [
					[gui.Text("Debug", text_color="white", font=("Arial", 15)), debug_layout, gui.Text("PWM", text_color="white", font=("Arial", 15)), fans_pwm_layout],
					#[],
					[gui.Text("Fan manual timer", text_color="white", font=("Arial", 15)), manual_timer_fans_layout],
					[gui.Text("Lights manual timer", text_color="white", font=("Arial", 15)), manual_timer_lights_layout],
					[gui.Text("Mobile Notifications", text_color="white", font=("Arial", 15)), mobile_notifications_layout],
					[gui.Text("ntfy_channel", text_color="white", font=("Arial", 15)), ntfy_channel_layout, ntfy_confirm_layout],
					[gui.Text("Motion detector", text_color="white", font=("Arial", 15)), motion_detector_layout],
					[gui.Text("LED color", text_color = "white", font=("Arial", 15)), color_layout],
					[gui.Button("Close", key = "-sac-", button_color='gray', font=("Arial", 20))]]
	
	option_window = gui.Window("Options", options_layout, size=(480, 750), resizable = True).Finalize()
	#option_window.Maximize()

	while True:
		event, values = option_window.read()
		
		
		# Basic case match in python
		# match case to -KEY- created in above layout section
		# The value <new_item_name_changed> = True needs to be set if changed so config will update
		# as well as the changed_dict.update({"<new_item_name>: <new_item_value>})
		# everything else is optional but may confuse user 
		match event:
			case gui.WIN_CLOSED:
				break
			case "-sac-":
				if changes_dict:
					update_config(changes_dict)
				break
			case "-DEBUG-":
				if debug == True:
					if debug_changed == False:
						option_window["-DEBUG-"].update("Off")
						option_window["-DEBUG-"].update(button_color="red")
						changes_dict.update({"debug": False})
						debug_changed = True
					else:
						option_window["-DEBUG-"].update("On")
						option_window["-DEBUG-"].update(button_color="green")
						changes_dict.pop('debug')
						debug_changed = False
				else:
					if debug_changed == False:
						option_window["-DEBUG-"].update("On")
						option_window["-DEBUG-"].update(button_color="green")
						changes_dict.update({"debug": True})
						debug_changed = True
					else:
						option_window["-DEBUG-"].update("Off")
						option_window["-DEBUG-"].update(button_color="red")
						changes_dict.pop("debug")
						debug_changed = False
			case "-PWM-":
				if fans_pwm == True:
					if fans_pwm_changed == False:
						option_window["-PWM-"].update("Off")
						option_window["-PWM-"].update(button_color="red")
						changes_dict.update({"fans_pwm": False})
						fans_pwm_changed = True
					else:
						option_window["-PWM-"].update("On")
						option_window["-PWM-"].update(button_color="green")
						changes_dict.pop("fans_pwm")
						fans_pwm_changed = False
				else:
					if fans_pwm_changed == False:
						option_window["-PWM-"].update("On")
						option_window["-PWM-"].update(button_color="green")
						changes_dict.update({"fans_pwm": True})
						fans_pwm_changed = True
					else:
						option_window["-PWM-"].update("Off")
						option_window["-PWM-"].update(button_color="red")
						changes_dict.pop("fans_pwm")
						fans_pwm_changed = False
			case "-FTIMER-":
				manual_timer_set_fans = int(values["-FTIMER-"])
				changes_dict.update({"manual_timer_set_fans": manual_timer_set_fans})
				manual_timer_set_fans_changed = True
			case "-LTIMER-":
				manual_timer_set_lights = int(values["-LTIMER-"])
				changes_dict.update({"manual_timer_set_lights": manual_timer_set_lights})
				manual_timer_set_lights_changed = True
			case "Confirm":
				temp = values["-NTFY-"]
				if temp == ntfy_channel:
					
					ntfy_channel_changed = False
				else:
					print("JIM")
					ntfy_channel = temp
					changes_dict.update({"ntfy_channel": ntfy_channel})
					ntfy_channel_changed = True
			case "-NOTIFICATIONS-":
				if mobile_notifications == True:
					if mobile_notifications_changed == False:
						#option_window["-NTFY-"].update(disabled=True)
						option_window["-NOTIFICATIONS-"].update("Off")
						option_window["-NOTIFICATIONS-"].update(button_color="red")
						changes_dict.update({"mobile_notifications": False})
						mobile_notifications_changed = True
					else:
						#option_window["-NTFY-"].update(disabled=False)
						option_window["-NOTIFICATIONS-"].update("On")
						option_window["-NOTIFICATIONS-"].update(button_color="green")
						changes_dict.pop("mobile_notifications")
						mobile_notifications_changed = False
				else:
					if mobile_notifications_changed == False:
						#option_window["-NTFY-"].update(disabled=False)
						option_window["-NOTIFICATIONS-"].update("On")
						option_window["-NOTIFICATIONS-"].update(button_color="green")
						changes_dict.update({"mobile_notifications": True})
						mobile_notifications_changed = True
					else:
						#option_window["-NTFY-"].update(disabled=True)
						option_window["-NOTIFICATIONS-"].update("Off")
						option_window["-NOTIFICATIONS-"].update(button_color="red")
						changes_dict.pop("mobile_notifications")
						mobile_notifications_changed = False
			case "-MOTION-":
				if motion_detector == True:
					if motion_detector_changed == False:
						option_window["-MOTION-"].update("Off")
						option_window["-MOTION-"].update(button_color="red")
						changes_dict.update({"motion_detector": False})
						motion_detector_changed = True
					else:
						option_window["-MOTION-"].update("On")
						option_window["-MOTION-"].update(button_color="green")
						changes_dict.pop("motion_detector")
						motion_detector_changed = False
				else:
					if motion_detector_changed == False:
						option_window["-MOTION-"].update("On")
						option_window["-MOTION-"].update(button_color="green")
						changes_dict.update({"motion_detector": True})
						motion_detector_changed = True
					else:
						option_window["-MOTION-"].update("Off")
						option_window["-MOTION-"].update(button_color="red")
						changes_dict.pop("motion_detector")
						motion_detector_changed = False
			case "-COLOR-":
				color= int(values["-COLOR-"])
				if color == 0:
					color = "white"
				elif color == 1:
					color = "green"
				elif color == 2:
					color = "lgreen"
				elif color == 3:
					color = "blue"
				elif color == 4:
					color = "lblue"
				elif color == 5:
					color = "purple"
				elif color == 6:
					color = "red"
				else:
					color = "white"
				
				changes_dict.update({"color": color})
				light_color = color
				change_light_color(color, lights_on)
				color_changed = True
				
		if changes_dict == {}:
			option_window["-sac-"].update("Close")
		else:
			option_window["-sac-"].update("Save and close")
				
	option_window.close()
			
		
	
def update_config(option_changed):
	# initializing global variables in function
	# If new config item is added
	# add new global variable here too
	# global <new_item_name>
	global debug
	global fans_pwm
	global manual_timer_set_fans
	global manual_timer_set_lights
	global ntfy_channel
	global mobile_notifications
	global motion_detector
	global color
	global light_color
	
	dir_path = os.path.dirname(sys.executable)
	if getattr(sys, 'frozen', False):
		dir_path = os.path.dirname(sys.executable)
	elif __file__:
		dir_path = os.path.dirname(__file__)
	config_filepath = dir_path+"/config.ini"
	#print("Filepath: "+str(config_filepath))
	#print("test filepath: "+str(dir_path_test))
	exists = os.path.exists(config_filepath)
	config = ConfigParser()
	config.read(config_filepath)
	
	for key in option_changed:
		# If new config item is added
		# add section to case match
		## case '<new_item_name>':
		##		<new_item_name> = option_changed[key]
		##		config.set('CONFIG', "<new_item_name>", str(<new_item_name>))
		# str(<new_item_name>) is needed for value to be read
		match key:
			case 'debug':
				debug = option_changed[key]
				config.set('CONFIG', "debug", str(debug))
			case "fans_pwm":
				fans_pwm = option_changed[key]
				config.set('CONFIG', "fans_pwm", str(fans_pwm))
			case "manual_timer_set_fans":
				manual_timer_set_fans = option_changed[key]
				config.set('CONFIG', "manual_timer_set_fans", str(manual_timer_set_fans))
			case "manual_timer_set_lights":
				manual_timer_set_lights = option_changed[key]
				config.set('CONFIG', "manual_timer_set_lights", str(manual_timer_set_lights))
			case "ntfy_channel":
				ntfy_channel = option_changed[key]
				config.set('CONFIG', "ntfy_channel", str(ntfy_channel))
			case "mobile_notifications":
				mobile_notifications = option_changed[key]
				config.set('CONFIG', "mobile_notifications", str(mobile_notifications))
			case "motion_detector":
				motion_detector = option_changed[key]
				config.set('CONFIG', "motion_detector", str(motion_detector))
			case "color":
				color = option_changed[key]
				config.set('CONFIG', "color", str(color))
				light_color = str(option_changed[key])
	
	
	
	print("-------Writing config-------")
	with open("config.ini", "w") as config_file:
		config.write(config_file)
		
def check_packages():
	try:
		subprocess.check_output(["dpkg", "-s", "i2c-tools"])
	except subprocess.CalledProcessError:
		subprocess.call(["sudo", 'apt-get', 'install', 'i2c-tools']) 
		
				
if __name__ == '__main__':
	
	subprocess.call(["sudo", 'pigpiod'])
	subprocess.call(["sudo", 'systemctl', 'enable', 'pigpiod'])
	
	GPIO.setmode(GPIO.BOARD)
	GPIO.setup(11, GPIO.OUT) # Green
	GPIO.setup(13, GPIO.OUT) # Red
	GPIO.setup(15, GPIO.OUT) # Blue
	GPIO.setup(16, GPIO.OUT) # Fan
	GPIO.setup(18, GPIO.IN) # Tachometer
	
	# This is needed for PWM
	PI = pigpio.pi()
	PI.set_mode(12, pigpio.OUTPUT)
	
	# Set a interrupt if motion is detected on motion sensor
	#GPIO.add_event_detect(16, GPIO.RISING, callback=lights, bouncetime=100)

	parent_conn, child_conn = Pipe()

	t1 = threading.Thread(target=main) # Start main function (in this file)
	t2 = threading.Thread(target=collectData, args = (child_conn, )) # Start data collection from CollectData.py
	
	# Start threads
	t1.start()
	t2.start()
	
	# Clean up GPIO when program closes
	signal.signal(signal.SIGINT, signal_handler)
	#signal.pause()
	
	# Close threads
	t1.join()
	t2.join() 
	
	sys.exit()
