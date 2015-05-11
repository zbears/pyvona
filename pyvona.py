"""Pyvona : an IVONA python library
Author: Zachary Bears
Note: Full operation of this library requires the requests and pygame libraries
"""
import sys,os,base64, datetime, hashlib, hmac, requests
pygame_available = False
try:
	import pygame
	pygame_available = True
except ImportError:
	pygame_available = False
try:
	import requests
except ImportError:
	print "The requests library is essential for pyvona operation. Please install the library and try again."
	exit()

def createVoice(access_key, secret_key):
	"""Creates and returns a voice object to interact with
	"""
	return Voice(access_key, secret_key)

class Voice:
	"""An object that contains all the required methods for interacting with the IVONA text-to-speech system
	"""
	region = ''
	host = ''
	voice_name = ''
	speech_rate = 'medium'
	sentence_break = '400'
	paragraph_break = '650'
	region_options = {
		'us-east' : 'us-east-1',
		'us-west' : 'us-west-2',
		'eu-west' : 'eu-west-1',
	}
	access_key = ''
	secret_key = ''
	if access_key is None or secret_key is None:
		print 'No IVONA credentials configured. Please add credentials to OS environment vars.'
		print "access key id should be referenced by IVONA_ACCESS_KEY_ID"
		print "secret access key should be referenced by IVONA_SECRET_ACCESS_KEY"
		sys.exit()

	def setRegion(self, regionName):
		"""Change the amazon server region that is interfaced with
		Options are: us-east, us-west, eu-west
		"""
		global region, host, endpoint
		self.region = self.region_options.get(regionName,'us-east-1')
		self.host = 'tts.'+self.region+'.ivonacloud.com'

	def setVoiceName(self, name):
		"""Change the desired speaker's name
		"""
		self.voice_name = name

	def setSpeechRate(self, rate):
		"""Change the speech rate. Default is 'medium'
		"""
		self.speech_rate = rate

	def setSentenceBreak(self, sent_break):
		"""Change the sentence break timing. Default is '400'
		"""
		self.sentence_break = sent_break

	def setParagraphBreak(self,para_break):
		"""Change the paragraph break timing. Default is '650'
		"""
		seft.paragraph_break = para_break

	def fetchVoiceOGG(self,textToSpeak, filename):
		""" Fetch an ogg file for given text and save it to the given file name
		"""
		if not filename.endswith(".ogg"):
			filename+=".ogg"
		r = self._sendAmazon4StepAuthPacket('POST', 'tts', 'application/json', '/CreateSpeech', '', self._generatePayload(textToSpeak), self.region, self.host)
		file = open(filename, 'wb')
		file.write(r.content)
		file.close()

	def speak(self,textToSpeak):
		""" Speak a given text
		"""
		if pygame_available:
			temp_fname = 'temp504032039423433493.ogg'
			self.fetchVoiceOGG(textToSpeak,temp_fname)
			channel = pygame.mixer.Channel(5)
			sound = pygame.mixer.Sound(temp_fname)
			channel.play(sound)
			while channel.get_busy():
				tmp=True
				#Do nothing
			os.remove(os.getcwd()+'/'+temp_fname)
		else:
			print "Please install the pygame library to use this feature."
			exit()

	def listVoices(self):
		""" Prints all the possible voices 
		"""
		r = self._sendAmazon4StepAuthPacket('POST','tts','application/json','/ListVoices','','',self.region,self.host)
		print r.content
		return r.content

	def _generatePayload(self,textToSpeak):
		payload = '{"Input":{"Data":"'+textToSpeak+'"}, "OutputFormat":{"Codec":"OGG"},'
		#payload += '"Parameters" : { "Rate" : "'+self.speech_rate+'", "SentenceBreak" : '+self.sentence_break+', "ParagraphBreak" : '+self.paragraph_break+'}'
		payload += '"Voice" : {"Name":"'+self.voice_name+'"}'
		payload += '}'
		return payload

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
		self.setRegion('us-east')
		self.setVoiceName('Brian')
		self.access_key = access_key
		self.secret_key = secret_key
		if pygame_available:
			pygame.mixer.init()
