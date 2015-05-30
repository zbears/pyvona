#!/usr/bin/env python
# encoding: utf-8

"""Pyvona : an IVONA python library
Author: Zachary Bears
Contact Email: bears.zachary@gmail.com
Note: Full operation of this library requires the requests and pygame libraries
"""

import datetime
import hashlib
import hmac
import json
import os
import uuid


class PyvonaException(Exception):
    pass

try:
    import pygame
except ImportError:
    pygame_available = False
else:
    pygame_available = True

try:
    import requests
except ImportError:
    msg = 'The requests library is essential for Pyvona operation. '
    msg += 'Without it, Pyvona will not function correctly.'
    raise PyvonaException(msg)


_amazon_date_format = '%Y%m%dT%H%M%SZ'
_date_format = '%Y%m%d'


def create_voice(access_key, secret_key):
    """Creates and returns a voice object to interact with
    """
    return Voice(access_key, secret_key)


class Voice(object):

    """An object that contains all the required methods for interacting
    with the IVONA text-to-speech system
    """
    voice_name = None
    speech_rate = None
    sentence_break = None
    paragraph_break = None
    _codec = "ogg"
    region_options = {
        'us-east': 'us-east-1',
        'us-west': 'us-west-2',
        'eu-west': 'eu-west-1',
    }
    access_key = None
    secret_key = None

    algorithm = 'AWS4-HMAC-SHA256'
    signed_headers = 'content-type;host;x-amz-content-sha256;x-amz-date'
    _region = None
    _host = None

    @property
    def region(self):
        return self._region

    @region.setter
    def region(self, region_name):
        self._region = self.region_options.get(region_name, 'us-east-1')
        self._host = 'tts.{}.ivonacloud.com'.format(self._region)

    @property
    def codec(self):
        return self._codec

    @codec.setter
    def codec(self, codec):
        if codec not in ["mp3", "ogg"]:
            raise PyvonaException(
                "Invalid codec specified. Please choose 'mp3' or 'ogg'")
        self._codec = codec

    def fetch_voice_ogg(self, text_to_speak, filename):
        """Fetch an ogg file for given text and save it to the given file name
        """
        current_codec = self.codec
        self.codec = "ogg"
        self.fetch_voice(text_to_speak, filename)
        self.codec = current_codec

    def fetch_voice(self, text_to_speak, filename):
        """Fetch a voice file for given text and save it to the given file name
        """
        file_extension = ".{codec}".format(codec=self.codec)
        filename += file_extension if not filename.endswith(
            file_extension) else ""
        r = self._send_amazon_auth_packet_v4(
            'POST', 'tts', 'application/json', '/CreateSpeech', '',
            self._generate_payload(text_to_speak), self._region, self._host)
        if r.content.startswith('{'):
            raise PyvonaException('Error fetching voice: {}'.format(r.content))
        else:
            with open(filename, 'wb') as f:
                f.write(r.content)

    def speak(self, text_to_speak):
        """Speak a given text
        """
        if not pygame_available:
            raise PyvonaException(
                "Pygame not installed. Please install to use speech.")

        temp_fname = '{}.ogg'.format(str(uuid.uuid4()))
        self.fetch_voice_ogg(text_to_speak, temp_fname)
        channel = pygame.mixer.Channel(5)
        sound = pygame.mixer.Sound(temp_fname)
        channel.play(sound)
        while channel.get_busy():
            pass
        os.remove(os.getcwd() + '/' + temp_fname)

    def list_voices(self):
        """Returns all the possible voices
        """
        r = self._send_amazon_auth_packet_v4(
            'POST', 'tts', 'application/json', '/ListVoices', '', '',
            self._region, self._host)
        return r.content

    def _generate_payload(self, text_to_speak):
        return json.dumps({
            'Input': {
                'Data': text_to_speak
            },
            'OutputFormat': {
                'Codec': self.codec.upper()
            },
            'Parameters': {
                'Rate': self.speech_rate,
                'SentenceBreak': self.sentence_break,
                'ParagraphBreak': self.paragraph_break
            },
            'Voice': {
                'Name': self.voice_name
            }
        })

    def _send_amazon_auth_packet_v4(self, method, service, content_type,
                                    canonical_uri, canonical_querystring,
                                    request_parameters, region, host):
        """Send a packet to a given amazon server using Amazon's signature Version 4,
        Returns the resulting response object
        """
        # Create date for headers and the credential string
        t = datetime.datetime.utcnow()
        amazon_date = t.strftime(_amazon_date_format)
        date_stamp = t.strftime(_date_format)

        # Step 1: Create canonical request
        payload_hash = self._sha_hash(request_parameters)

        canonical_headers = 'content-type:{}\n'.format(content_type)
        canonical_headers += 'host:{}\n'.format(host)
        canonical_headers += 'x-amz-content-sha256:{}\n'.format(payload_hash)
        canonical_headers += 'x-amz-date:{}\n'.format(amazon_date)

        canonical_request = '\n'.join([
            method, canonical_uri, canonical_querystring, canonical_headers,
            self.signed_headers, payload_hash])

        # Step 2: Create the string to sign
        credential_scope = '{}/{}/{}/aws4_request'.format(
            date_stamp, region, service)
        string_to_sign = '\n'.join([
            self.algorithm, amazon_date, credential_scope,
            self._sha_hash(canonical_request)])

        # Step 3: Calculate the signature
        signing_key = self._get_signature_key(
            self.secret_key, date_stamp, region, service)
        signature = hmac.new(
            signing_key, string_to_sign.encode('utf-8'),
            hashlib.sha256).hexdigest()

        # Step 4: Create the signed packet
        endpoint = 'https://{}{}'.format(host, canonical_uri)
        authorization_header = '{} Credential={}/{}, ' +\
            'SignedHeaders={}, Signature={}'
        authorization_header = authorization_header.format(
            self.algorithm, self.access_key, credential_scope,
            self.signed_headers, signature)
        headers = {
            'Host': host,
            'Content-type': content_type,
            'X-Amz-Date': amazon_date,
            'Authorization': authorization_header,
            'x-amz-content-sha256': payload_hash,
            'Content-Length': len(request_parameters)
        }
        # Send the packet and return the response
        return requests.post(endpoint, data=request_parameters,
                             headers=headers)

    def _sha_hash(self, to_hash):
        return hashlib.sha256(to_hash).hexdigest()

    def _sign(self, key, msg):
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

    def _get_signature_key(self, key, date_stamp, region_name, service_name):
        k_date = self._sign(('AWS4{}'.format(key)).encode('utf-8'), date_stamp)
        k_region = self._sign(k_date, region_name)
        k_service = self._sign(k_region, service_name)
        k_signing = self._sign(k_service, 'aws4_request')
        return k_signing

    def __init__(self, access_key, secret_key):
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
