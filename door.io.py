import RPi.GPIO as GPIO
from mpd import MPDClient
from wakeonlan import wol
import os
import time
import random

#The GPIO Pin Number for the door switch (BCM)
INPUT_PIN = 26
#The second one, same circuit
INPUT2_PIN = 16
#Global variable to hold whether I'm present
IS_PRESENT = True
#File to hold Timestamp of Last Change
LAST_CHANGE_FILE = '/home/pi/tmp/door.io.change'
#LOG - File
LOG_FILE = '/home/pi/tmp/door.io.log'
#BOUND local IP address of my laptop
MERCURIUS_IP = '192.168.0.102'
#MAC address of enkidu
ENKIDU_MAC = 'E0.CB.4E.DA.68.7F'
#BOUND local IP address of enkidu
ENKIDU_IP = '192.168.0.101'
#Forwarded port to wol enkidu
WOL_PORT = 40000
#DIR with subdirs with mp3-messages
MESSAGES_DIR = '/home/pi/var/text-to-speech/'

def d_print(message, print_time=True):
	if print_time:
		message = time.ctime() + "\n" + message
	print(message)
	with open(LOG_FILE, 'a') as f_log:
		print >> f_log, message
		
def play_rand_message(type):
	os.system("mpg123 " + MESSAGES_DIR + type + "/" + random.choice(os.listdir("/home/pi/var/text-to-speech/" + type + "/")))


def is_mpd_playing():
	client = MPDClient()
	client.connect('localhost', 6600)
	client_state = client.status()['state']
	client.close()
	return client_state == 'play'

def ip_address_present(address):
	return os.system("fping -t50 -c1 " + address) == 0

def start_welcome():
	wol.send_magic_packet(ENKIDU_MAC, ip_address=ENKIDU_IP, port=WOL_PORT)
	play_rand_message('welcome')
	play_rand_message('welcome-joke')

def shutdown():
	play_rand_message('goodbye')
	if ip_address_present(ENKIDU_IP):
		os.system("sudo -u pi ssh morris@" + ENKIDU_IP + " 'systemctl suspend'")

def add_callback(pin):
	GPIO.remove_event_detect(pin)
	GPIO.add_event_detect(pin, GPIO.FALLING, callback=test_open_door, bouncetime=50)
	
def shut_door_end(pin, opening_starttime):
	GPIO.remove_event_detect(pin)
	GPIO.wait_for_edge(pin, GPIO.RISING)
	d_print('and shut after {:.2f} sec'.format(time.time() - opening_starttime), False)
	GPIO.remove_event_detect(pin)
	
def is_leaving_plausible():
	return not is_mpd_playing() and not ip_address_present(MERCURIUS_IP)

def get_last_change():
	open(LAST_CHANGE_FILE, 'a').close()
	with open(LAST_CHANGE_FILE, 'r+') as handle:
		last_change = handle.readline().rstrip('\n')
	if not last_change:
		last_change = time.time()
	return int(last_change)

def write_last_change(change):
	open(LAST_CHANGE_FILR, 'a').close()
	with open(LAST_CHANGE_FILE, 'r+') as handle:
		handle.seek(0)
		handle.write(str(int(change)))
		handle.truncate()
	return true

def test_open_door(pin):
	global last_time_opened, IS_PRESENT
	opening_starttime = time.time()
	if (opening_starttime - last_time_opened) <= 5:
		return False
	time.sleep(0.3)
	for off_probe_counter in range(1,10):
		print '-' * off_probe_counter
		if GPIO.input(pin):
			return False
		time.sleep(0.05)
	d_print('Door was opened')
	last_change = get_last_change()
	if (opening_starttime -last_change) <= 15:
		return False
	if IS_PRESENT:
		if is_leaving_plausible():
			d_print('with Master leaving', False)
			d_print('after he was ' + str(int(opening_starttime - last_change)) + 'sec at home', False)
			IS_PRESENT = False
			write_last_change(opening_starttime)
			shutdown()
	else:
		start_welcome()
		d_print('with Master arriving', False)
		d_print('after he was ' + str(int(opening_starttime - last_change)) + 'sec away from home', False)
		IS_PRESENT = True
		write_last_change(opening_starttime)
	shut_door_end(INPUT2_PIN, opening_starttime)
	last_time_opened = opening_starttime

if __name__ == "__main__":

	GPIO.setmode(GPIO.BCM)
	GPIO.setwarnings(False)
	GPIO.setup(INPUT_PIN, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
	GPIO.setup(INPUT2_PIN, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)

	try:
		last_time_opened = ((time.time()) - 10)
		add_callback(INPUT_PIN)

		while True:
			time.sleep(300)
		
	finally:
		GPIO.cleanup()
