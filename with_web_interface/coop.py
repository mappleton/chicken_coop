'''
Chicken coop automation with web interface for raspberry pi.
Opens and closes coop door and tunnel door based on sunrise & sunset.
Displays temp, humidity, shows video feed from coop.

Author: Michael Appleton
Date: September 26, 2021

'''

import RPi.GPIO as GPIO
from flask import Flask, render_template, request, Response, Blueprint, jsonify
from flask_cors import CORS, cross_origin
import time
import sys
import cv2
sys.path.append('/home/pi/.local/lib/python3.7/site-packages')
import picamera
import Adafruit_DHT
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
logHandler = handlers.RotatingFileHandler('/home/pi/coop.log', maxBytes=1000000, backupCount=2)
logHandler.setLevel(logging.INFO)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

scheduler = BackgroundScheduler()
scheduler.start()

temp_sensor = Adafruit_DHT.DHT22
city = astral.LocationInfo(name='Edmonds, WA', region='USA', timezone='US/Pacific', latitude=47.8107, longitude=-122.3774)
door_in_use = 'no'
fixed_sunrise = datetime.time(7,00)
fixed_dusk = datetime.time(19,00)

# app = Flask(__name__)
app = Flask(__name__, static_url_path='/')


from video import videoStreamBp
app.register_blueprint(videoStreamBp)


GPIO.setmode(GPIO.BCM)

# Create a dictionary called pins to store the pin number, name, and pin state:
pins = {
   23 : {'name' : 'Door Close', 'state' : GPIO.HIGH},
   24 : {'name' : 'Door Open', 'state' : GPIO.HIGH},
   25 : {'name' : 'Camera IR', 'state' : GPIO.HIGH},
   26 : {'name' : 'Coop LED', 'state' : GPIO.HIGH},
   #19 : {'name' : 'Extra - disconnected', 'state' : GPIO.HIGH},
   5 : {'name' : 'Tunnel Open', 'state' : GPIO.HIGH},
   6 : {'name' : 'Tunnel Close', 'state' : GPIO.HIGH}
   }

# Set each pin as an output and make it low:
for pin in pins:
   GPIO.setup(pin, GPIO.OUT)
   GPIO.output(pin, GPIO.HIGH)


#class for the timed door functions.  Coop/tunnel, open/close
class Door:
    
    # parameterized constructor
   def __init__(self, door, direction, duration, gpio_pin):
      self.door = door
      self.direction = direction
      self.duration = duration
      self.gpio_pin = gpio_pin
     

   def door_run(self):
      global door_in_use
      if door_in_use == 'yes':
         logger.info('DOOR IN USE - DID NOT RUN '+str(self.door)+'-'+str(self.direction))
      elif door_in_use == 'no':
         door_in_use = 'yes'
         GPIO.output(self.gpio_pin, GPIO.LOW)
         time.sleep(self.duration)
         GPIO.output(self.gpio_pin, GPIO.HIGH)
         logger.info(str(self.door)+'-'+str(self.direction))
         time.sleep(1)
         door_in_use = 'no'



 
# creating object for class Door
# Door('which door', 'open/close', duration in seconds, pin #)
coop_open = Door('coop', 'open', 35, 24)
coop_close = Door('coop', 'close', 50, 23) 
tunnel_open = Door('tunnel', 'open', 40, 5)
tunnel_close = Door('tunnel', 'close', 40, 6)



#class for the on/off functions.  IR for camera, coop light, etc
class On_off:
    
    # parameterized constructor
   def __init__(self, item, on_or_off, gpio_pin):
      self.item = item
      self.on_or_off = on_or_off
      self.gpio_pin = gpio_pin
     

   def trigger(self):
      #high == off, low == on
      if self.on_or_off == 'on':
         GPIO.output(self.gpio_pin, GPIO.LOW)
         logger.info(str(self.item)+'-'+str(self.on_or_off))
      elif self.on_or_off == 'off':
         GPIO.output(self.gpio_pin, GPIO.HIGH)
         logger.info(str(self.item)+'-'+str(self.on_or_off))
         
 
# creating object for class On_off
# On_off('which item', 'on or off', pin #) - could make this a toggle but wanted a definite off
ir_on = On_off('IR light', 'on', 25)
ir_off = On_off('IR light', 'off', 25) 
coop_light_on = On_off('Coop light', 'on', 26)
coop_light_off = On_off('Coop light', 'off', 26)


