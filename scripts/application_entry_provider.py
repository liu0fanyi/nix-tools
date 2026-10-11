"""Reviewed Compose representation and non-secret HAProxy mount compatibility."""
import copy
import json
import tomllib
from pathlib import Path
from application_entry_transaction import ConfigurationTransaction, atomic, digest, private

NAMES = ['application-compose.json', 'native-nuc-control.json']


def compatible(model):
    result = copy.deepcopy(model)
    hosts = result['services']['readonly-gateway'].get('extra_hosts')
    if hosts != {'host.containers.internal':'host-gateway'}:
        raise ValueError('Only the reviewed readonly host-gateway mapping may be adapted')
    result['services']['readonly-gateway']['extra_hosts'] = ['host.containers.internal:host-gateway']
    return result


def materialize(release, runtime, primary):
    release = Path(release); runtime = Path(runtime)
    directory = release / 'p2/provider-input'
    directory.mkdir(mode=0o700)
    records = primary.load()['records']
    model = json.loads(private(records[str(runtime/NAMES[0])]['after']['source']).read_text())
    transformed = compatible(model)
    atomic(directory/NAMES[0],json.dumps(transformed,sort_keys=True,indent=2)+'\n')
    control = json.loads(private(records[str(runtime/NAMES[1])]['after']['source']).read_text())
    control['files'][str(runtime/NAMES[0])] = digest(directory/NAMES[0])
    atomic(directory/NAMES[1],json.dumps(control,sort_keys=True,indent=2)+'\n')
    desired = {runtime/n:{'kind':'file','source':str(directory/n),'sha256':digest(directory/n)} for n in NAMES}
    correction = ConfigurationTransaction(release/'p2/provider-transaction',desired)
    correction.create(desired)
    correction.install()
    return verify(release,runtime,primary)


def verify(release, runtime, primary):
    runtime = Path(runtime);release = Path(release)
    if not (release/'p2/provider-transaction').exists():return verify_transport_mode(release, runtime, primary)
    correction = ConfigurationTransaction(release/'p2/provider-transaction',{runtime/n for n in NAMES})
    records = primary.load()['records'];overrides = {}
    for name,item in correction.load()['records'].items():
        if item['before'].get('sha256') != records[name]['after']['sha256']:
            raise ValueError('Provider correction must start from reviewed original bytes')
        after = item['after']
        source = private(after['source'])
        if source.parent != release/'p2/provider-input' or source.name != Path(name).name or digest(source)!=after['sha256']:
            raise ValueError('Provider input scope/digest changed')
        overrides[name] = after
    original_model = json.loads(private(records[str(runtime/NAMES[0])]['after']['source']).read_text())
    actual_model = json.loads(private(overrides[str(runtime/NAMES[0])]['source']).read_text())
    if actual_model != compatible(original_model):raise ValueError('Provider correction changed additional model fields')
    original_control = json.loads(private(records[str(runtime/NAMES[1])]['after']['source']).read_text())
    original_control['files'][str(runtime/NAMES[0])] = overrides[str(runtime/NAMES[0])]['sha256']
    actual_control = json.loads(private(overrides[str(runtime/NAMES[1])]['source']).read_text())
    if actual_control != original_control:raise ValueError('Provider correction changed additional startup controls')
    overrides.update(verify_source(release, runtime, primary, overrides))
    correction.verify_after(overrides)
    overrides.update(verify_transport_mode(release, runtime, primary))
    return overrides


TRANSPORT = 'haproxy.readonly.cfg'


def materialize_transport_mode(release, runtime, primary):
    """Allow the image's haproxy UID to read only the non-secret routing file."""
    release = Path(release); runtime = Path(runtime)
    path = runtime / TRANSPORT
    original = primary.load()['records'][str(path)]['after']
    source = private(original['source'])
    # Reject widening access to any other configuration or to changed bytes.
    if source != release / TRANSPORT or digest(path) != original['sha256']:
        raise ValueError('Transport correction requires unchanged reviewed routing')
    expected = ('global\n    log stdout format raw local0\n\ndefaults\n'
                '    log global\n    mode tcp\n    timeout connect 5s\n'
                '    timeout client 1h\n    timeout server 1h\n\n'
                'frontend readonly_dual_protocol\n    bind :5008\n'
                '    tcp-request inspect-delay 100ms\n'
                '    tcp-request content accept if { req.ssl_hello_type 1 }\n'
                '    use_backend readonly_https if { req.ssl_hello_type 1 }\n'
                '    default_backend readonly_http\n\nbackend readonly_http\n'
                '    server native_http host.containers.internal:18182 check\n\n'
                'backend readonly_https\n    server caddy_https caddy:5443 check\n')
    if source.read_text() != expected:
        raise ValueError('Only the fixed non-secret HAProxy transport may be made readable')
    desired = {path: dict(original, mode=0o644)}
    correction = ConfigurationTransaction(release / 'p2/transport-mode-transaction', desired)
    correction.create(desired)
    correction.install()
    return verify_transport_mode(release, runtime, primary)


