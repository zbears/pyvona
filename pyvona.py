"""Pyvona : an IVONA python library
Author: Zachary Bears
Contact Email: bears.zachary@gmail.com
Note: Full operation of this library requires the requests and pygame libraries
"""
# TODO switch to urllib instead of requests
# TODO make code beautiful
import sys,os,base64, datetime, hashlib, hmac, json
pygame_available = False
try:
	import pygame
	pygame_available = True
except ImportError:
	pass
try:
	import requests
except ImportError:
	raise PyvonaException('The requests library is essential for Pyvona operation. Without it, Pyvona will not function correctly.')

def createVoice(access_key, secret_key):
	"""Creates and returns a voice object to interact with
	"""
	return Voice(access_key, secret_key)

class Voice(object):
	"""An object that contains all the required methods for interacting with the IVONA text-to-speech system
	"""

	voice_name = None
	speech_rate = None
	sentence_break = None
	paragraph_break = None
	region_options = {
		'us-east' : 'us-east-1',
		'us-west' : 'us-west-2',
		'eu-west' : 'eu-west-1',
	}
	access_key = ''
	secret_key = ''

	_region = None
	_host = None

	@property
	def region(self):
		return self._region
	@region.setter
	def region(self,region_name):
		self._region = self.region_options.get(region_name,'us-east-1')
		self._host = 'tts.{}.ivonacloud.com'.format(self._region)

	def fetchVoiceOGG(self,textToSpeak, filename):
		""" Fetch an ogg file for given text and save it to the given file name
		"""
		if not filename.endswith(".ogg"):
			filename+=".ogg"
		r = self._sendAmazon4StepAuthPacket('POST', 'tts', 'application/json', '/CreateSpeech', '', self._generatePayload(textToSpeak), self._region, self._host)
		file = open(filename, 'wb')
		file.write(r.content)
		file.close()

	def speak(self,textToSpeak):
		""" Speak a given text
		"""
		if not pygame_available:
			raise PyvonaException("Pygame not installed. Please install to use speech.")
		temp_fname = 'temp504032039423433493.ogg'
		self.fetchVoiceOGG(textToSpeak,temp_fname)
		channel = pygame.mixer.Channel(5)
		sound = pygame.mixer.Sound(temp_fname)
		channel.play(sound)
		while channel.get_busy():
			pass
		os.remove(os.getcwd()+'/'+temp_fname)
		

	def listVoices(self):
		""" Returns all the possible voices 
		"""
		r = self._sendAmazon4StepAuthPacket('POST','tts','application/json','/ListVoices','','',self.region,self.host)
		return r.content

	def _generatePayload(self,textToSpeak):
		payload = {
			'Input': {
				'Data': textToSpeak
			},
			'OutputFormat': {
				'Codec': 'OGG'
			},
			'Parameters' : {
				'Rate' : self.speech_rate,
				'SentenceBreak' : self.sentence_break,
				'ParagraphBreak' : self.paragraph_break
			},
			'Voice' : {
				'Name' : self.voice_name
			}

		}
		return json.dumps(payload)

	def _sendAmazon4StepAuthPacket(self,method,service,content_type,canonical_uri,canonical_querystring,request_parameters,region,host):
		"""Send a packet to a given amazon server using Amazon's signature Version 4,
		Returns the resulting response object
		"""
		# Create date for headers and the credential string
		t = datetime.datetime.utcnow()
		amz_date = t.strftime('%Y%m%dT%H%M%SZ')
		date_stamp = t.strftime('%Y%m%d')
		# Step 1: Create canonical request
		canonical_headers = 'content-type:'+content_type+'\n'+'host:'+host+'\n'+ \
			'x-amz-content-sha256:'+ hashlib.sha256(request_parameters).hexdigest() +'\n'+ 'x-amz-date:'+amz_date+'\n'
		signed_headers = 'content-type;host;x-amz-content-sha256;x-amz-date'
		payload_hash = hashlib.sha256(request_parameters).hexdigest()
		canonical_request = method+'\n'+canonical_uri+'\n'+canonical_querystring+'\n'+ \
							canonical_headers+'\n'+signed_headers+'\n'+payload_hash
		# Step 2: Create the string to sign
		algorithm = 'AWS4-HMAC-SHA256'
		credential_scope = date_stamp+'/'+region+'/'+service+'/'+'aws4_request'
		string_to_sign = algorithm+'\n'+amz_date+'\n'+credential_scope+'\n'+hashlib.sha256(canonical_request).hexdigest()
		# Step 3: Calculate the signature
		signing_key = self._getSignatureKey(self.secret_key,date_stamp,region,service)
 		signature = hmac.new(signing_key,(string_to_sign).encode('utf-8'),hashlib.sha256).hexdigest()
 		# Step 4: Create the signed packet
		endpoint = 'https://'+host+canonical_uri
		authorization_header = algorithm + ' ' + 'Credential=' + self.access_key + '/' + credential_scope + ', ' + \
 			'SignedHeaders=' + signed_headers + ', ' + 'Signature='+signature
 		headers = { 'Host':host,
 					'Content-type':content_type,
 					'X-Amz-Date':amz_date,
 					'Authorization':authorization_header,
 					'x-amz-content-sha256':payload_hash,
 					'Content-Length':len(request_parameters)}
 		# Send the packet and return the response
 		return requests.post(endpoint, data=request_parameters, headers=headers)

 	def _sign(self,key,msg):
		return hmac.new(key,msg.encode('utf-8'),hashlib.sha256).digest()

	def _getSignatureKey(self,key, date_stamp, regionName, serviceName):
		kDate = self._sign(('AWS4'+key).encode('utf-8'),date_stamp)
		kRegion = self._sign(kDate, regionName)
		kService = self._sign(kRegion,serviceName)
		kSigning = self._sign(kService, 'aws4_request')
		return kSigning

	def __init__(self, access_key,secret_key):
		"""Set initial voice object parameters
		"""
		self.region = 'us-east'
		self.voice_name = 'Brian'
		self.access_key = access_key
		self.secret_key = secret_key
		self.speech_rate = 'medium'
		self.sentence_break = 400
		self.paragraph_break = 650
		if pygame_available:
			pygame.mixer.init()

class PyvonaException(Exception):
	pass
