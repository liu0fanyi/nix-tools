#!/usr/bin/env python3
"""Stage only public Trime config/dictionary files; never deploy or copy userdb."""
from pathlib import Path
import argparse,hashlib,json,shutil
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
config=root/'config/android/trime';pin=json.loads((config/'sources.json').read_text())['dictionary'];source=Path(pin['nix_store'])/'share/rime-data'
assert str(source).startswith('/nix/store/')
a.output.mkdir(parents=True,exist_ok=True)
for name,expected in pin['files_sha256'].items():
 path=source/name;assert hashlib.sha256(path.read_bytes()).hexdigest()==expected,name
 target=a.output/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
for name in ['default.custom.yaml','tongwenfeng_plus.trime.custom.yaml','clover.dict.yaml']:shutil.copyfile(config/name,a.output/name)
files={str(f.relative_to(a.output)):hashlib.sha256(f.read_bytes()).hexdigest() for f in a.output.rglob('*') if f.is_file()}
assert len(files)==7 and not any('userdb' in name or name.startswith(('build/','sync/')) for name in files)
for f in a.output.rglob('*'):f.chmod(0o755 if f.is_dir() else 0o644)
print(json.dumps({'public_files_sha256':files,'device_written':False,'user_dictionary_read':False},ensure_ascii=False,indent=2))
