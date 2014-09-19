#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main module
"""

__author__ = "Hui Zheng"
__copyright__ = "Copyright 2011-2012 Hui Zheng"
__credits__ = ["Hui Zheng"]
__license__ = "MIT <http://www.opensource.org/licenses/mit-license.php>"
__version__ = "0.1"
__email__ = "xyzdll[AT]gmail[DOT]com"


import os
import sys
import getpass
import json
import re

from cachette.aes_crypt import decrypt_file, encrypt


class Cachette(object):

    def __init__(self, cache_file, password):
        self._cache_file = cache_file
        self._password = password

        if os.path.getsize(cache_file) < 2:
            # initialize an empty file
            with open(cache_file, 'w') as f:
                f.write(encrypt("{}", password))

    def list_all_data(self):
        with open(self._cache_file) as f:
            decrypted = decrypt_file(f, self._password)
            return json.loads(decrypted)

    def retrieve_data(self, key, exact=False):
        json_data = {}
        with open(self._cache_file) as f:
            decrypted = decrypt_file(f, self._password)
            json_data = json.loads(decrypted)
        if exact:
            return json_data[key]
        else:
            for k in sorted(json_data):
                pattern = ".*".join([c for c in key])
                if re.search(pattern, k):
                    return json_data[k]
            raise KeyError(u"{}(fuzzy)".format(key))

    def _update_data(self, process_data):
        with open(self._cache_file, 'r+') as f:
            decrypted = decrypt_file(f, self._password)
            json_data = json.loads(decrypted)
            process_data(json_data)
            encrypted = encrypt(
                    json.dumps(json_data), self._password)
            f.seek(0)
            f.truncate()
            f.write(encrypted)

    def update_data(self, key, value):

        def process_data(data):
            data[key] = value

        self._update_data(process_data)

    def del_data(self, key):

        def process_data(data):
            del data[key]

        self._update_data(process_data)

    def del_data_re(self, key_re):

        def process_data(data):
            found = False
            for k in data.keys():
                if re.search(key_re, k):
                    found = True
                    del data[k]
            if not found:
                raise KeyError("{}(regex)".format(key_re))

        self._update_data(process_data)


ENCODING = sys.stdin.encoding or "UTF-8"


def encode(unicode_str):
    """Encode the given unicode as stdin's encoding"""
    return unicode_str.encode(ENCODING)


def decode_args(args, options):
    """Convert args and options to unicode string"""
    for attr, value in options.__dict__.iteritems():
        if isinstance(value, str):
            setattr(options, attr, value.decode(ENCODING))
    return [arg.decode(ENCODING) for arg in args]

def main(argv=None):
    from optparse import OptionParser
    usage = "usage: %prog [options] cache_file [key [value]]"
    parser = OptionParser(usage)
    parser.add_option("-p", dest="password", help="password")
    parser.add_option("-d", dest="del_key",
            help="delete data mapped by the key")
    parser.add_option("-D", dest="del_key_re",
            help="delete data mapped by the key regex")
    parser.add_option("-e", action="store_true", default=False,
            dest="exact", help="exact key match")
    (options, args) = parser.parse_args(argv)
    args = decode_args(args, options)

    arg_len = len(args)
    if arg_len < 1:
        parser.error("cache file not specified")
    elif arg_len > 3:
        parser.error("too many arguments")

    password = options.password or getpass.getpass("password: ")
    cachette = Cachette(args[0], password)
    try:
        if arg_len == 1: # delete matched data or list all data
            if options.del_key:
                cachette.del_data(options.del_key)
            elif options.del_key_re:
                cachette.del_data_re(options.del_key_re)
            else:
                data = cachette.list_all_data()
                for key, value in sorted(data.items()):
                    sys.stdout.write("{} -> {}\n".format(encode(key), encode(value)))
        elif arg_len == 2: # fetch one item
            cache_file, key = args
            data = cachette.retrieve_data(key, options.exact)
            if data:
                sys.stdout.write("{}".format(encode(data)))
            else:
                sys.stderr.write("no matched data\n")
                return 1
        else: # (arg_len == 3) update one item
            cache_file, key, value = args
            cachette.update_data(key, value)
    except ValueError:
        sys.stderr.write("wrong password or corrupted data\n")
        return 1
    except KeyError as e:
        sys.stderr.write("key not found: {} \n".format(encode(e.message)))
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())