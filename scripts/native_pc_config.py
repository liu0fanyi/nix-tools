"""Pure PC container-to-native configuration adaptation; no I/O or activation."""
from copy import deepcopy
from ipaddress import IPv4Address, IPv4Network
from pathlib import PurePosixPath
from urllib.parse import urlsplit


def absolute_path(value):
    if not isinstance(value, str) or not value.startswith('/'):
        raise ValueError('Expected an absolute path')
    if any(c in value for c in '\x00\r\n') or '..' in value.split('/') or '.' in value.split('/'):
        raise ValueError('Unsafe path component')
    return PurePosixPath(value)


def translate_path(value, mounts):
    path = absolute_path(value)
    matches = []
    for target, source in mounts.items():
        destination, host = absolute_path(target), absolute_path(source)
        if path == destination or destination in path.parents:
            matches.append((len(destination.parts), host / path.relative_to(destination)))
    if not matches:
        raise ValueError('Configuration path has no explicit bind mapping')
    return str(max(matches, key=lambda match: match[0])[1])


def discovery_arguments(arguments):
    result = {}
    allowed = {'--node-id', '--metadata-dir', '--advertise-url', '--advertise-ip', '--interface'}
    if len(arguments) % 2:
        raise ValueError('Discovery arguments must be explicit flag/value pairs')
    for flag, value in zip(arguments[::2], arguments[1::2]):
        if flag not in allowed or flag in result or not isinstance(value, str) or not value:
            raise ValueError('Unknown, repeated or empty discovery argument')
        result[flag] = value
    if set(result) != allowed:
        raise ValueError('Missing discovery argument')
    return result


def adapt_configuration(config, mounts, arguments):
    """Return a fresh dictionary; keep identity, peers and unknown settings intact."""
    candidate = deepcopy(config)
    workspace = translate_path('/workspace', mounts)
    mappings = {}
    for target, source in mounts.items():
        destination = absolute_path(target)
        root = PurePosixPath('/workspace')
        if root in destination.parents:
            relative = str(destination.relative_to(root))
            mappings[relative] = str(absolute_path(source))
    for location in candidate.get('locations', []):
        location['path'] = translate_path(location['path'], mounts)
    pairing = candidate.get('pairing', {})
    if 'trusted_ca_files' in pairing:
        pairing['trusted_ca_files'] = [translate_path(path, mounts) for path in pairing['trusted_ca_files']]
    discovery = candidate.get('discovery', {})
    if discovery.get('enabled'):
        if not discovery.get('external_agent'):
            raise ValueError('Source discovery must use the explicitly inspected external agent')
        args = discovery_arguments(arguments)
        if args['--node-id'] != candidate['node']['id'] or args['--advertise-url'] != discovery.get('advertise_url'):
            raise ValueError('Discovery identity or advertised origin differs from core configuration')
        origin = urlsplit(args['--advertise-url'])
        if origin.scheme != 'https' or not origin.hostname or origin.username is not None or origin.password is not None or origin.path not in ('', '/') or origin.query or origin.fragment:
            raise ValueError('Expected a private HTTPS peer origin without credentials or extra route')
        origin.port  # Reject malformed ports.
        address = IPv4Address(args['--advertise-ip'])
        if not any(address in IPv4Network(network) for network in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')):
            raise ValueError('Expected a private LAN IPv4 address')
        interface = args['--interface']
        if any(not (c.isalnum() or c in '_-.') for c in interface):
            raise ValueError('Invalid explicit interface name')
        if args['--metadata-dir'] != '/data/metadata':
            raise ValueError('Discovery metadata must match the source core state layout')
        discovery.update(external_agent=False, advertise_ip=str(address), interfaces=[interface])
    return candidate, {'workspace': workspace, 'workspace_mounts': mappings}


def serialize_configuration(config):
    """Canonical TOML without a second parser dependency; verify lossless roundtrip."""
    import datetime
    import json
    import tomllib

    def value(item):
        if isinstance(item, str):
            return json.dumps(item, ensure_ascii=False)
        if isinstance(item, bool):
            return 'true' if item else 'false'
        if isinstance(item, (int, float)):
            return repr(item)
        if isinstance(item, (datetime.datetime, datetime.date, datetime.time)):
            return item.isoformat()
        if isinstance(item, list):
            return '[' + ', '.join(value(entry) for entry in item) + ']'
        if isinstance(item, dict) and all(isinstance(key, str) for key in item):
            return '{ ' + ', '.join(value(key) + ' = ' + value(entry) for key, entry in item.items()) + ' }'
        raise ValueError('Unsupported TOML configuration value')

    text = '\n'.join(value(key) + ' = ' + value(entry) for key, entry in config.items()) + '\n'
    if tomllib.loads(text) != config:
        raise ValueError('TOML serialization must preserve every configuration field')
    return text


def adapt_peer_network(config, approved, extra_hosts, system_hosts):
    """Preserve container DNS aliases and use only unambiguous approved origins."""
    import re
    candidate = deepcopy(config)
    lines = []
    aliases = {}
    for item in extra_hosts:
        host, address = item.rsplit(':', 1)
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]*', host):
            raise ValueError('Unsafe container host alias')
        address = str(IPv4Address(address))
        if host in aliases and aliases[host] != address:
            raise ValueError('Conflicting container host aliases')
        aliases[host] = address
    for host, address in aliases.items():
        for line in system_hosts.splitlines():
            parts = line.split('#', 1)[0].split()
            if len(parts) > 1 and host in parts[1:] and parts[0] != address:
                raise ValueError('Container alias conflicts with existing hosts')
        lines.append(address + ' ' + host)
    for peer in candidate.get('sync', {}).get('peers', []):
        old = peer if isinstance(peer, str) else peer['url']
        parsed = urlsplit(old)
        if parsed.username is not None: continue  # Never discard explicit credentials.
        matches = [entry for entry in approved
                   if urlsplit(entry['url']).hostname == parsed.hostname
                   and (not isinstance(peer, dict) or not peer.get('node_id')
                        or peer['node_id'] == entry['identity']['node_id'])]
        if len(matches) > 1: raise ValueError('Ambiguous approved peer origin')
        if not matches: continue
        origin = urlsplit(matches[0]['url'])
        if origin.scheme != 'https' or origin.username is not None or origin.password is not None or origin.query or origin.fragment or origin.path not in ('', '/'):
            raise ValueError('Approved peer must be an explicit HTTPS origin')
        origin.port
        if isinstance(peer, str):
            candidate['sync']['peers'][candidate['sync']['peers'].index(peer)] = matches[0]['url']
        else: peer['url'] = matches[0]['url']
    return candidate, system_hosts.rstrip() + '\n# Preserved PC container peer aliases\n' + '\n'.join(lines) + '\n'