def verify_transport_mode(release, runtime, primary):
    release = Path(release); runtime = Path(runtime); path = runtime / TRANSPORT
    directory = release / 'p2/transport-mode-transaction'
    if not directory.exists(): return {}
    correction = ConfigurationTransaction(directory, {path})
    record = correction.load()['records'][str(path)]
    original = primary.load()['records'][str(path)]['after']
    if record['before'].get('sha256') != original['sha256'] or record['before'].get('mode') != 0o600:
        raise ValueError('Transport correction did not start from private installed routing')
    if record['after'] != dict(original, mode=0o644):
        raise ValueError('Transport correction changed more than routing read permission')
    correction.verify_after()
    return {str(path): record['after']}


HOST_SOURCE = '192.168.1.12/32'
OLD_SOURCES = ['10.89.50.0/24', '127.0.0.0/8', '::1/128']


def compatible_readonly_source(text):
    """pasta maps rootless host-gateway traffic to this fixed NUC host address."""
    parsed = tomllib.loads(text)
    if parsed.get('allowed_sources') != OLD_SOURCES or '192.168.1.12:5008' not in parsed.get('authorities', []):
        raise ValueError('Unknown fixed NUC readonly source/authority configuration')
    old = 'allowed_sources = ' + json.dumps(OLD_SOURCES)
    if text.count(old) != 1: raise ValueError('Unknown readonly source representation')
    return text.replace(old, 'allowed_sources = ' + json.dumps(OLD_SOURCES + [HOST_SOURCE]))


def source_paths(runtime):
    return [Path('/home/liou/.local/share/tag-all/nuc-native/readonly/config/application-entry.toml'), Path(runtime)/NAMES[1]]


def materialize_source(release, runtime, primary):
    release = Path(release); runtime = Path(runtime)
    overrides = verify(release, runtime, primary)
    entry, control = source_paths(runtime)
    records = primary.load()['records']
    entry_after = records[str(entry)]['after']
    control_after = overrides.get(str(control), records[str(control)]['after'])
    directory = release/'p2/source-input'; directory.mkdir(mode=0o700)
    atomic(directory/'readonly-entry.toml', compatible_readonly_source(private(entry_after['source']).read_text()))
    value = json.loads(private(control_after['source']).read_text())
    value['files'][str(entry)] = digest(directory/'readonly-entry.toml')
    atomic(directory/NAMES[1], json.dumps(value,sort_keys=True,indent=2)+'\n')
    desired = {entry:{'kind':'file','source':str(directory/'readonly-entry.toml'),'sha256':digest(directory/'readonly-entry.toml')},
               control:{'kind':'file','source':str(directory/NAMES[1]),'sha256':digest(directory/NAMES[1])}}
    correction = ConfigurationTransaction(release/'p2/source-transaction', desired)
    correction.create(desired); correction.install()
    return verify(release, runtime, primary)


def verify_source(release, runtime, primary, previous):
    release = Path(release); runtime = Path(runtime)
    directory = release/'p2/source-transaction'
    if not directory.exists(): return {}
    entry, control = source_paths(runtime); records=primary.load()['records']
    correction=ConfigurationTransaction(directory,{entry,control}); journal=correction.load()['records'];overrides={}
    for path in [entry,control]:
        name=str(path); before=previous.get(name,records[name]['after']);item=journal[name]
        if item['before'].get('sha256') != before['sha256'] or item['before'].get('mode') != 0o600:
            raise ValueError('Source correction did not start from reviewed configuration')
        after=item['after'];source=private(after['source'])
        expected='readonly-entry.toml' if path==entry else NAMES[1]
        if source!=release/'p2/source-input'/expected or digest(source)!=after['sha256'] or after.get('mode',0o600)!=0o600:
            raise ValueError('Source correction scope/digest/permissions changed')
        overrides[name]=after
    original=private(records[str(entry)]['after']['source']).read_text()
    if private(overrides[str(entry)]['source']).read_text()!=compatible_readonly_source(original):
        raise ValueError('Source correction changed additional entry fields')
    original_control=previous.get(str(control),records[str(control)]['after'])
    value=json.loads(private(original_control['source']).read_text());value['files'][str(entry)]=overrides[str(entry)]['sha256']
    if json.loads(private(overrides[str(control)]['source']).read_text())!=value:
        raise ValueError('Source correction changed additional startup controls')
    correction.verify_after();return overrides
