"""Opt-in external NUC entry: transport/auth only; default renderer stays unchanged."""
import ipaddress
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'deploy/scripts'))
import render

PEER_PATHS = '/tag-api/v1/peers/identity /tag-api/v1/peers/challenge /tag-api/v1/peers/requests/incoming /tag-api/v1/peers/requests/accepted /tag-api/v1/sync/* /tag-api/v1/locations /tag-api/v1/locations/* /tag-api/v1/proxy/* /tag-api/listing /tag-api/items /tag-api/v1/inspect'
UNTRUSTED = ['Remote-User', 'Remote-Groups', 'Remote-Name', 'Remote-Email', 'X-Tag-Admin-Token', 'X-Dufs-Device-Api', 'X-Dufs-Device-Provisioning']

def blocks(text):
    """Split outer Caddy blocks; preserve all unowned sites byte-for-byte."""
    start = 0; depth = 0; quote = None; escaped = False; comment = False
    for index, ch in enumerate(text):
        if comment:
            if ch == '\n': comment = False
            continue
        if quote:
            if escaped: escaped = False
            elif ch == '\\' and quote != '`': escaped = True
            elif ch == quote: quote = None
            continue
        if ch == '#': comment = True
        elif ch in ('"', '`'): quote = ch
        elif ch == '{': depth += 1
        elif ch == '}':
            depth -= 1
            if depth < 0: raise ValueError('Unbalanced authoritative ingress')
            if depth == 0:
                yield text[start:index+1]; start = index+1
    if depth or quote or text[start:].strip(): raise ValueError('Incomplete authoritative ingress')

def proxy(socket, *, authenticated=False, basic=False):
    headers = [f'header_up -{name}' for name in UNTRUSTED if not ((authenticated and name.startswith('Remote-')) or (basic and name in ('Remote-User','Remote-Groups')))]
    if authenticated or basic: headers += ['header_up -Authorization']
    if basic: headers += ['header_up Remote-User {http.auth.user.id}', 'header_up Remote-Groups ""']
    return f'reverse_proxy {socket} {{\n' + '\n'.join(headers) + '\n}'

def candidate_ingress(original, config):
    if config['deployment']['profile'] != 'home-ipv6-cdn' or not config['features']['authelia'] or not config['features']['readonly']:
        raise ValueError('Complete authenticated NUC dual-workspace configuration required')
    if config['ports'] != {'lan':5006, 'readonly_origin':5008, 'main_origin':5009, 'http':80, 'https':443}:
        raise ValueError('Fixed NUC entry ports required')
    expected_domains = {'public':'nas.wttliou.top','origin':'home.wttliou.top','readonly_public':'workcdn.wttliou.top','readonly_origin':'work.wttliou.top'}
    if any(config['domains'].get(key) != value for key,value in expected_domains.items()) or config['domains'].get('aliases'):
        raise ValueError('Candidate authority templates require fixed NUC domains')
    if config['security']['container_subnet'] != '10.89.50.0/24':
        raise ValueError('Candidate readonly transport requires the fixed NUC container subnet')
    cidrs = ' '.join(str(ipaddress.ip_network(n)) for n in config['security']['lan_cidrs'])
    output=[]; seen=set(); retained=[]
    def record(name):
        if name in seen: raise ValueError("Repeated fixed NUC site")
        seen.add(name)
    for block in blocks(original):
        header=block.split('{',1)[0].strip()
        if header in ('http://:5006','http://:5008'):
            record(header); continue
        if header.startswith('https://nuc.local:5009,'):
            record('private')
            domain=config['domains'];auth=render.auth_routes(domain['public'],peer_identity_exempt=True)
            auth,errors=auth.split('handle_errors {',1)
            errors='handle_errors {'+errors
            clear='\n'.join('request_header -'+name for name in UNTRUSTED)
            body=f'''tls internal
@origin_host host {domain['origin']}
redir @origin_host https://{domain['public']}{{uri}} permanent
route {{
{clear}
@external_device path /device-api /device-api/*
handle @external_device {{
{proxy('unix//run/tag-native/private-peer.sock')}
}}
@node_peer path {PEER_PATHS}
handle @node_peer {{
route {{
@node_source remote_ip {cidrs}
handle @node_source {{
{proxy('unix//run/tag-native/private-peer.sock')}
}}
respond "Not found" 404
}}
}}
{auth}
handle {{
{proxy('unix//run/tag-native/private-web.sock',authenticated=True)}
}}
}}
{errors}'''
            output.append('\n'+header+' {\n'+body+'\n}');continue
        if ':5443' in header and header.startswith('https://'):
            record('readonly')
            output.append('\n'+header+''' {
tls internal
route {
'''+'\n'.join('request_header -'+name for name in UNTRUSTED)+'''
@not_options not method OPTIONS
basic_auth @not_options {
import "/run/secrets/caddy_lan_basic_auth"
}
'''+proxy('unix//run/tag-native/readonly-web.sock',basic=True)+'\n}\n}');continue
        retained.append(block);output.append(block)
    if seen != {'http://:5006','http://:5008','private','readonly'}: raise ValueError('Missing or repeated fixed NUC sites')
    result=''.join(output)+'\n'
    if any(x in result for x in ['uri strip_prefix /tag-api', 'header_up X-Tag-Admin-Token', 'tag-server:8081', 'dufs:5000']):
        raise ValueError('Application business routing remained in external candidate')
    return result, {'caddy_lan_listeners_removed':[5006,5008], 'readonly_public_dual_protocol_retained':5008, 'readonly_application_transport_port':18182, 'private_tls_preserved':True, 'authelia_preserved':True, 'readonly_credentials_runtime_only':True, 'unowned_blocks_preserved':len(retained), 'external_socket_roles':['private-web','private-peer','readonly-web']}


def candidate_profile(original):
    """Replace the fixed profile input, never merge an additive ports overlay."""
    line = '      - "${LAN_BIND_IP:-0.0.0.0}:${LAN_PUBLISH_PORT:-5006}:5006"\n'
    marker = '  readonly-gateway:\n'
    if original.count(line) != 1 or original.count(marker) != 1:
        raise ValueError('Unknown NUC transport profile')
    return original.replace(line, '').replace(marker, marker + '    extra_hosts:\n      - "host.containers.internal:host-gateway"\n')


def candidate_readonly_transport(original):
    """Retain TLS/plain TCP discrimination; HTTP is handled by authenticated Rust."""
    target = 'server caddy_http caddy:5008 check'
    if original.count(target) != 1 or 'server caddy_https caddy:5443 check' not in original:
        raise ValueError('Unknown readonly dual-protocol transport')
    return original.replace(target, 'server native_http host.containers.internal:18182 check')
