#!/usr/bin/env python3
"""Collect ingredient inventories, apply reviewed vocabulary changes, rebuild search indexes."""
from pathlib import Path
import argparse
import copy
import functools
import hashlib
import json
import os
import re
import tempfile
import unicodedata

VERSION = '1.0.0'
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DICTIONARY = ROOT / 'config/recipe/ingredients.json'


def normalize(value):
    return unicodedata.normalize('NFKC', value).strip().lower()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'), parse_constant=lambda value: (_ for _ in ()).throw(ValueError('non-finite JSON number: ' + value)))


def fingerprint(value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(data).hexdigest()


def write_new(path, value, text=False):
    """Publish a new file atomically, never overwrite a previous result."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.ingredient-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            if text:
                stream.write(value)
            else:
                json.dump(value, stream, ensure_ascii=False, indent=2)
                stream.write('\n')
        os.chmod(temporary, 0o644)
        os.link(temporary, path)
    finally:
        os.unlink(temporary)


def fields(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(f'{label}: fields must be {sorted(expected)}')


def strings(values, label, empty=True):
    if not isinstance(values, list) or (not values and not empty):
        raise ValueError(f'{label}: expected list')
    if any(not isinstance(x, str) or not x.strip() for x in values) or len(values) != len(set(values)):
        raise ValueError(f'{label}: nonempty unique strings required')


def vocabulary(dictionary):
    fields(dictionary, ['schema_version', 'revision', 'items', 'ambiguities', 'history'], 'dictionary')
    if dictionary['schema_version'] != VERSION or type(dictionary['revision']) is not int or dictionary['revision'] < 0:
        raise ValueError('invalid dictionary version/revision')
    if not isinstance(dictionary['items'], list) or not isinstance(dictionary['ambiguities'], list) or not isinstance(dictionary['history'], list):
        raise ValueError('invalid dictionary arrays')
    items, names = {}, {}
    for item in dictionary['items']:
        fields(item, ['id', 'name', 'kind', 'aliases', 'parents'], 'item')
        if not isinstance(item['id'], str) or not re.fullmatch(r'[a-z][a-z0-9_]*', item['id']) or item['id'] in items:
            raise ValueError('invalid or duplicate ingredient ID')
        if not isinstance(item['name'], str) or not item['name'].strip() or item['kind'] not in ['ingredient', 'group']:
            raise ValueError('invalid ingredient name/kind')
        strings(item['aliases'], 'aliases'); strings(item['parents'], 'parents')
        items[item['id']] = item
        for name in [item['name']] + item['aliases']:
            key = normalize(name)
            if key in names:
                raise ValueError('alias collision: ' + name)
            names[key] = item['id']
    active, done = set(), set()
    def visit(item_id):
        if item_id in active:
            raise ValueError('ingredient hierarchy cycle')
        if item_id in done:
            return
        active.add(item_id)
        for parent in items[item_id]['parents']:
            if parent not in items:
                raise ValueError('unknown ingredient parent')
            visit(parent)
        active.remove(item_id); done.add(item_id)
    for item_id in items:
        visit(item_id)
    ambiguous = set()
    for entry in dictionary['ambiguities']:
        fields(entry, ['name', 'candidate_ids', 'reason'], 'ambiguity')
        if not isinstance(entry['name'], str) or not entry['name'].strip() or not isinstance(entry['reason'], str) or not entry['reason'].strip():
            raise ValueError('ambiguity requires name and reason')
        strings(entry['candidate_ids'], 'candidate_ids')
        key = normalize(entry['name'])
        if key in ambiguous or key in names or not set(entry['candidate_ids']) <= items.keys():
            raise ValueError('ambiguous name collides or references unknown ingredients')
        ambiguous.add(key)
    return items, names, ambiguous


def resolve(name, dictionary):
    _, names, ambiguous = vocabulary(dictionary)
    key = normalize(name)
    return None if key in ambiguous else names.get(key)


def collect_records(records, dictionary):
    _, names, ambiguous = vocabulary(dictionary)
    occurrences, inventory = {}, {}
    for record in records:
        if not isinstance(record['id'], str) or not record['id'] or not isinstance(record['ingredients'], list):
            raise ValueError('invalid recipe record')
        for n, ingredient in enumerate(record['ingredients']):
            raw = ingredient['name']
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError('empty ingredient name')
            occurrence_id = f'{record["id"]}:{n}'
            if occurrence_id in occurrences:
                raise ValueError('duplicate recipe ID/occurrence')
            occurrence = {'id': occurrence_id, 'recipe_id': record['id'], 'recipe_title': record['title'],
                          'raw_name': raw, 'role': ingredient.get('role', 'main'),
                          'evidence': ingredient.get('evidence', [])}
            occurrences[occurrence_id] = occurrence
            inventory.setdefault(raw, []).append(occurrence_id)
    data = {'schema_version': VERSION, 'dictionary_sha256': fingerprint(dictionary),
            'records_sha256': fingerprint(records), 'recipe_count': len(records),
            'entries': [{'raw_name': name, 'mapped_id': None if normalize(name) in ambiguous else names.get(normalize(name)), 'occurrence_ids': inventory[name]}
                        for name in sorted(inventory)], 'occurrences': list(occurrences.values())}
    return data


def input_records(source):
    source = Path(source)
    if source.is_file():
        data = load(source)
        if not isinstance(data, list):
            raise ValueError('index input must be a recipe record list')
        return data
    paths = sorted(source.glob('*/recipe.internal.json'))
    records = []
    for path in paths:
        data = load(path)
        evidence = {entry['id']: entry for entry in data['evidence']}
        records.append({'id': data['source']['video_id'], 'title': data['title'],
                        'ingredients': [{'name': i['name'], 'role': i['role'],
                                         'evidence': [evidence[eid] for eid in i['evidence_ids']]}
                                        for i in data['ingredients']]})
    if not records:
        raise ValueError('no internal recipe inputs; pass a search-index.json or internal recipe directory')
    return records


def apply_review(dictionary, inventory, review):
    vocabulary(dictionary)
    fields(review, ['schema_version', 'inventory_sha256', 'dictionary_sha256', 'reviewer',
                    'new_items', 'alias_additions', 'parent_additions', 'ambiguity_additions', 'decisions'], 'review')
    if review['schema_version'] != VERSION or review['inventory_sha256'] != fingerprint(inventory):
        raise ValueError('stale or invalid inventory review')
    if review['dictionary_sha256'] != fingerprint(dictionary) or inventory['dictionary_sha256'] != fingerprint(dictionary):
        raise ValueError('dictionary changed since collection/review')
    fields(review['reviewer'], ['kind', 'name'], 'reviewer')
    if review['reviewer']['kind'] not in ['ai', 'human'] or not isinstance(review['reviewer']['name'], str) or not review['reviewer']['name'].strip():
        raise ValueError('invalid reviewer identity')
    for field in ['new_items', 'alias_additions', 'parent_additions', 'ambiguity_additions', 'decisions']:
        if not isinstance(review[field], list):
            raise ValueError('invalid review array: ' + field)
    occurrences = {x['id']: x for x in inventory['occurrences']}
    entries = {x['raw_name']: x for x in inventory['entries']}
    def references(change, permit_empty=False):
        if not isinstance(change['reason'], str) or not change['reason'].strip():
            raise ValueError('missing review reason')
        strings(change['occurrence_ids'], 'occurrence_ids', empty=permit_empty)
        if not set(change['occurrence_ids']) <= occurrences.keys():
            raise ValueError('invented ingredient occurrence')
    result = copy.deepcopy(dictionary)
    for change in review['new_items']:
        fields(change, ['item', 'reason', 'occurrence_ids'], 'new item')
        references(change, permit_empty=change['item']['kind'] == 'group')
        result['items'].append(copy.deepcopy(change['item']))
    by_id = {item['id']: item for item in result['items']}
    for change in review['alias_additions']:
        fields(change, ['item_id', 'alias', 'reason', 'occurrence_ids'], 'alias addition'); references(change)
        if change['item_id'] not in by_id:
            raise ValueError('alias target missing')
        if not isinstance(change['alias'], str) or not change['alias'].strip():
            raise ValueError('invalid alias')
        by_id[change['item_id']]['aliases'].append(change['alias'])
    for change in review['parent_additions']:
        fields(change, ['item_id', 'parent_id', 'reason', 'occurrence_ids'], 'parent addition'); references(change)
        if change['item_id'] not in by_id or change['parent_id'] not in by_id:
            raise ValueError('parent target missing')
        by_id[change['item_id']]['parents'].append(change['parent_id'])
    for change in review['ambiguity_additions']:
        fields(change, ['name', 'candidate_ids', 'reason', 'occurrence_ids'], 'ambiguity addition'); references(change)
        result['ambiguities'].append({key: copy.deepcopy(change[key]) for key in ['name', 'candidate_ids', 'reason']})
    vocabulary(result)
    decisions = {}
    for decision in review['decisions']:
        fields(decision, ['raw_name', 'verdict', 'item_id', 'reason', 'occurrence_ids'], 'decision'); references(decision)
        name = decision['raw_name']
        if name not in entries or name in decisions or not set(decision['occurrence_ids']) <= set(entries[name]['occurrence_ids']):
            raise ValueError('decision evidence must come from its actual name')
        if decision['verdict'] not in ['mapped', 'ambiguous', 'keep_unmapped']:
            raise ValueError('invalid mapping verdict')
        mapped = resolve(name, result)
        if decision['verdict'] == 'mapped':
            if mapped is None or mapped != decision['item_id']:
                raise ValueError('decision disagrees with vocabulary')
        elif decision['item_id'] is not None or mapped is not None:
            raise ValueError('unresolved decision must remain unmapped')
        if decision['verdict'] == 'ambiguous' and normalize(name) not in {normalize(a['name']) for a in result['ambiguities']}:
            raise ValueError('ambiguous decision must be retained in dictionary')
        decisions[name] = decision
    if set(decisions) != set(entries):
        raise ValueError('review omitted inventory names')
    result['revision'] += 1
    result['history'].append({'inventory_sha256': fingerprint(inventory), 'review_sha256': fingerprint(review),
                              'reviewer': review['reviewer'], 'mapped_names': sum(x['verdict'] == 'mapped' for x in decisions.values()),
                              'unresolved_names': [x['raw_name'] for x in decisions.values() if x['verdict'] != 'mapped']})
    return result


def review_packet(inventory, dictionary):
    vocabulary(dictionary)
    if inventory['dictionary_sha256'] != fingerprint(dictionary):
        raise ValueError('dictionary changed since inventory collection')
    occurrences = {entry['id']: entry for entry in inventory['occurrences']}
    entries = []
    for entry in inventory['entries']:
        sample_ids = entry['occurrence_ids'][:3]
        entries.append({'raw_name': entry['raw_name'], 'mapped_id': entry['mapped_id'],
                        'occurrence_count': len(entry['occurrence_ids']),
                        'sample_occurrences': [occurrences[item] for item in sample_ids]})
    return {'schema_version': VERSION, 'inventory_sha256': fingerprint(inventory),
            'dictionary_sha256': fingerprint(dictionary), 'recipe_count': inventory['recipe_count'],
            'entries': entries, 'dictionary_items': dictionary['items'], 'ambiguities': dictionary['ambiguities'],
            'sampling_note': 'All unique names are present; at most three occurrences per name. Retrieve more from inventory when ambiguous. Not a full evidence review of every recipe.'}


def index_records(records, dictionary):
    items, names, ambiguous = vocabulary(dictionary)
    @functools.lru_cache(maxsize=None)
    def terms(item_id):
        item = items[item_id]
        result = [item['name']] + item['aliases']
        for parent in item['parents']:
            result.extend(terms(parent))
        return tuple(dict.fromkeys(result))
    result = copy.deepcopy(records)
    for record in result:
        for ingredient in record['ingredients']:
            key = normalize(ingredient['name'])
            mapped = None if key in ambiguous else names.get(key)
            ingredient.pop('evidence', None)
            ingredient['canonical_id'] = mapped
            ingredient['search_terms'] = list(dict.fromkeys([ingredient['name']] + (list(terms(mapped)) if mapped else [])))
            ingredient['mapping_status'] = 'mapped' if mapped else ('ambiguous' if key in ambiguous else 'unmapped')
        record['ingredient_dictionary_revision'] = dictionary['revision']
    return result



def render_directory(records, source_parent):
    for record in records:
        for field in ['page', 'thumbnail']:
            value = record.get(field)
            if field == 'thumbnail' and value is None:
                continue
            if not isinstance(value, str) or not value or value.startswith('/') or '..' in Path(value).parts or ':' in value or '\\' in value:
                raise ValueError('directory requires safe relative page/image paths')
            path = source_parent / value
            if not path.is_file() or not path.resolve().is_relative_to(source_parent.resolve()):
                raise ValueError('directory references missing/outside file: ' + value)
        if not isinstance(record.get('issues', 0), int):
            raise ValueError('invalid issue count')
        record.setdefault('issues', 0)
    payload = json.dumps(records, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    scripts = (ROOT / 'scripts/recipe-ingredient-search.js').read_text() + '\n' + (ROOT / 'scripts/recipe-directory.js').read_text()
    values = {'COUNT': str(len(records)), 'DATA': payload, 'SCRIPT': scripts}
    return re.sub(r'\{\{(COUNT|DATA|SCRIPT)\}\}', lambda match: values[match[1]], (ROOT / 'scripts/recipe-directory.html').read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ['collect', 'prepare-review', 'reindex', 'directory']:
        command = commands.add_parser(name)
        command.add_argument('--input', required=True, type=Path)
        command.add_argument('--dictionary', type=Path, default=DEFAULT_DICTIONARY)
        command.add_argument('--output', required=True, type=Path)
    command = commands.add_parser('apply')
    command.add_argument('--inventory', required=True, type=Path)
    command.add_argument('--review', required=True, type=Path)
    command.add_argument('--dictionary', type=Path, default=DEFAULT_DICTIONARY)
    command.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    dictionary = load(args.dictionary)
    try:
        if args.command == 'collect':
            result = collect_records(input_records(args.input), dictionary)
        elif args.command == 'prepare-review':
            result = review_packet(load(args.input), dictionary)
        elif args.command == 'apply':
            result = apply_review(dictionary, load(args.inventory), load(args.review))
        elif args.command == 'reindex':
            result = index_records(input_records(args.input), dictionary)
        else:
            records = index_records(input_records(args.input), dictionary)
            result = render_directory(records, args.input.parent)
        if args.command == 'directory' and args.output.parent.resolve() != args.input.parent.resolve():
            raise ValueError('directory HTML must be beside the input index to preserve relative links')
        write_new(args.output, result, text=args.command == 'directory')
    except (ValueError, KeyError, TypeError, FileExistsError) as error:
        parser.exit(2, f'ingredient review failed: {error}\n')
    print(json.dumps({'output': str(args.output), 'command': args.command,
                      'sha256': fingerprint(result)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
