"""Preserve inspected peer aliases and approved NUC broadcast destinations."""
from urllib.parse import urlsplit
from native_pc_config import adapt_peer_network


def adapt_network(config, approved, extra_hosts, system_hosts):
    candidate, hosts = adapt_peer_network(config, approved, extra_hosts, system_hosts)
    aliases = {item.rsplit(':', 1)[0] for item in extra_hosts}
    routes = candidate.setdefault('sync', {}).setdefault('peer_nodes', {})
    for peer in approved:
        origin = peer['url']; parsed = urlsplit(origin)
        if (parsed.scheme != 'https' or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment or parsed.path not in ('', '/')):
            raise ValueError('Approved sync origin must preserve explicit HTTPS without credentials')
        parsed.port
        if parsed.hostname not in aliases:
            continue
        node = peer['identity']['node_id']
        if node in routes and routes[node].rstrip('/') != origin.rstrip('/'):
            raise ValueError('Existing sync route conflicts with approved peer')
        routes[node] = origin
    return candidate, hosts
