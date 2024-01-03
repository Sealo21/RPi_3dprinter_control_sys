import PySimpleGUI as gui
import threading, time, subprocess, signal, sys, datetime, requests
from multiprocessing import Process, Pipe, Queue
from Pipe_collectData import collectData
import RPi.GPIO as GPIO

# Global variables used in interrupts
lights_sig_on = False
light_timer = 0
debug = False

def main():
	
	# Declaration of variables used
	temperature_F = 0
	VOC = 0
	humidity = 0
	nox = 0
	
	global lights_sig_on
	global light_timer
	global debug
	
	lights_on = False
	fans_on = False
	print_on = False
	notification_sent = False
	light_timer_active = False
	lights_manual_set = False
	fans_manual_set = False
	manual_light_timer = 0
	manual_fan_timer = 0
	
	if debug == True:
		print_signal = GPIO.input(11)
		fan_signal = GPIO.input(13)
		light_signal = GPIO.input(15)
	
		fuckstupid = "print = "+str(print_signal)+" fans = "+str(fan_signal)+" lights = "+str(light_signal)
		print(fuckstupid)
	
	
	GPIO.output(37, GPIO.LOW)
	GPIO.output(31, GPIO.LOW)
	GPIO.output(29, GPIO.LOW)
	#if print_signal == 1:
	#	GPIO.output(37, GPIO.LOW)
	#elif fan_signal == 1:
	#	GPIO.output(31, GPIO.LOW)
	#elif light_signal == 1:
	#	GPIO.output(29, GPIO.LOW)	
	
	# Set keys for window layout
	VOC_safe = "SAFE"
	VOC_unsafe = "UNSAFE"

	key_lights_on = "Turn Lights On"
	key_lights_off = "Turn Lights Off"

	key_fans_on = "Turn Fans On"
	key_fans_off = "Turn Fans Off"
	
	key_print_start = "Start Print"
	key_print_end = "End Print"
	
	# Initial window layout
	layout = [
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
		[gui.Button(key_print_start, size = 40, button_color='green', font=("Arial", 50))]
	]

	# Create the window
	gui.theme_background_color('black')
	window = gui.Window("Control Panel", layout, size=(480, 640),  element_justification='c').Finalize()
	window.Maximize()
	
	running = True
	
	# Create an event loop
	while running:
		
		# Button event read
		event, value = window.read(timeout=2250)
		backup_event = event
		backup_value = value
		
		# End program if user closes window or
		if event == gui.WIN_CLOSED:
			#requests.post("https://ntfy.sh/jimburger", data="Program closing".encode(encoding='utf-8'))
			
			break 
		
		
		# Collect data sent from sensor and parse
		data = parent_conn.recv() 
		temperature_C = data[0] 
		temperature_F = round((temperature_C * 1.8) + 32) # COnvert to Fahrenheit
		VOC = round(data[1])
		humidity = data[2]
		nox = data[3]
		
		# Get current minute of the hour
		current_time = datetime.datetime.now()
		now = current_time.minute
		
		# Testing data
		if debug == True:
			print_signal = GPIO.input(11)
			fan_signal = GPIO.input(13)
			light_signal = GPIO.input(15)
		
			input_signals = "print = "+str(print_signal)+", fans = "+str(fan_signal)+", lights = "+str(light_signal)
			print(fuckstupid)
			setting_data = "lights_sig_on = "+str(lights_sig_on)+"\nlights_on = "+str(lights_on)+"\nfans_on = "+str(fans_on)+"\nprint_on = "+str(print_on)+"\nnotification_sent = "+str(notification_sent)+"\nlight_timer_active = "+str(light_timer_active)+"\nlights_manual_set = "+str(lights_manual_set)+"\nfans_manual_set = "+str(fans_manual_set)
			print(setting_data)
			timer_data = "light_timer = "+str(light_timer)+", manual_light_timer = "+str(manual_light_timer)+", manual_fan_timer = "+str(manual_fan_timer)
			print(current_time.strftime("%X"))
			print("\n")
			
		
		# Send push notifications hourly of temperature/VOC levels
		if now == 0 and notification_sent == False:
			status_notification(VOC, temperature_F)
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
			print("light timer")
		
		# Turn lights on if motion sensor detects movement
		if lights_sig_on == True and lights_on == False and lights_manual_set == False:
			event = key_lights_on
			lights_sig_on = False
			light_timer_active = True
			print("motion signal")
		
		# Check if manual light button event took place
		if event == key_lights_on:
			if lights_on == True:
				lights_on = False
				print("lights off")
				GPIO.output(29, GPIO.LOW)
				window[key_lights_on].update(key_lights_on, button_color='red')
			else:
				lights_on = True
				print("lights on")
				GPIO.output(29, GPIO.HIGH)
				window[key_lights_on].update(key_lights_off, button_color='green')
		
		# Restore event if changed earlier
		event = backup_event
		value = backup_value
		
		# Check temperature to change fan status
		if temperature_F < 80 and fans_on == True and fans_manual_set == False:
			event = key_fans_on
			print("temp fans off")
		elif temperature_F >= 80 and fans_on == False and fans_manual_set == False:
			event = key_fans_on
			print("temp fans on")
		
		# Check for status change from event
		if event == key_fans_on:
			if fans_on == True:
				fans_on = False
				print("fans off")
				GPIO.output(31, GPIO.LOW)
				window[key_fans_on].update(key_fans_on, button_color='red')
			else:
				fans_on = True
				print("fans on")
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
				notify()
				print("printing ended 1")
				GPIO.output(37, GPIO.LOW)
				window[key_print_start].update(key_print_start, button_color='green')
			else:
				print_on = True
				print("printing started")
				GPIO.output(37, GPIO.HIGH)
				window[key_print_start].update(key_print_end, button_color='red')
		
		
	window.close()
	sys.exit(0)	

	
def notify():
	
	# Function sends notification at the end of a printing cycle
	# Uses ntfy (ntfy.sh) to send push notifications to mobile app
	print("printing ended 2")
	#requests.post("https://ntfy.sh/jimburger", data="Printing Complete".encode(encoding='utf-8'))

def status_notification(VOC, temperature):
	
	# Function called at beginning of every hour to show 
	# current temperature and VOC levels
	# Uses ntfy (ntfy.sh) to send push notifications to mobile app
	myObj = "VOC level = " + str(VOC) + ", Temperature = " + str(temperature) + "°F"
	requests.post("https://ntfy.sh/jimburger", data=myObj.encode(encoding='utf-8'))
	
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
