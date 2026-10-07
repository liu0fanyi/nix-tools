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
