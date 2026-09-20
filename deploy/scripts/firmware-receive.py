#!/usr/bin/env python3
"""Forced SSH command: bounded transactions for the unified firmware only."""
import importlib.util
import io
import json
import os
from pathlib import Path
import sys

MAX_REQUEST = 5 * 1024 * 1024

def validate_request(request):
    if type(request) is not dict:
        raise ValueError('object required')
    operation = request.get('operation')
    allowed = {'read': {'operation'}, 'assets': {'operation', 'assets'}, 'catalog': {'operation', 'entries', 'expected'}}
    if operation not in allowed or set(request) != allowed[operation]:
        raise ValueError('unsupported transaction')
    if operation == 'read':
        return
    entries = request['assets'] if operation == 'assets' else request['entries']
    if type(entries) is not list or len(entries) != 1:
        raise ValueError('exactly one unified release required')
    entry = entries[0]
    if operation == 'assets':
        if type(entry) is not dict or set(entry) != {'entry', 'data'} or type(entry['data']) is not str:
            raise ValueError('invalid asset')
        entry = entry['entry']
    if type(entry) is not dict or entry.get('product') != 'esp32_device_bean':
        raise ValueError('only unified firmware may be written')
    if entry.get('supportedSourceProducts') != ['esp32_device_bean']:
        raise ValueError('unexpected source products')
    if entry.get('bootstrapRequired') is not False or entry.get('requiredResources') != []:
        raise ValueError('bootstrap/resources cannot be published')

def receive(stream, original_command, transaction):
    if original_command != 'firmware-publish':
        raise ValueError('interactive/other commands disabled')
    data = stream.read(MAX_REQUEST + 1)
    if len(data) > MAX_REQUEST:
        raise ValueError('request too large')
    request = json.loads(data)
    validate_request(request)
    # Reuse the exact immutable/CAS/path validation from the PC publisher.
    previous = sys.stdin
    try:
        sys.stdin = io.StringIO(json.dumps(request))
        transaction()
    finally:
        sys.stdin = previous

if __name__ == '__main__':
    spec = importlib.util.spec_from_file_location('publisher', Path(__file__).with_name('publish-firmware.py'))
    publisher = importlib.util.module_from_spec(spec); spec.loader.exec_module(publisher)
    ns = {'__name__': 'restricted_transaction'}
    exec(compile(publisher.REMOTE, '<firmware-transaction>', 'exec'), ns)
    try:
        receive(sys.stdin, os.environ.get('SSH_ORIGINAL_COMMAND'), ns['main'])
    except (ValueError, AssertionError, KeyError, TypeError, OSError):
        sys.exit('firmware transaction rejected')
