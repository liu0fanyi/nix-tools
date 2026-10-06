#!/usr/bin/env python3
"""Validate evidence-linked recipe inputs and build an offline searchable library."""
from pathlib import Path
import argparse,base64,hashlib,html,json,re,shutil,tempfile,os
from urllib.parse import urlparse
from jsonschema import Draft202012Validator
from PIL import Image
from referencing import Registry, Resource
import importlib.util

ROOT=Path(__file__).resolve().parents[1]
CONTRACTS=ROOT/'specs/010-host-configuration/contracts'
TEMPLATES=Path(__file__).resolve().parent/'recipe-library-templates'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def reject_constant(value):raise ValueError('non-finite JSON number: '+value)
def read(p):return json.loads(p.read_text(encoding='utf-8'),parse_constant=reject_constant)
def dump(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def esc(s):return html.escape(str(s),quote=True)
def clock(t):return f'{int(t)//60:02}:{int(t)%60:02}'
def quantity(q):
 if q['mode']=='unspecified':
  if q['unit'] is not None:return q['original']
  original=q['original'].strip()
  return '未明确'if original in ('','未明确','未知','不详')else '用量待核对；原文：'+original
 n=lambda x:f'{x:g}'
 value=n(q['min']) if q['min']==q['max'] else n(q['min'])+'–'+n(q['max'])
 return ('约' if q['mode']=='approximate' else '')+value+q['unit']
def ingredient_name(name):return re.sub(r'（.*?）|\(.*?\)','',name).strip()

def validate(folder,schema):
 d=read(folder/'recipe.internal.json');transcript=read(folder/'transcript.json');cue={c['id']:c for c in transcript['cues']}
 Draft202012Validator(schema).validate(d)
 if d['source']['transcript_sha256']!=digest(folder/'source.srt'):raise ValueError('source subtitle digest mismatch')
 if transcript['transcript_sha256']!=d['source']['transcript_sha256']:raise ValueError('transcript metadata mismatch')
 # The source SRT and its normalized cues must also agree, not just their metadata.
 import sys
 sys.path.insert(0,str(Path(__file__).parent))
 def sec(t):
  h,m,s=t.replace(',','.').split(':');return int(h)*3600+int(m)*60+float(s)
 parsed=[]
 for block in re.split(r'\n\s*\n',(folder/'source.srt').read_text().strip()):
  lines=block.splitlines();a,b=lines[1].split(' --> ');parsed.append({'id':int(lines[0]),'start':sec(a),'end':sec(b),'text':'\n'.join(lines[2:])})
 if parsed!=transcript['cues']:raise ValueError('normalized transcript does not match SRT')
 duration=d['source']['duration_seconds'];ids=[]
 tables={name:{x['id']:x for x in d[name]}for name in ['ingredients','steps','variants','evidence','frames','issues']}
 for name in tables:ids.extend(x['id']for x in d[name])
 facts=[f for s in d['steps']+d['variants']for f in s['facts']];ids.extend(f['id']for f in facts)
 if len(ids)!=len(set(ids)):raise ValueError('duplicate IDs')
 allids=set(ids);ev=tables['evidence'];frames=tables['frames'];stepids=tables['steps'];used=set()
 def interval(i):
  if not 0<=i['start']<i['end']<=duration+0.001:raise ValueError('invalid time range')
 def qcheck(q):
  if q['mode']=='unspecified':
   if q['min'] is not None or q['max'] is not None:raise ValueError('unspecified quantity has a number')
  else:
   if q['min'] is None or q['max'] is None or not q['unit'] or q['min']>q['max']:raise ValueError('invalid numeric quantity')
   if q['mode']in ['exact','approximate']and q['min']!=q['max']:raise ValueError('scalar quantity is a range')
 for e in ev.values():
  interval(e['interval'])
  if e['kind']=='subtitle':
   if not e['cue_ids']or e['frame_id']is not None or e['observation']is not None:raise ValueError('invalid subtitle evidence')
   cited=[cue[x]for x in e['cue_ids']]
   if e['quote']!='\n'.join(c['text']for c in cited):raise ValueError('quote does not match actual cues')
   if min(c['start']for c in cited)<e['interval']['start']or max(c['end']for c in cited)>e['interval']['end']:raise ValueError('evidence interval omits cue')
  elif e['kind']=='frame':
   f=frames[e['frame_id']]
   if e['cue_ids']or not e['observation']or not e['interval']['start']<=f['timestamp']<e['interval']['end']:raise ValueError('invalid frame evidence')
  else:raise ValueError('audio evidence unsupported by this builder')
 for x in d['ingredients']+facts:
  if not set(x['evidence_ids'])<=ev.keys():raise ValueError('missing evidence reference')
  if 'quantity'in x:qcheck(x['quantity'])
  if 'measure'in x and x['measure']is not None:qcheck(x['measure'])
 for f in facts:
  if not set(f['ingredient_ids'])<=tables['ingredients'].keys():raise ValueError('unknown ingredient reference')
 for s in d['steps']:
  used.update(i for f in s['facts']for i in f['ingredient_ids'])
 for i in d['ingredients']:
  if i['role']=='main'and i['id']not in used:raise ValueError('main ingredient is not used: '+i['name'])
 for f in frames.values():
  if not 0<=f['timestamp']<duration:raise ValueError('frame outside video')
  path=folder/f['file'];resolved=path.resolve()
  if path.is_symlink()or not resolved.is_relative_to((folder/'images').resolve())or not path.is_file():raise ValueError('unsafe or missing image')
  if path.parent.is_symlink()or digest(path)!=f['sha256']:raise ValueError('image changed or linked')
  with Image.open(path)as image:
   if image.size!=(f['width'],f['height']):raise ValueError('image dimensions mismatch')
 visited=set()
 for s in d['steps']:
  if not set(s['depends_on'])<=visited:raise ValueError('dependency order invalid or cyclic')
  visited.add(s['id'])
  for window in s['evidence_windows']:interval(window)
  selected=s['selected_frame_id']
  if selected is None:
   if not s['no_image_reason']or not any(i['code']=='missing_image'and s['id']in i['target_ids']for i in d['issues']):raise ValueError('empty image without reason and issue')
  else:
   f=frames[selected]
   if not any(r['step_id']==s['id']and r['frame_id']==selected and r['relevance']=='matches'and r['quality']=='usable'for r in d['image_reviews']):raise ValueError('selected frame lacks positive review')
   if not any(max(0,w['start']-5)<=f['timestamp']<=w['end']+5 for w in s['evidence_windows']):raise ValueError('selected frame outside evidence windows')
 for r in d['image_reviews']:
  if r['step_id']not in stepids or r['frame_id']not in frames:raise ValueError('invalid image review references')
 for v in d['variants']:
  if not set(v['replaces_ingredient_ids'])<=tables['ingredients'].keys():raise ValueError('unknown variant ingredient')
 for i in d['issues']:
  if not set(i['target_ids'])<=allids or not set(i['evidence_ids'])<=ev.keys():raise ValueError('invalid issue references')
  if i['resolution']=='resolved'and(not i['resolution_note']or not i['evidence_ids']):raise ValueError('resolved issue without explanation/evidence')
 for x in d['ingredients']+facts:
  if x['review_status']=='needs_review'and not any(i['resolution']=='open'and x['id']in i['target_ids']for i in d['issues']):raise ValueError('needs-review item without issue')
 for window in d['covered_intervals']:interval(window)
 spans=sorted(d['covered_intervals'],key=lambda x:x['start']);end=0
 for span in spans:
  if span['start']>end+0.001:raise ValueError('full coverage has a gap')
  end=max(end,span['end'])
 if spans[0]['start']>0.001 or end<duration-0.001:raise ValueError('full coverage does not cover the video')
 if d['coverage']!='full':raise ValueError('partial recipe cannot be exported as full recipe')
 if d['human_reviewed']:raise ValueError('this AI trial cannot mark human_reviewed')
 source=urlparse(d['source']['url'])
 if source.scheme!='https'or source.hostname!='www.bilibili.com'or source.username or source.password:raise ValueError('unsupported source URL')
 if not re.fullmatch(r'BV[A-Za-z0-9]+',d['source']['video_id']):raise ValueError('invalid video ID')
 if source.path.rstrip('/')!='/video/'+d['source']['video_id']:raise ValueError('source URL does not match video ID')
 for run in d['runs']:
  if run['stage']=='extract' and run['input_sha256']!=digest(folder/'source.srt'):raise ValueError('extract input digest mismatch')
  if run['stage']=='select_images':
   snapshots=[folder/'candidates.json',folder/('candidates-input-'+run['input_sha256']+'.json')]
   if not any(p.is_file() and not p.is_symlink() and digest(p)==run['input_sha256'] for p in snapshots):raise ValueError('image input digest mismatch')
  if run['stage'] in ['review','repair'] and run['prompt_version']=='1.1.0':
   snapshot=folder/('stage-input-'+run['input_sha256']+'.json')
   if not snapshot.is_file() or snapshot.is_symlink() or digest(snapshot)!=run['input_sha256']:raise ValueError('review/repair input digest mismatch')
  if run['stage']=='render':
   snapshots=[folder/'recipe-input.json',folder/('recipe-input-'+run['input_sha256']+'.json')]
   if not any(p.is_file() and digest(p)==run['input_sha256'] for p in snapshots):raise ValueError('render input digest mismatch')
 stage_schema=read(CONTRACTS/'video-recipe-stage.schema.json')
 registry=Registry().with_resource('video-recipe.schema.json',Resource.from_contents(schema))
 validator=Draft202012Validator(stage_schema,registry=registry)
 semantic=read(folder/'semantic-review.json');validator.validate(semantic)
 if {x['fact_id']for x in semantic['fact_reviews']}!={f['id']for f in facts} or len(semantic['fact_reviews'])!=len(facts):raise ValueError('semantic review does not cover all facts')
 for item in semantic['fact_reviews']:
  if not set(item['evidence_ids'])<=ev.keys():raise ValueError('semantic review has unknown evidence')
 if 'ingredient_reviews' in semantic:
  reviews=semantic['ingredient_reviews'];ingredients=tables['ingredients']
  if len(reviews)!=len(ingredients) or {x['ingredient_id']for x in reviews}!=set(ingredients):raise ValueError('semantic review does not cover all ingredients')
  for item in reviews:
   if not set(item['evidence_ids'])<=ev.keys() or (item['verdict']=='supported'and not item['evidence_ids']):raise ValueError('invalid ingredient review evidence')
   if item['verdict']!=ingredients[item['ingredient_id']]['review_status']:raise ValueError('ingredient review differs from recipe')
 selections=read(folder/'image-selection.json')
 if {x['step_id']for x in selections}!=set(stepids) or len(selections)!=len(stepids):raise ValueError('image selection does not cover all steps')
 for selection in selections:
  validator.validate(selection)
  if selection['selected_frame_id']!=stepids[selection['step_id']]['selected_frame_id']:raise ValueError('selected image response differs from recipe')
 if any(x['verdict']=='needs_review' for x in semantic['fact_reviews']) and d['status']!='needs_review':raise ValueError('unreviewed facts cannot be ready')
 computed='needs_review'if any(i['resolution']=='open'for i in d['issues'])else'ready'
 if d['status']!=computed:raise ValueError('status must be computed from issues')
 return d

def render_recipe(d,folder):
 frames={f['id']:f for f in d['frames']};evidence={e['id']:e for e in d['evidence']}
 exported={'@context':'https://schema.org','@type':'Recipe','name':d['title'],'author':{'@type':'Person','name':d['source']['author']},'url':d['source']['url'],'description':'视频字幕与画面整理的AI试稿；未明确用量和待核对项见阅读版。','recipeIngredient':[], 'recipeInstructions':[]}
 ingredients=[]
 for x in d['ingredients']:
  label=x['name']+'：'+quantity(x['quantity'])+('（可选）'if x['role']=='optional'else'')
  exported['recipeIngredient'].append(label)
  quotes=' / '.join(evidence[i]['quote']or evidence[i]['observation']for i in x['evidence_ids'])
  ingredients.append(f'<li><b>{esc(x["name"])}</b><span>{esc(quantity(x["quantity"]))}{" · 可选"if x["role"]=="optional"else""}</span><details><summary>来源原文</summary>{esc(quotes)}</details></li>')
 rows=[]
 for n,s in enumerate(d['steps'],1):
  facts=''.join(f'<p>{esc(f["text"])}</p>'for f in s['facts']);src=[]
  for f in s['facts']:
   for eid in f['evidence_ids']:
    e=evidence[eid]
    if e['kind']=='subtitle':src.append(e['interval'])
  start=min(w['start']for w in src);end=max(w['end']for w in src);url=d['source']['url']+'?t='+str(int(start))
  description=' '.join(f['text']for f in s['facts']);step={'@type':'HowToStep','name':s['title'],'text':description,'url':url}
  if s['selected_frame_id']:
   f=frames[s['selected_frame_id']];data=base64.b64encode((folder/f['file']).read_bytes()).decode();image=f'<img alt="{esc(s["image_goal"])}" src="data:image/jpeg;base64,{data}"><small>操作画面 · {clock(f["timestamp"])}</small>';step['image']=f['file']
  else:image=f'<div class="empty-image">{esc(s["no_image_reason"])}</div>'
  rows.append(f'<tr id="{esc(s["id"])}"><td><span class="number">{n:02}</span><h3>{esc(s["title"])}</h3>{facts}<a class="time" href="{esc(url)}">来源 {clock(start)}–{clock(end)} ↗</a></td><td>{image}</td></tr>');exported['recipeInstructions'].append(step)
 variants=''.join(f'<li><b>{esc(v["name"])}</b>'+''.join(f'<p>{esc(f["text"])}</p>'for f in v['facts'])+'</li>'for v in d['variants'])or'<li>未列其他版本。</li>'
 issues=''.join('<li>'+esc(i['description'])+'</li>'for i in d['issues']if i['resolution']=='open')
 vals={'TITLE':esc(d['title']),'AUTHOR':esc(d['source']['author']),'SOURCE':esc(d['source']['url']),'INGREDIENTS':''.join(ingredients),'STEPS':''.join(rows),'VARIANTS':variants,'ISSUES':issues}
 template=(TEMPLATES/'recipe.html').read_text()
 template=re.sub(r'\{\{('+ '|'.join(vals) +r')\}\}',lambda match:vals[match[1]],template)
 return template,exported

def build(source,output,dictionary_path):
 spec=importlib.util.spec_from_file_location("ingredients",ROOT/"scripts/recipe-ingredients.py");ingredients_tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(ingredients_tool)
 dictionary=read(dictionary_path);ingredients_tool.vocabulary(dictionary)
 schema=read(CONTRACTS/'video-recipe.schema.json');Draft202012Validator.check_schema(schema)
 folders=sorted(p.parent for p in source.glob('*/recipe.internal.json'))
 if not folders:raise ValueError('no recipe.internal.json inputs')
 recipes=[(p,validate(p,schema))for p in folders]
 vids=[d['source']['video_id']for _,d in recipes]
 if len(vids)!=len(set(vids)):raise ValueError('duplicate video ID')
 # Build in a sibling staging directory; existing destinations are preserved.
 if output.exists():raise ValueError('output already exists; choose a new directory')
 output.parent.mkdir(parents=True,exist_ok=True)
 stage=Path(tempfile.mkdtemp(prefix='.recipe-build-',dir=output.parent))
 try:
  records=[]
  for folder,d in recipes:
   vid=d['source']['video_id'];dst=stage/'recipes'/vid;dst.mkdir(parents=True)
   for name in ['recipe.internal.json','transcript.json','source.srt','semantic-review.json','image-selection.json','candidates.json','processing.json']:
    if (folder/name).is_file():shutil.copy2(folder/name,dst/name)
   for f in d['frames']:
    (dst/f['file']).parent.mkdir(exist_ok=True);shutil.copy2(folder/f['file'],dst/f['file'])
   for snapshot in list(folder.glob('recipe-input*.json'))+list(folder.glob('candidates-input-*.json'))+list(folder.glob('stage-input-*.json')):
    if snapshot.is_file() and not snapshot.is_symlink():shutil.copy2(snapshot,dst/(('candidates-input-' if snapshot.name.startswith('candidates-input-') else 'stage-input-' if snapshot.name.startswith('stage-input-') else 'recipe-input-')+digest(snapshot)+'.json'))
   shutil.copy2(folder/'recipe.internal.json',dst/'recipe-input.json')
   d['runs'].append({'stage':'render','processor':'recipe-library.py','model':None,'prompt_version':'1.0.0','input_sha256':digest(folder/'recipe.internal.json')})
   dump(dst/'recipe.internal.json',d)
   page,export=render_recipe(d,folder);(dst/'recipe.html').write_text(page);dump(dst/'recipe.json',export)
   review={'status':d['status'],'human_reviewed':False,'coverage':d['coverage'],'structural_checks':'passed','semantic_review':read(folder/'semantic-review.json'),'open_issues':[i for i in d['issues']if i['resolution']=='open']};dump(dst/'review.json',review)
   frames_by_id={f['id']:f for f in d['frames']}
   selected=[frames_by_id[s['selected_frame_id']] for s in d['steps']if s['selected_frame_id']]
   thumbnail=f'recipes/{vid}/'+selected[-1]['file']if selected else None
   records.append({'id':vid,'title':d['title'],'page':f'recipes/{vid}/recipe.html','thumbnail':thumbnail,'ingredients':[{'name':i['name'],'role':i['role']}for i in d['ingredients']],'status':d['status'],'issues':len(review['open_issues'])})
   dump(dst/'manifest.json',{'schema_version':d['schema_version'],'source':d['source'],'runs':d['runs'],'method':read(folder/'processing.json').get('method','unknown'),'processing':read(folder/'processing.json'),'ingredient_dictionary_sha256':digest(dictionary_path),'template_sha256':{name:digest(TEMPLATES/name)for name in ['recipe.html']},'outputs':{f.name:digest(f)for f in dst.glob('*')if f.is_file()}})
  records.sort(key=lambda r:r['title']);records=ingredients_tool.index_records(records,dictionary);dump(stage/'search-index.json',records)
  shutil.copy2(dictionary_path,stage/'ingredient-dictionary.json')
  payload=json.dumps(records,ensure_ascii=False,separators=(',',':'))
  (stage/'index.html').write_text(ingredients_tool.render_directory(records,stage))
  dump(stage/'manifest.json',{'recipe_count':len(records),'search_source':'ingredient lists only; variants excluded','ingredient_dictionary_sha256':digest(dictionary_path),'directory_templates_sha256':{name:digest(ROOT/'scripts'/name)for name in ['recipe-directory.html','recipe-directory.js','recipe-ingredient-search.js']},'files':{str(f.relative_to(stage)):digest(f)for f in stage.rglob('*')if f.is_file()}})
  for p in [stage]+list(stage.rglob('*')):p.chmod(0o755 if p.is_dir()else 0o644)
  stage.rename(output)
 except BaseException:
  shutil.rmtree(stage);raise
 print(json.dumps({'output':str(output),'recipes':len(records),'index_bytes':len(payload.encode()),'sqlite':False},ensure_ascii=False))

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('input',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--dictionary',type=Path,default=ROOT/'config/recipe/ingredients.json');args=parser.parse_args();build(args.input.resolve(),args.output.resolve(),args.dictionary.resolve())
if __name__=='__main__':main()
