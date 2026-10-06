"""Pure evidence/review transitions; no model or filesystem access."""
import copy


def objects(recipe):
    facts = [f for s in recipe['steps'] + recipe['variants'] for f in s['facts']]
    items = recipe['ingredients'] + recipe['steps'] + recipe['variants'] + facts + recipe['evidence'] + recipe['frames'] + recipe['issues']
    return facts, {i['id']: i for i in items}


def validate_review(recipe, result):
    facts, ids = objects(recipe)
    evidence = {e['id'] for e in recipe['evidence']}
    for name, key, items in [('fact_reviews', 'fact_id', facts), ('ingredient_reviews', 'ingredient_id', recipe['ingredients']), ('issue_reviews', 'issue_id', recipe['issues'])]:
        reviews = result.get(name)
        if not isinstance(reviews, list) or len(reviews) != len(items) or {r[key] for r in reviews} != {i['id'] for i in items}:
            raise ValueError('review must cover every ' + key + ' exactly once')
        for r in reviews:
            if not set(r['evidence_ids']) <= evidence:
                raise ValueError('unknown review evidence')
            if (r.get('verdict') == 'supported' or r.get('resolution') == 'resolved') and not r['evidence_ids']:
                raise ValueError('positive review needs provided evidence')
    for review in result['issue_reviews']:
        issue = ids[review['issue_id']]
        if review['resolution'] == 'resolved' and issue['code'] == 'missing_image' and any(t in ids and 'selected_frame_id' in ids[t] and ids[t]['selected_frame_id'] is None for t in issue['target_ids']):
            raise ValueError('missing image cannot resolve without an actual selected frame')
    requests = result.get('repair_requests')
    if not isinstance(requests, list):
        raise ValueError('repair_requests must be explicit')
    editable = {i['id'] for i in recipe['ingredients'] + recipe['steps'] + recipe['variants'] + facts}
    if len({r['target_id'] for r in requests}) != len(requests) or not {r['target_id'] for r in requests} <= editable:
        raise ValueError('unknown or duplicate repair target')
    issue_ids = [i['id'] for i in result['issues']]
    if len(issue_ids) != len(set(issue_ids)) or set(issue_ids) & set(ids):
        raise ValueError('duplicate or overwritten review issue')
    for issue in result['issues']:
        if not set(issue['target_ids']) <= ids.keys() or not set(issue['evidence_ids']) <= evidence or issue['resolution'] != 'open':
            raise ValueError('invalid new review issue')


def pending(recipe):
    facts, _ = objects(recipe)
    for item in recipe['ingredients'] + facts:
        if item['review_status'] == 'needs_review' and not any(i['resolution'] == 'open' and item['id'] in i['target_ids'] for i in recipe['issues']):
            key = 'issue_pending_' + item['id']
            existing = next((i for i in recipe['issues'] if i['id'] == key), None)
            if existing:
                existing.update(resolution='open', resolution_note=None)
            else:
                recipe['issues'].append({'id': key, 'code': 'other', 'target_ids': [item['id']], 'description': '该项证据仍需独立核对。', 'evidence_ids': item['evidence_ids'], 'resolution': 'open', 'resolution_note': None})


def apply_review(recipe, result):
    validate_review(recipe, result)
    updated = copy.deepcopy(recipe)
    facts, ids = objects(updated)
    for name, key in [('fact_reviews', 'fact_id'), ('ingredient_reviews', 'ingredient_id')]:
        for review in result[name]:
            item = ids[review[key]]
            item['review_status'] = review['verdict']
            # Preserve original evidence, append independently cited provided evidence.
            item['evidence_ids'] = list(dict.fromkeys(item['evidence_ids'] + review['evidence_ids']))
    for review in result['issue_reviews']:
        issue = ids[review['issue_id']]
        issue['resolution'] = review['resolution']
        issue['resolution_note'] = review['reason'] if review['resolution'] == 'resolved' else None
        issue['evidence_ids'] = list(dict.fromkeys(issue['evidence_ids'] + review['evidence_ids']))
    updated['issues'].extend(copy.deepcopy(result['issues']))
    pending(updated)
    updated['status'] = 'draft'
    return updated


def apply_repair(recipe, result, allowed_targets):
    updated = copy.deepcopy(recipe)
    facts, ids = objects(updated)
    categories = {}
    for item in updated['ingredients']:
        categories[item['id']] = {'name', 'quantity', 'evidence_ids'}
    for item in facts:
        categories[item['id']] = {'text', 'measure', 'ingredient_ids', 'evidence_ids'}
    for item in updated['steps']:
        categories[item['id']] = {'depends_on', 'evidence_windows', 'image_goal'}
    for item in updated['variants']:
        categories[item['id']] = {'name'}
    changed = set()
    for change in result['changes']:
        key, field = change['target_id'], change['field']
        if key not in allowed_targets or field not in categories.get(key, set()) or (key, field) in changed:
            raise ValueError('repair field/target outside whitelist or duplicated')
        changed.add((key, field))
        ids[key][field] = copy.deepcopy(change['value'])
        if 'review_status' in ids[key]:
            ids[key]['review_status'] = 'needs_review'
    existing = {i['id']: i for i in updated['issues']}
    seen = set()
    for issue in result['issue_updates']:
        old = existing.get(issue['id'])
        if not old or issue['id'] in seen or not set(old['target_ids']) & set(allowed_targets) or issue['code'] != old['code'] or issue['target_ids'] != old['target_ids']:
            raise ValueError('repair cannot remove/reassign/overwrite unrelated issues')
        seen.add(issue['id'])
        old['description'] = issue['description']
        old['evidence_ids'] = list(dict.fromkeys(old['evidence_ids'] + issue['evidence_ids']))
        # A repair proposal cannot certify itself. Only the next independent review resolves it.
        old['resolution'] = 'open'; old['resolution_note'] = None
    updated['status'] = 'draft'; pending(updated)
    return updated


def add_observations(recipe, response, task_id):
    updated = copy.deepcopy(recipe)
    frames = {f['id']: f for f in updated['frames']}
    for n, observation in enumerate(response['observations']):
        frame = frames[observation['frame_id']]
        evidence_id = 'ev_visual_' + task_id[:12] + '_' + str(n)
        updated['evidence'].append({'id': evidence_id, 'kind': 'frame', 'interval': {'start': frame['timestamp'], 'end': min(updated['source']['duration_seconds'], frame['timestamp'] + .25)}, 'cue_ids': [], 'frame_id': frame['id'], 'quote': None, 'observation': observation['observation']})
        updated['issues'].append({'id': 'issue_visual_' + task_id[:12] + '_' + str(n), 'code': 'source_conflict' if observation['verdict'] == 'needs_review' else 'other', 'target_ids': [observation['target_id']], 'description': '新增画面观察待独立核对：' + observation['observation'], 'evidence_ids': [evidence_id], 'resolution': 'open', 'resolution_note': None})
    return updated
