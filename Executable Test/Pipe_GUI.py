import PySimpleGUI as gui
import threading, time, subprocess, signal, sys, datetime, requests
from multiprocessing import Process, Pipe, Queue
from Pipe_collectData import collectData
import RPi.GPIO as GPIO
from configparser import ConfigParser
import os.path

# Global variables used in interrupts
lights_sig_on = False
light_timer = 0

# Global variables used in config
#debug = False					# Enable/disable debug mode
#fans_pwm=False					# PWM mode on?
#manual_timer_set_fans = 10		# Preset time (minutes) for manual fans timer
#manual_timer_set_lights = 10	# Preset time (minutes) for manual lights timer
#ntfy_channel = ""				# Channel for ntfy
#mobile_notifications = True		# Enable/disable mobile notifications
#motion_detector = True			# Enable/disable motion detector

def main():
	
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
	
	lights_on = False
	fans_on = False
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
		print(ntfy_full_request)
		ntfy_on = True
		print("ntfy_on " + str(ntfy_on))
	
	if debug == True:
		print_signal = GPIO.input(11)
		fan_signal = GPIO.input(13)
		light_signal = GPIO.input(15)
	
		debug_data = "print = "+str(print_signal)+" fans = "+str(fan_signal)+" lights = "+str(light_signal)
		print(debug_data)
	
	GPIO.output(37, GPIO.LOW)
	GPIO.output(31, GPIO.LOW)
	GPIO.output(29, GPIO.LOW)	
	
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
		# Manual lights button, red when lights are off, green when on
		[gui.Button(key_lights_on, size = (13, 3), button_color='red', font=("Arial", 20)),
		# Manual fan button, red when fans are off, green when fans are on
		gui.Button(key_fans_on, size = (15, 3), button_color='red', font=("Arial", 20))],
		# Temperature display tag
		[gui.Text("Temperature (°F)", text_color="white", key = '-text-', background_color='black', font=("Roboto", 35))],
		# Displays temperature reading
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
	
	running = True

	# Create an event loop
	while running:
		#print("Enter loop " + str(datetime.datetime.now()))
		# Button event read
		event, value = window.read(timeout=2250)
		backup_event = event
		backup_value = value
		#print("After event " + str(datetime.datetime.now()))
		
		# End program if user closes window or
		if event == gui.WIN_CLOSED or event == 'Exit':
			if mobile_notifications == True and ntfy_on == True:
				#requests.post(ntfy_full_request, data="Program closing".encode(encoding='utf-8'))
				jim = 1
			break 
		
		if event == "Options":
			options_menu()
		
		#print("Before Data collect " + str(datetime.datetime.now()))
		# Collect data sent from sensor and parse
		data = parent_conn.recv() 
		#print("After data collect " + str(datetime.datetime.now()))
		temperature_C = data[0] 
		temperature_F = round((temperature_C * 1.8) + 32) # Convert to Fahrenheit
		VOC = round(data[1])
		humidity = data[2]
		nox = data[3]
		#print("After data sort " + str(datetime.datetime.now()))
		# Get current minute of the hour
		current_time = datetime.datetime.now()
		now = current_time.minute
		
		#print("Before Debug " + str(datetime.datetime.now()))
		# Testing data
		if debug == True:
			print_signal = GPIO.input(11)
			fan_signal = GPIO.input(13)
			light_signal = GPIO.input(15)
		
			input_signals = "print = "+str(print_signal)+", fans = "+str(fan_signal)+", lights = "+str(light_signal)
			print(input_signals)
			setting_data = "lights_sig_on = "+str(lights_sig_on)+"\nlights_on = "+str(lights_on)+"\nfans_on = "+str(fans_on)+"\nprint_on = "+str(print_on)+"\nnotification_sent = "+str(notification_sent)+"\nlight_timer_active = "+str(light_timer_active)+"\nlights_manual_set = "+str(lights_manual_set)+"\nfans_manual_set = "+str(fans_manual_set)
			print(setting_data)
			timer_data = "light_timer = "+str(light_timer)+", manual_light_timer = "+str(manual_light_timer)+", manual_fan_timer = "+str(manual_fan_timer)
			print(current_time.strftime("%X"))
			print("\n")
		#print("After Debug " + str(datetime.datetime.now()))
		
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
				GPIO.output(29, GPIO.LOW)
				window[key_lights_on].update(key_lights_on, button_color='red')
			else:
				lights_on = True
				GPIO.output(29, GPIO.HIGH)
				window[key_lights_on].update(key_lights_off, button_color='green')
		
		# Restore event if changed earlier
		event = backup_event
		value = backup_value
		
		# Check temperature to change fan status
		if temperature_F < 80 and fans_on == True and fans_manual_set == False:
			event = key_fans_on
		elif temperature_F >= 80 and fans_on == False and fans_manual_set == False:
			event = key_fans_on
		
		# Check for status change from event
		if event == key_fans_on:
			if fans_on == True:
				fans_on = False
				GPIO.output(31, GPIO.LOW)
				window[key_fans_on].update(key_fans_on, button_color='red')
			else:
				fans_on = True
				GPIO.output(31, GPIO.HIGH)
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
				GPIO.output(37, GPIO.LOW)
				window[key_print_start].update(key_print_start, button_color='green')
			else:
				print_on = True
				GPIO.output(37, GPIO.HIGH)
				window[key_print_start].update(key_print_end, button_color='red')
		
		#print("End loop " + str(datetime.datetime.now()) + "\n")
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
	
