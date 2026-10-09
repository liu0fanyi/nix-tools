"""Change only fixed NUC upstream tokens; preserve the authoritative complete ingress."""
import re

UPSTREAMS = {
    'tag-server:8081': 'unix//run/tag-native/private-api.sock',
    'tag-server-readonly:8081': 'unix//run/tag-native/readonly-api.sock',
    'dufs:5000': 'unix//run/tag-native/private-files.sock',
    'dufs-readonly:5000': 'unix//run/tag-native/readonly-files.sock',
}


def adapt_ingress(caddyfile):
    """Pure candidate transformation, with refusal on missing or ambiguous upstreams."""
    original = caddyfile
    counts = {}
    for upstream, socket in UPSTREAMS.items():
        pattern = re.compile(r'(^[ \t]*reverse_proxy[ \t]+)' + re.escape(upstream) + r'(?=[ \t{\r\n]|$)', re.MULTILINE)
        caddyfile, count = pattern.subn(lambda m: m[1] + socket, caddyfile)
        if count == 0:
            raise ValueError('Complete NUC ingress required; missing upstream ' + upstream)
        counts[upstream] = count
    for upstream in UPSTREAMS:
        if upstream in caddyfile:
            raise ValueError('Unhandled upstream reference: ' + upstream)
    restored = caddyfile
    for upstream, socket in UPSTREAMS.items():
        restored = restored.replace(socket, upstream)
    if restored != original:
        raise ValueError('Ingress change must only replace fixed upstreams')
    return caddyfile, counts
