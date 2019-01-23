#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from Renderer import Renderer
from Components.VariableText import VariableText
#import library to do http requests:
import urllib2
from enigma import eLabel, ePixmap
#import easy to use xml parser called minidom:
from xml.dom.minidom import parseString
from Components.config import config, configfile, ConfigSubsection, ConfigSelection, ConfigNumber, ConfigSelectionNumber, ConfigYesNo, ConfigText, ConfigDateTime, ConfigInteger
from threading import Timer, Thread
from time import time, strftime, localtime
from twisted.web.client import getPage
import sys
#from twisted.python import log
#log.startLogging(sys.stdout)

import json

g_updateRunning = False
g_isRunning = False

def initWeatherConfig():
	config.plugins.SimpleWeather = ConfigSubsection()

	#SimpleWeather
	config.plugins.SimpleWeather.enabled = ConfigYesNo(default=False)
	config.plugins.SimpleWeather.woeid = ConfigNumber(default=2510911) #Location (visit https://openweathermap.org/)
	config.plugins.SimpleWeather.apikey = ConfigText(default="ba8e0e8e9042dcb7e1ba98cbdd21f6cf")
	config.plugins.SimpleWeather.tempUnit = ConfigSelection(default="Celsius", choices = [
		("Celsius", _("Celsius")),
		("Fahrenheit", _("Fahrenheit"))
	])
	config.plugins.SimpleWeather.refreshInterval = ConfigSelectionNumber(default = 90, stepwidth = 1, min = 0, max = 1440, wraparound = True)

	## RENDERER CONFIG:
	config.plugins.SimpleWeather.currentWeatherDataValid = ConfigYesNo(default=False)
	config.plugins.SimpleWeather.currentLocation = ConfigText(default="N/A")
	config.plugins.SimpleWeather.currentWeatherCode = ConfigText(default="(")
	config.plugins.SimpleWeather.currentWeatherText = ConfigText(default="N/A")
	config.plugins.SimpleWeather.currentWeatherTemp = ConfigText(default="0")

	config.plugins.SimpleWeather.forecastTodayCode = ConfigText(default="(")
	config.plugins.SimpleWeather.forecastTodayDay = ConfigText(default="N/A")
	config.plugins.SimpleWeather.forecastTodayText = ConfigText(default="N/A")
	config.plugins.SimpleWeather.forecastTodayTempMin = ConfigText(default="0")
	config.plugins.SimpleWeather.forecastTodayTempMax = ConfigText(default="0")

	config.plugins.SimpleWeather.forecastTomorrowCode = ConfigText(default="(")
	config.plugins.SimpleWeather.forecastTomorrowDay = ConfigText(default="N/A")
	config.plugins.SimpleWeather.forecastTomorrowText = ConfigText(default="N/A")
	config.plugins.SimpleWeather.forecastTomorrowTempMin = ConfigText(default="0")
	config.plugins.SimpleWeather.forecastTomorrowTempMax = ConfigText(default="0")

	config.plugins.SimpleWeather.save()
	configfile.save()

initWeatherConfig()

