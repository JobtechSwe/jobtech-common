import logging
import base64
import binascii
import re
import json
from flask import request
from flask_restplus import abort
from pymemcache.client import base
from jobtech.common import settings
from jobtech.common.repository import elastic

log = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"\"?([-a-zA-Z0-9.`?{}]+@\w+\.\w+)\"?")


def json_serializer(key, value):
    if type(value) == str:
        return (value, 1)
    return (json.dumps(value), 2)


def json_deserializer(key, value, flags):
    if flags == 0:
        return None
    if flags == 1:
        return value.decode('utf-8')
    if flags == 2:
        return json.loads(value.decode('utf-8'))
    raise Exception("Unknown serialization format")


client = base.Client(('localhost', 11211),
                     serializer=json_serializer,
                     deserializer=json_deserializer, ignore_exc=True)


def check_api_key_simple(func):
    def wrapper(*args, **kwargs):
        apikey = request.headers.get(settings.APIKEY)
        decoded_key = _decode_key(apikey)
        if EMAIL_REGEX.match(decoded_key):
            log.debug("API key %s is valid." % decoded_key)
            return func(*args, **kwargs)
        log.info("Failed validation for key '%s'" % decoded_key)
        abort(401, message="You're no monkey!")

    return wrapper


def check_api_key(api_identifier):
    def real_check_api_key_decorator(func):
        def wrapper(*args, **kwargs):
            memcache_key = "valid_api_keys_%s" % api_identifier
            valid_api_keys = client.get(memcache_key)
            if not valid_api_keys:
                apikeys_id = "%s_%s" % (settings.ES_APIKEYS_DOC_ID, api_identifier)
                log.debug("Reloading API keys for id %s" % apikeys_id)
                new_keys = elastic.get_source(index=settings.ES_SYSTEM_INDEX,
                                              id=apikeys_id, ignore=404)
                if new_keys:
                    log.debug("Updating API keys from ES")
                    valid_api_keys = new_keys
                    try:
                        client.set(memcache_key, valid_api_keys, 60)
                    except ConnectionRefusedError:
                        log.debug("Memcache not available, reloading keys for " +
                                  "each request.")
            apikey = request.headers.get(settings.APIKEY)
            if valid_api_keys and apikey in valid_api_keys.get('validkeys', []):
                decoded_key = _decode_key(apikey)
                if decoded_key == 'Invalid Key':
                    decoded_key = apikey
                log.debug("API key \"%s\" is valid." % decoded_key)
                return func(*args, **kwargs)
            log.info("Failed validation for key '%s'" % apikey)
            abort(401, message="Missing or invalid API key")

        return wrapper

    return real_check_api_key_decorator


# Decodes the API which is in base64 format
def _decode_key(apikey):
    decoded = apikey if apikey is not None else 'Invalid Key: None'
    if apikey:
        for i in range(3):
            try:
                decoded = base64.urlsafe_b64decode(apikey).decode('utf-8').strip()
                break
            except binascii.Error as e:
                log.debug("Failed to decode api key: %s: %s" % (apikey, e))
                pass
            except UnicodeDecodeError as u:
                log.debug("Failed to decode utf-8 key: %s: %s" % (apikey, u))
                decoded = 'Invalid Key'  # Prevents users from sending plain email adress
            # Reappend trailing '=' to find correct padding
            apikey = "%s=" % apikey
    return decoded
