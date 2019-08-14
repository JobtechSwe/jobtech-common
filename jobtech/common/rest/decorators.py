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


memcache = base.Client(('localhost', 11211),
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


def check_api_key(api_identifier, rate_limit=None):
    def real_check_api_key_decorator(func):
        def wrapper(*args, **kwargs):
            memcache_key = "valid_api_keys_%s" % api_identifier
            valid_api_dict = memcache.get(memcache_key)
            if not valid_api_dict:
                log.debug("Reloading API keys for id %s" % api_identifier)
                new_keys = elastic.get_source(index=settings.ES_SYSTEM_INDEX,
                                              id=api_identifier, ignore=404)
                if new_keys:
                    log.debug("Updating API keys from ES")
                    valid_api_dict = new_keys
                    try:
                        memcache.set(memcache_key, valid_api_dict, 60)
                    except ConnectionRefusedError:
                        log.debug("Memcache not available, reloading keys for " +
                                  "each request.")
            apikey = request.headers.get(settings.APIKEY)
            memcache_rate_key = "rate_limit_%s_%s_%s" % \
                (api_identifier, apikey, rate_limit)
            if apikey in valid_api_dict:
                if rate_limit and memcache.get(memcache_rate_key):
                    abort(429,
                          message='Rate limit is one request per %d seconds.'
                          % rate_limit)

                if rate_limit:
                    try:
                        memcache.set(memcache_rate_key, True, rate_limit)
                    except ConnectionRefusedError:
                        log.debug("Memcache not available, unable to set rate limit.")

                log.debug("API key \"%s\" is valid for application \"%s\" "
                          "(ID:%s)" % (apikey,
                                       valid_api_dict[apikey].get('app'),
                                       valid_api_dict[apikey].get('id')))
                return func(*args, **kwargs)
            log.info("Failed validation for key '%s'" % apikey)
            abort(401, message="Missing or invalid API key")

        return wrapper

    return real_check_api_key_decorator


def check_api_key_and_return_metadata(api_identifier):
    def real_check_api_key_decorator(func):
        def wrapper(*args, **kwargs):
            memcache_key = "valid_api_keys_%s" % api_identifier
            valid_api_dict = client.get(memcache_key)
            if not valid_api_dict:
                log.debug("Reloading API keys for id %s" % api_identifier)
                new_keys = elastic.get_source(index=settings.ES_SYSTEM_INDEX,
                                              id=api_identifier, ignore=404)
                if new_keys:
                    log.debug("Updating API keys from ES")
                    valid_api_dict = new_keys
                    try:
                        client.set(memcache_key, valid_api_dict, 60)
                    except ConnectionRefusedError:
                        log.debug("Memcache not available, reloading keys for " +
                                  "each request.")
            apikey = request.headers.get(settings.APIKEY)
            if apikey in valid_api_dict:
                kwargs['key_id'] = apikey
                kwargs['key_app'] = valid_api_dict[apikey].get('app')
                log.debug("API key \"%s\" is valid for application \"%s\" "
                          "(ID:%s)" % (apikey,
                                       kwargs['key_app'],
                                       valid_api_dict[apikey].get('id')))
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
