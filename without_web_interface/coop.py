'''
Chicken coop automation w/o web interface for raspberry pi.
Opens and closes coop door and tunnel door based on sunrise & sunset.

Author: Michael Appleton
Date: September 26, 2021

'''

import RPi.GPIO as GPIO
import time
import astral
from astral.sun import sun
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import logging.handlers as handlers

# Define logger to add events to coop.log
logger = logging.getLogger('coop')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s')
logHandler = handlers.RotatingFileHandler('/home/pi/coop_without_web/coop.log', maxBytes=1000000, backupCount=2)
logHandler.setLevel(logging.INFO)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

# Create schedule handler
scheduler = BackgroundScheduler()
scheduler.start()

# Define the location to determine event times
city = astral.LocationInfo(name='Edmonds, WA', region='USA', timezone='US/Pacific', latitude=47.8107, longitude=-122.3774)
fixed_sunrise = datetime.time(7,00)
fixed_dusk = datetime.time(19,00)

GPIO.setmode(GPIO.BCM)

# Create a dictionary called pins to store the gpio # and state
pins = {
   23 : {'name' : 'Door Close', 'state' : GPIO.HIGH},
   24 : {'name' : 'Door Open', 'state' : GPIO.HIGH},
   5 : {'name' : 'Tunnel Open', 'state' : GPIO.HIGH},
   6 : {'name' : 'Tunnel Close', 'state' : GPIO.HIGH},
   25: {'name': 'Blue', 'state': GPIO.HIGH}
   }

'''
UNUSED GPIO
GPIO 26 (Grey wire.  Bad pin?)
GPIO 19 (Purple wire.  Bad pin?)
GPIO 13 (Brn/white)
'''


# Set each pin as an output and make it low
for pin in pins:
   GPIO.setup(pin, GPIO.OUT)
   GPIO.output(pin, GPIO.HIGH)

#class for the door functions.  Coop/tunnel, open/close
class Door:
    
    # parameterized constructor
    def __init__(self, door, direction, duration, gpio_pin):
        self.door = door
        self.direction = direction
        self.duration = duration
        self.gpio_pin = gpio_pin
     

    def door_run(self):
        GPIO.output(self.gpio_pin, GPIO.LOW)
        time.sleep(self.duration)
        GPIO.output(self.gpio_pin, GPIO.HIGH)
        logger.info(str(self.door)+'-'+str(self.direction))


#class for On/Off Functions ie: Coop Light
class OnOff:

    # parameterized constructor
    def __init__(self, item, onoff, gpio_pin):
        self.item = item
        self.onoff = onoff
        self.gpio_pin = gpio_pin

    def onoff_run(self):
        if self.onoff == 'on':
            GPIO.output(self.gpio_pin, GPIO.LOW)
        elif self.onoff == 'off':
            GPIO.output(self.gpio_pin, GPIO.HIGH)
        logger.info(str(self.item) + '-' + str(self.onoff))


# creating objects of the classes
# Door('which door', 'open/close', duration in seconds, pin #)
# OnOff('which item', 'on' or 'off', pin #)
coop_open = Door('coop', 'open', 35, 24)
coop_close = Door('coop', 'close', 50, 23) 
tunnel_open = Door('tunnel', 'open', 40, 5)
tunnel_close = Door('tunnel', 'close', 40, 6)
coop_light_on = OnOff('coop light', 'on', 25)
coop_light_off = OnOff('coop light', 'off', 25)




# Function to add events to coop.log
def log_events(x):
    jobs = scheduler.get_jobs()
    logger.info(x)
    for job in jobs:
        logger.info('scheduled - '+str(job))


# Function to add the daily events to the scheduler
def get_time(period):
   global fixed_sunrise 
   global fixed_dusk
   try:
      x = eval('astral.sun.'+period+'(city.observer, date=datetime.date.today(), tzinfo=city.timezone)')
      if period == 'sunrise':
         fixed_sunrise = x.time()
      elif period == 'dusk':
         fixed_dusk = x.time()
      logger.info('get_time had wifi')
      return x
   except:
      if period == 'sunrise':
         fixed_x = datetime.datetime.combine(datetime.datetime.today(),fixed_sunrise)
      elif period == 'dusk':
         fixed_x = datetime.datetime.combine(datetime.datetime.today(),fixed_dusk)
      logger.info('get_time DID NOT have wifi - using fixed times')
      return fixed_x


# Function to add the daily events to the scheduler
def add_events():
   sunrise = get_time('sunrise')
   sunset = get_time('sunset')
   dusk = get_time('dusk')
   tunnel_open_time = sunrise + datetime.timedelta(minutes=30)
   needed_coop_light = datetime.timedelta(minutes=int(870 - ((sunset - sunrise) / datetime.timedelta(minutes=1))))
   scheduler.add_job(coop_open.door_run, 'date', run_date=sunrise, name='Coop Open')
   scheduler.add_job(tunnel_open.door_run, 'date', run_date=tunnel_open_time, name='Tunnel Open')
   scheduler.add_job(coop_close.door_run, 'date', run_date=dusk, name='Coop Close')
   scheduler.add_job(tunnel_close.door_run, 'date', run_date=dusk, name='Tunnel Close')
   if needed_coop_light > datetime.timedelta(seconds=300):
       coop_light_on_time = sunrise - needed_coop_light
       coop_light_off_time = sunrise
       scheduler.add_job(coop_light_on.onoff_run, 'date', run_date=coop_light_on_time, name='Coop Light On')
       scheduler.add_job(coop_light_off.onoff_run, 'date', run_date=coop_light_off_time, name='Coop Light Off')
   log_events('add_events')

if __name__ == '__main__':
    #call add_events to schedule once at boot
    add_events()
    #schedule repeating job to schedule events at 00:10/01:10 dst/std 
    scheduler.add_job(add_events, 'interval', hours=24, start_date='2021-09-26 01:10:00')
    log_events('Startup Check')
    while True:
        time.sleep(86400)
