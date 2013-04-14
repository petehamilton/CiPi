#! /usr/bin/env python

import time
import json
import urllib2
import random
import sys
import getopt
import RPi.GPIO as GPIO

# Set mode to use board numbering system
GPIO.setmode(GPIO.BOARD)

# Pi Pin Configs
GREEN_PIN  = 15
YELLOW_PIN = 13
RED_PIN    = 11

# Circle CI Config
TOKEN = None
USER = None
REPO_NAME = None
BRANCH = 'master'
INTERVAL = 10


class BuildStatus:
  GOOD    = 0
  UNKNOWN = 1
  BAD     = 2

class Light:
  def __init__(self, pin):
    self.pin = pin
    GPIO.setup(pin, GPIO.OUT)
    self.switch_on()

  def switch_off(self):
    GPIO.output(self.pin, GPIO.HIGH)

  def switch_on(self):
    GPIO.output(self.pin, GPIO.LOW)

  def cleanup():
    self.switch_off()

class TrafficLight:
  def __init__(self, green_light, yellow_light, red_light, initial_build_status=BuildStatus.UNKNOWN):
    self.green_light = green_light
    self.yellow_light = yellow_light
    self.red_light = red_light
    self.build_status = initial_build_status
 
    # Set up output channel
    for light in self.all_lights():  
      light.switch_off()

  def set_build_status(self, build_status):
    self.build_status = build_status
    self.update_lights()

  def update_lights(self):
    self.switch_all_off()
    if self.build_status == BuildStatus.GOOD:
      self.green_light.switch_on()
    elif self.build_status == BuildStatus.BAD:
      self.red_light.switch_on()
    else:
      self.yellow_light.switch_on()

  def all_lights(self):
    return [self.green_light, self.yellow_light, self.red_light]

  def cleanup(self):
   for light in self.all_lights():
     light.cleanup() 
   GPIO.cleanup()

  def switch_all_on(self):
    for light in self.all_lights():
      light.switch_on()
  
  def switch_all_off(self):
    for light in self.all_lights():
      light.switch_off()

  def lightshow(self):
    for i in range(0, 50):
      self.switch_all_off()
      random.sample(self.all_lights(), 1)[0].switch_on()
      time.sleep(0.1)

class CircleCIChecker:
  def __init__(self, token, user, repo_name, branch='master'):
    self.token = token
    self.user = user
    self.repo_name = repo_name
    self.branch = branch

  def circleci_endpoint(self):
    url_string = 'https://circleci.com/api/v1/project/%s/%s/tree/%s?circle-token=%s'
    return url_string % (self.user, self.repo_name, self.branch, self.token)

  def get_circleci_build_status(self):
    url = self.circleci_endpoint()
    request = urllib2.Request(url)
    request.add_header('Accept', 'application/json')
    response = urllib2.urlopen(request)
    result = json.loads(response.read())
    return result[0]['status']

  def get_build_status(self):
    status = self.get_circleci_build_status()
    return {
      'success':   BuildStatus.GOOD,
      'fixed':     BuildStatus.GOOD,
      'cancelled': BuildStatus.UNKNOWN,
      'not_run':   BuildStatus.UNKNOWN,
      'failed':    BuildStatus.BAD,
    }.get(status, BuildStatus.UNKNOWN)

def parse_options():
  global TOKEN, USER, REPO_NAME, BRANCH, INTERVAL

  argv = sys.argv[1:]

  help_message = "Usage: ci_pi.py TOKEN USER REPO_NAME [-b BRANCH] [-n INTERVAL]"

  if len(argv) < 3:
    print help_message
    sys.exit(2)

  TOKEN = argv.pop(0)
  USER = argv.pop(0)
  REPO_NAME = argv.pop(0)
  print REPO_NAME
  try:
    opts, args = getopt.getopt(argv[4:], "hb:n:", ["branch=", "interval="])
  except getopt.GetoptError:
    print "ci_pi.py TOKEN USER REPO_NAME -b BRANCH -n INTERVAL"
    sys.exit(2)
  
  for opt, args in opts:
    if opt in ('-h', '--help'):
      print help_message
    elif opt in ('-b', '--branch'):
      BRANCH = arg
    elif opt in ('-n', '--interval'):
      INTERVAL = arg

# Create a CI Checker & update every CHECK_INTERVAL
def run():
  cci = CircleCIChecker(TOKEN, USER, REPO_NAME, BRANCH)
  traffic_light = TrafficLight(Light(GREEN_PIN), Light(YELLOW_PIN), Light(RED_PIN))
  while True:
    status = cci.get_build_status()
    traffic_light.set_build_status(status)
    time.sleep(INTERVAL)  

if __name__ == '__main__':
  parse_options()
  run()