# Function to add events to coop.log
def log_events(x):
   jobs = scheduler.get_jobs()
   logger.info(x)
   for job in jobs:
      logger.info('scheduled - '+str(job))


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
   dusk = get_time('dusk')
   tunnel_open_time = sunrise + datetime.timedelta(minutes=30)
   scheduler.add_job(coop_open.door_run, 'date', run_date=sunrise, name='Coop Open')
   scheduler.add_job(tunnel_open.door_run, 'date', run_date=tunnel_open_time, name='Tunnel Open')
   scheduler.add_job(coop_close.door_run, 'date', run_date=dusk, name='Coop Close')
   scheduler.add_job(tunnel_close.door_run, 'date', run_date=dusk, name='Tunnel Close')
   log_events('add_events')


@app.route("/")

def main():
   humidity, temperature = Adafruit_DHT.read_retry(temp_sensor, 4)
   if humidity == None:
      humidity = 0.0
   if temperature == None:
      temperature = 0.0
   timeNow = datetime.datetime.now().strftime('%A, %B %d  %-H:%M')
   sunrise = get_time('sunrise').strftime('%m-%d-%y %H:%M')
   dusk = get_time('dusk').strftime('%m-%d-%y %H:%M')
   jobs = scheduler.get_jobs()

   # Put the pin dictionary into the template data dictionary:
   templateData = {
      'time': timeNow,
      'temp': round(((temperature*1.8)+32),1),
      'hum'	: round(humidity,1),
      'sunrise' : sunrise,
      'dusk' : dusk,
      'jobs' : jobs,
      'fixed_sunrise' : fixed_sunrise.strftime('%H:%M'),
      'fixed_dusk' : fixed_dusk.strftime('%H:%M')
      }
   # Pass the template data into the template main.html and return it to the user
   return render_template('main.html', **templateData)


videoStreamBp = Blueprint('video_stream', __name__)

# Raspberry Pi camera module (requires picamera package)
def gen():
   camera = cv2.VideoCapture(0)

   while True:
      ret, img = camera.read()

      if ret:
         frame = cv2.imencode('.jpg', img)[1].tobytes()
         yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@videoStreamBp.route('/videopi')
def video_stream():
   return Response(gen(),mimetype='multipart/x-mixed-replace; boundary=frame')

#--------------routes for ajax buttons 

@app.route('/manualcoopclose')
def manualcoopclose():
    coop_close.door_run()
    logger.info('Coop Closed via web button')
    return jsonify(result='Closed coop')

@app.route('/manualcoopopen')
def manualcoopopen():
    coop_open.door_run()
    logger.info('Coop Opened via web button')
    return jsonify(result='Opened coop')

@app.route('/manualtunnelclose')
def manualtunnelclose():
    tunnel_close.door_run()
    logger.info('Tunnel Closed via web button')
    return jsonify(result='Closed tunnel')

@app.route('/manualtunnelopen')
def manualtunnelopen():
    tunnel_open.door_run()
    logger.info('Tunnel Opened via web button')
    return jsonify(result='Opened tunnel')

@app.route('/manualiron')
def manualiron():
    ir_on.trigger()
    logger.info('IR on via web button')
    return jsonify(result='Turned IR on')

@app.route('/manualiroff')
def manualiroff():
    ir_off.trigger()
    logger.info('IR off via web button')
    return jsonify(result='Turned IR off')

@app.route('/manualcooplighton')
@cross_origin()
def manualcooplighton():
    coop_light_on.trigger()
    logger.info('Cooop light on via web button')
    return jsonify(result='Turned light on')

@app.route('/manualcooplightoff')
def manualcooplightoff():
    coop_light_off.trigger()
    logger.info('Coop light off via web button')
    return jsonify(result='Turned light off')

if __name__ == '__main__':
   #call add_events to schedule once at boot
   add_events()
   #schedule repeating job to schedule events at 00:10
   scheduler.add_job(add_events, 'interval', hours=24, start_date='2021-09-26 00:10:00')
   log_events('Startup Check')
   app.run(host='0.0.0.0', debug=True)

