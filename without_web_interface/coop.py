'''
Chicken coop automation w/o web interface for raspberry pi.
Opens and closes coop door and tunnel door based on sunrise & sunset.

Author: Michael Appleton
Date: September 26, 2021

'''

import RPi.GPIO as GPIO
import time
import astral
import datetime
from astral.sun import sun
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


GPIO.setmode(GPIO.BCM)

# Create a dictionary called pins to store the pin number, name, and pin state
pins = {
   23 : {'name' : 'Door Close', 'state' : GPIO.HIGH},
   24 : {'name' : 'Door Open', 'state' : GPIO.HIGH},
   5 : {'name' : 'Tunnel Open', 'state' : GPIO.HIGH},
   6 : {'name' : 'Tunnel Close', 'state' : GPIO.HIGH}
   }

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



 
# creating object of the class
# Door('which door', 'open/close', duration in seconds, pin #)
coop_open = Door('coop', 'open', 35, 24)
coop_close = Door('coop', 'close', 50, 23) 
tunnel_open = Door('tunnel', 'open', 40, 5)
tunnel_close = Door('tunnel', 'close', 40, 6)



# Function to add events to coop.log
def log_events(x):
    jobs = scheduler.get_jobs()
    logger.info(x)
    for job in jobs:
        logger.info('scheduled - '+str(job))


# Function to add the daily events to the scheduler
def get_time(period):
   try:
      x = eval('astral.sun.'+period+'(city.observer, date=datetime.date.today(), tzinfo=city.timezone)')
      logger.info('get_time had wifi')
      return x
   except:
      if period == 'sunrise':
         fixed_x = datetime.datetime.combine(datetime.datetime.today(),datetime.time(7,00))
      elif period == 'dusk':
         fixed_x = datetime.datetime.combine(datetime.datetime.today(),datetime.time(19,00))
      logger.info('get_time DID NOT have wifi - using fixed times')
      return fixed_x


# Function to add the daily events to the scheduler
def add_events():
   sunrise = get_time('sunrise')
   dusk = get_time('dusk')
   tunnel_open_time = sunrise + datetime.timedelta(minutes=30)
   scheduler.add_job(coop_open.door_run, 'date', run_date=sunrise, name='Coop Open')
   scheduler.add_job(tunnel_open.door_run, 'date', run_date=tunnel_open_time, name='Tunnel Open')
   scheduler.add_job(coop_close.door_run, 'date', run_date=dusk, name='Coop Close')
   scheduler.add_job(tunnel_close.door_run, 'date', run_date=dusk, name='Tunnel Close')
   log_events('add_events')

if __name__ == '__main__':
    #call add_events to schedule once at boot
    add_events()
    #schedule repeating job to schedule events at 00:10
    scheduler.add_job(add_events, 'interval', hours=24, start_date='2021-09-26 00:10:00')
    log_events('Startup Check')
    while True:
        time.sleep(86400)