class SimpleWeatherWidget(Renderer, VariableText, Thread):

	def __init__(self, once=False, check=False):
		Renderer.__init__(self)
		VariableText.__init__(self)
		Thread.__init__(self)
		self.woeid = config.plugins.SimpleWeather.woeid.value
		self.once = once
		self.check = check
		self.Timer = None
		self.refreshcnt = 0
		self.error = False
		if not g_isRunning or self.once or self.check:
			self.getWeather()

	GUI_WIDGET = eLabel

	def __del__(self):
		try:
			if self.Timer is not None:
				self.Timer.cancel()
		except:
			pass

	def startTimer(self, refresh=False):
		seconds = int(config.plugins.SimpleWeather.refreshInterval.value) * 60

		if seconds < 60:
			seconds = 300

		if refresh:
			if self.refreshcnt >= 6:
				self.refreshcnt = 0
				seconds=300
			else:
				seconds=10

		try:
			if self.Timer:
				try:
					self.Timer.cancel()
					self.Timer = None
				except:
					pass
		except:
			pass

		self.Timer = Timer(seconds, self.getWeather)
		self.Timer.start()

	def onShow(self):
		self.text = config.plugins.SimpleWeather.currentWeatherCode.value

	def getWeather(self):
		self.startTimer()

		# skip if weather-widget is disabled
		if config.plugins.SimpleWeather.enabled.value == "False":
			config.plugins.SimpleWeather.currentWeatherDataValid.value = False
			return

		global g_updateRunning
		#if g_updateRunning:
		#	print "[SimpleWeather] lookup for ID " + str(self.woeid) + " skipped, allready running..."
		#	return
		g_updateRunning = True
		Thread(target = self.getWeatherThread).start()

	def error(self, error = None):
		errormessage = ""
		if error is not None:
			errormessage = str(error.getErrorMessage())
			print errormessage

	def getWeatherThread(self):
		global g_updateRunning
		#try:
		#	print "[SimpleWeather] lookup for ID " + str(self.woeid)
		#except:
		#	pass
		#text = "[SimpleWeather] lookup for ID " + str(self.woeid)
		#if self.check:
		#	self.writeCheckFile(text)
		#print text

		#http='api.openweathermap.org/data/2.5/weather?' #current weather
		#http='api.openweathermap.org/data/2.5/forecast/daily?' #16day/daily forcast

		language = config.osd.language.value
		apikey = "&appid=%s" % config.plugins.SimpleWeather.apikey.value
		city="id=%s" % self.woeid
		feedurl = "http://api.openweathermap.org/data/2.5/weather?%s&lang=%s&units=metric%s" % (city,language[:2],apikey)
		getPage(feedurl).addCallback(self.jsonCallback).addErrback(self.error)
		if not self.check:
			feedurl = "http://api.openweathermap.org/data/2.5/forecast?%s&lang=%s&units=metric&cnt=1%s" % (city,language[:2],apikey)
			getPage(feedurl).addCallback(self.jsonCallback).addErrback(self.error)

	def jsonCallback(self, jsonstring):
		d = json.loads(jsonstring)
		if 'list' in d and 'cnt' in d:
			temp_min_cnt_0 = d['list'][0]['main']['temp_min']
			temp_max_cnt_0 = d['list'][0]['main']['temp_max']
			weather_code_cnt_0 = d['list'][0]['weather'][0]['id']
			config.plugins.SimpleWeather.forecastTomorrowTempMax.value = str(int(round(temp_max_cnt_0)))
			config.plugins.SimpleWeather.forecastTomorrowTempMin.value = str(int(round(temp_min_cnt_0)))
			config.plugins.SimpleWeather.forecastTomorrowCode.value = self.ConvertCondition(weather_code_cnt_0)
		else:
			if 'name' in d:
				name = d['name']
				config.plugins.SimpleWeather.currentLocation.value = str(name)
			if 'id' in d:
				id = d['id']
			if 'main' in d and 'temp' in d['main']:
				temp = d['main']['temp']
				config.plugins.SimpleWeather.currentWeatherTemp.value = str(int(round(temp)))
			if 'temp_max' in d['main']:
				temp_max = d['main']['temp_max']
				config.plugins.SimpleWeather.forecastTodayTempMax.value = str(int(round(temp_max)))
			if 'temp_min' in d['main']:
				temp_min = d['main']['temp_min']
				config.plugins.SimpleWeather.forecastTodayTempMin.value = str(int(round(temp_min)))
			if 'weather' in d:
				weather_code = d['weather'][0]['id']
				config.plugins.SimpleWeather.currentWeatherCode.value = self.ConvertCondition(weather_code)
			if self.check:
				text = "%s|%s|%s°|%s°|%s°" %(id,name,temp,temp_max,temp_min)
				self.writeCheckFile(text)
				g_updateRunning = False
				return
		self.save()
		g_updateRunning = False
		self.refreshcnt = 0

	def save(self):
		config.plugins.SimpleWeather.save()
		configfile.save()

	def getText(self,nodelist):
		rc = []
		for node in nodelist:
			if node.nodeType == node.TEXT_NODE:
				rc.append(node.data)
		return ''.join(rc)

	def ConvertCondition(self, c):
		c = int(c)
		condition = "("
		if c == 800:
			condition = "B" # Sonne am Tag 
		elif c == 801:
			condition = "H" # Bewoelkt Sonning 
		elif c == 802:
			condition = "J" # Nebel Sonning
		elif c == 711 or c == 721:
			condition = "L" # Bewoelkt Nebeling
		elif c == 701 or c == 731 or c == 741 or c == 751 or c == 761 or c == 762:
			condition = "M" # Nebel
		elif c == 803 or c == 804:
			condition = "N" # Bewoelkt
		elif c == 202 or c == 212 or c == 221:
			condition = "O" # Gewitter
		elif c == 200 or c == 210 or c == 230 or c == 231 or c == 232:
			condition = "P " # Gewitter leicht
		elif c == 500 or  c == 501:
			condition = "Q" # Leicher Regen
		elif c == 520 or c == 521 or c == 531 or c == 300 or c == 301 or c == 302 or c == 310 or c == 311 or c == 312 or c == 313 or c == 314 or c == 321:
			condition = "R" # Mittlere Regen
		elif c == 771 or c == 781:
			condition = "S" # Starker Wind
		elif c == 502:
			condition = "T" # Wind und Regen
		elif c == 531 or c == 531:
			condition = "U" # Normaler Regen
		elif c == 600 or c == 601 or c == 616 or c == 620:
			condition = "V" # Schnee
		elif c == 611 or c == 612 or c == 615:
			condition = "W" # Schnee gefahr
		elif c == 602 or c == 622 or c == 621 or c == 511:
			condition = "X" # Starker Schnee
		elif c == 504 or c == 503:
			condition = "Y" # Stark Regen
		elif c == 803 or c == 804:
			condition = "Z" # Stark Bewoelkt
		else:
			condition = ")"
		return str(condition)

	def getTemp(self,temp):
		if config.plugins.SimpleWeather.tempUnit.value == "Fahrenheit":
			return str(int(round(float(temp),0)))
		else:
			celsius = (float(temp) - 32 ) * 5 / 9
			return str(int(round(float(celsius),0)))