def lights(callback):
	
	# Interrupt function when motion sensor detects motion
	# Sets global variable to True to notify main function that motion was detected
	# Only sets light_sig_on = True if the timer has already ran out
	# resets timer, takes into account hour reset
	global lights_sig_on
	global light_timer
	print("interrupt")
	time_set = datetime.datetime.now()
	if light_timer <= time_set.minute:
		lights_sig_on = True
	light_timer = (time_set.minute + 2)%60
	
def config_setup():
	global debug
	global fans_pwm
	global manual_timer_set_fans
	global manual_timer_set_lights
	global ntfy_channel
	global mobile_notifications
	global motion_detector
	
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
		print("-------Config file not found - generating default config-------")
		config['CONFIG'] = {
			'debug': False,
			'fans_pwm': False,
			'manual_timer_set_fans': 10,
			'manual_timer_set_lights': 10,
			'ntfy_channel': "",
			'mobile_notifications': False,
			'motion_detector': True,
		}
		with open("config.ini", "w") as output_file:
			config.write(output_file)
			
			
	config_data = config["CONFIG"]
	debug = config_data["debug"]
	fans_pwm = config_data["fans_pwm"]
	manual_timer_set_fans = config_data["manual_timer_set_fans"]
	manual_timer_set_lights = config_data["manual_timer_set_lights"]
	ntfy_channel = config_data["ntfy_channel"]
	mobile_notifications = config_data["mobile_notifications"]
	motion_detector = config_data["motion_detector"]
	
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
	#print("Enter Options menu " + str(datetime.datetime.now()))
	global debug
	global fans_pwm
	global manual_timer_set_fans
	global manual_timer_set_lights
	global ntfy_channel
	global mobile_notifications
	global motion_detector
	
	#print("Declare globals " + str(datetime.datetime.now()))
	debug_layout = gui.Button("Off", key = "-DEBUG-", size = (13, 3),  button_color='red', font=("Arial", 15))
	if debug == True:
		debug_layout = gui.Button("On", key = "-DEBUG-", size = (13, 3),  button_color='green', font=("Arial", 15))
		
	fans_pwm_layout = gui.Button("Off", key = "-PWM-", size = (13, 3),  button_color='red', font=("Arial", 15))
	if fans_pwm == True:
		fans_pwm_layout = gui.Button("On", key = "-PWM-", size = (13, 3),  button_color='green', font=("Arial", 15))
		
	manual_timer_fans_layout = gui.Slider(range=(0, 30), key="-FTIMER-", enable_events=True, default_value = manual_timer_set_fans, orientation='h', s=(10, 15))
	manual_timer_lights_layout = gui.Slider(range=(0, 30), key="-LTIMER-", enable_events=True, default_value = manual_timer_set_lights, orientation='h', s=(10, 15))
	ntfy_channel_layout = gui.Input(ntfy_channel, key="-NTFY-", size = (13, 3))
	ntfy_confirm_layout = gui.Submit("Confirm", size = (13, 3))
	
	mobile_notifications_layout = gui.Button("Off", key = "-NOTIFICATIONS-", size = (13, 3),  button_color='red', font=("Arial", 15))
	if mobile_notifications == True:
		mobile_notifications_layout = gui.Button("On", key = "-NOTIFICATIONS-", size = (13, 3),  button_color='green', font=("Arial", 15))
		
	motion_detector_layout = gui.Button("Off", key = "-MOTION-", size = (13, 3),  button_color='red', font=("Arial", 15))
	if motion_detector== True:
		motion_detector_layout = gui.Button("On", key = "-MOTION-", size = (13, 3),  button_color='green', font=("Arial", 15))
	
	changes_dict = {}
	debug_changed, fans_pwm_changed, manual_timer_set_fans_changed, manual_timer_set_lights_changed, ntfy_channel_changed, mobile_notifications_changed, motion_detector_changed = (False for i in range(7))
	
	#print("Set individual layouts " + str(datetime.datetime.now()))
	
	# Options layout
	options_layout = [
					[gui.Text("Debug", text_color="white", font=("Arial", 15)), debug_layout],
					[gui.Text("PWM", text_color="white", font=("Arial", 15)), fans_pwm_layout],
					[gui.Text("Fan manual timer", text_color="white", font=("Arial", 15)), manual_timer_fans_layout],
					[gui.Text("Lights manual timer", text_color="white", font=("Arial", 15)), manual_timer_lights_layout],
					[gui.Text("Mobile Notifications", text_color="white", font=("Arial", 15)), mobile_notifications_layout],
					[gui.Text("ntfy_channel", text_color="white", font=("Arial", 15)), ntfy_channel_layout, ntfy_confirm_layout],
					[gui.Text("Motion detector", text_color="white", font=("Arial", 15)), motion_detector_layout],
					[gui.Button("Close", key = "-sac-", button_color='gray', font=("Arial", 20))]]
	
	#print("After Layout " + str(datetime.datetime.now()))
	option_window = gui.Window("Options", options_layout, size=(400, 600)).Finalize()
	#print("After create window " + str(datetime.datetime.now()))
	while True:
		#print("Enter options loop " + str(datetime.datetime.now()))
		event, values = option_window.read()
		#print("Before matchs " + str(datetime.datetime.now()))
		match event:
			case gui.WIN_CLOSED:
				break
			case "-sac-":
				update_config(changes_dict)
				break
			case "-DEBUG-":
				if debug == True:
					if debug_changed == False:
						option_window["-DEBUG-"].update("Off")
						option_window["-DEBUG-"].update(button_color="red")
						changes_dict.update({"debug": False})
						option_window["-sac-"].update("Save and close")
						debug_changed = True
					else:
						option_window["-DEBUG-"].update("On")
						option_window["-DEBUG-"].update(button_color="green")
						changes_dict.pop('debug')
						option_window["-sac-"].update("Close")
						debug_changed = False
				else:
					if debug_changed == False:
						option_window["-DEBUG-"].update("On")
						option_window["-DEBUG-"].update(button_color="green")
						changes_dict.update({"debug": True})
						option_window["-sac-"].update("Save and close")
						debug_changed = True
					else:
						option_window["-DEBUG-"].update("Off")
						option_window["-DEBUG-"].update(button_color="red")
						changes_dict.pop("debug")
						option_window["-sac-"].update("Close")
						debug_changed = False
			case "-PWM-":
				if fans_pwm == True:
					if fans_pwm_changed == False:
						option_window["-PWM-"].update("Off")
						option_window["-PWM-"].update(button_color="red")
						changes_dict.update({"fans_pwm": False})
						option_window["-sac-"].update("Save and close")
						fans_pwm_changed = True
					else:
						option_window["-PWM-"].update("On")
						option_window["-PWM-"].update(button_color="green")
						changes_dict.pop("fans_pwm")
						option_window["-sac-"].update("Close")
						fans_pwm_changed = False
				else:
					if fans_pwm_changed == False:
						option_window["-PWM-"].update("On")
						option_window["-PWM-"].update(button_color="green")
						changes_dict.update({"fans_pwm": True})
						option_window["-sac-"].update("Save and close")
						fans_pwm_changed = True
					else:
						option_window["-PWM-"].update("Off")
						option_window["-PWM-"].update(button_color="red")
						changes_dict.pop("fans_pwm")
						option_window["-sac-"].update("Close")
						fans_pwm_changed = False
			case "-FTIMER-":
				manual_timer_set_fans = int(values["-FTIMER-"])
				changes_dict.update({"manual_timer_set_fans": manual_timer_set_fans})
				option_window["-sac-"].update("Save and close")
				manual_timer_set_fans_changed = True
			case "-LTIMER-":
				manual_timer_set_lights = int(values["-LTIMER-"])
				changes_dict.update({"manual_timer_set_lights": manual_timer_set_lights})
				option_window["-sac-"].update("Save and close")
				manual_timer_set_lights_changed = True
			case "Confirm":
				temp = values["-NTFY-"]
				if temp == ntfy_channel:
					
					ntfy_channel_changed = False
				else:
					print("JIM")
					ntfy_channel = temp
					changes_dict.update({"ntfy_channel": ntfy_channel})
					option_window["-sac-"].update("Save and close")
					ntfy_channel_changed = True
			case "-NOTIFICATIONS-":
				if mobile_notifications == True:
					if mobile_notifications_changed == False:
						#option_window["-NTFY-"].update(disabled=True)
						option_window["-NOTIFICATIONS-"].update("Off")
						option_window["-NOTIFICATIONS-"].update(button_color="red")
						changes_dict.update({"mobile_notifications": False})
						option_window["-sac-"].update("Save and close")
						mobile_notifications_changed = True
					else:
						#option_window["-NTFY-"].update(disabled=False)
						option_window["-NOTIFICATIONS-"].update("On")
						option_window["-NOTIFICATIONS-"].update(button_color="green")
						changes_dict.pop("mobile_notifications")
						option_window["-sac-"].update("Close")
						mobile_notifications_changed = False
				else:
					if mobile_notifications_changed == False:
						#option_window["-NTFY-"].update(disabled=False)
						option_window["-NOTIFICATIONS-"].update("On")
						option_window["-NOTIFICATIONS-"].update(button_color="green")
						changes_dict.update({"mobile_notifications": True})
						option_window["-sac-"].update("Save and close")
						mobile_notifications_changed = True
					else:
						#option_window["-NTFY-"].update(disabled=True)
						option_window["-NOTIFICATIONS-"].update("Off")
						option_window["-NOTIFICATIONS-"].update(button_color="red")
						changes_dict.pop("mobile_notifications")
						option_window["-sac-"].update("Close")
						mobile_notifications_changed = False
			case "-MOTION-":
				if motion_detector == True:
					if motion_detector_changed == False:
						option_window["-MOTION-"].update("Off")
						option_window["-MOTION-"].update(button_color="red")
						changes_dict.update({"motion_detector": False})
						option_window["-sac-"].update("Save and close")
						motion_detector_changed = True
					else:
						option_window["-MOTION-"].update("On")
						option_window["-MOTION-"].update(button_color="green")
						changes_dict.pop("motion_detector")
						option_window["-sac-"].update("Close")
						motion_detector_changed = False
				else:
					if motion_detector_changed == False:
						option_window["-MOTION-"].update("On")
						option_window["-MOTION-"].update(button_color="green")
						changes_dict.update({"motion_detector": True})
						option_window["-sac-"].update("Save and close")
						motion_detector_changed = True
					else:
						option_window["-MOTION-"].update("Off")
						option_window["-MOTION-"].update(button_color="red")
						changes_dict.pop("motion_detector")
						option_window["-sac-"].update("Close")
						motion_detector_changed = False
		#print("End matches " + str(datetime.datetime.now()))
	option_window.close()
			
		
	
def update_config(option_changed):
	global debug
	global fans_pwm
	global manual_timer_set_fans
	global manual_timer_set_lights
	global ntfy_channel
	global mobile_notifications
	global motion_detector
	
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
	
	
	
	print("-------Writing config-------")
	with open("config.ini", "w") as config_file:
		config.write(config_file)
				
if __name__ == '__main__':
	GPIO.setmode(GPIO.BOARD)
	GPIO.setup(11, GPIO.IN) # Printing in
	GPIO.setup(13, GPIO.IN) # Fans in
	GPIO.setup(15, GPIO.IN) # Lights in
	GPIO.setup(16, GPIO.IN) # motion sensor in
	GPIO.setup(29, GPIO.OUT) # Lights out
	GPIO.setup(31, GPIO.OUT) # Fans out
	GPIO.setup(37, GPIO.OUT) # Print out
	
	# Set a interrupt if motion is detected on motion sensor
	GPIO.add_event_detect(16, GPIO.RISING, callback=lights, bouncetime=100)

	parent_conn, child_conn = Pipe()

	t1 = threading.Thread(target=main) # Start main function (in this file)
	t2 = threading.Thread(target=collectData, args = (child_conn, )) # Start data collection from Pipe_collectData.py
	
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
