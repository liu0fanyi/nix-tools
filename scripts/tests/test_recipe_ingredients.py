"""Evidence inventory, alias collisions, hierarchy and stale review protections."""
from pathlib import Path
import copy
import importlib.util
import tempfile
import unittest

script = Path(__file__).resolve().parents[1] / 'recipe-ingredients.py'
spec = importlib.util.spec_from_file_location('ingredients', script)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class IngredientTests(unittest.TestCase):
    def setUp(self):
        self.base = {'schema_version':m.VERSION,'revision':0,'items':[], 'ambiguities':[], 'history':[]}
        self.records = [{'id':'r1','title':'番茄炒蛋','ingredients':[{'name':'西红柿','role':'main'}]}]
        self.inventory = m.collect_records(self.records,self.base)
        self.review = {'schema_version':m.VERSION,'inventory_sha256':m.fingerprint(self.inventory),
            'dictionary_sha256':m.fingerprint(self.base),'reviewer':{'kind':'ai','name':'test'},
            'new_items':[{'item':{'id':'tomato','name':'番茄','kind':'ingredient','aliases':['西红柿'],'parents':[]},
                          'reason':'此词为同义名称','occurrence_ids':['r1:0']}],
            'alias_additions':[], 'parent_additions':[], 'ambiguity_additions':[],
            'decisions':[{'raw_name':'西红柿','verdict':'mapped','item_id':'tomato','reason':'同义词', 'occurrence_ids':['r1:0']}]}

    def test_alias_index_preserves_original_and_input(self):
        dictionary=m.apply_review(self.base,self.inventory,self.review)
        indexed=m.index_records(self.records,dictionary)
        self.assertEqual(indexed[0]['ingredients'][0]['name'],'西红柿')
        self.assertIn('番茄',indexed[0]['ingredients'][0]['search_terms'])
        self.assertNotIn('canonical_id',self.records[0]['ingredients'][0])
        self.assertEqual(self.base['revision'],0)

    def test_collision_and_cycle_rejected(self):
        dictionary=m.apply_review(self.base,self.inventory,self.review)
        bad=copy.deepcopy(dictionary)
        bad['items'].append({'id':'other','name':'其他','kind':'ingredient','aliases':[' 西红柿 '],'parents':[]})
        with self.assertRaisesRegex(ValueError,'collision'):m.vocabulary(bad)
        bad=copy.deepcopy(dictionary);bad['items'][0]['parents']=['tomato']
        with self.assertRaisesRegex(ValueError,'cycle'):m.vocabulary(bad)

    def test_stale_review_omission_and_fabricated_evidence_rejected(self):
        bad=copy.deepcopy(self.inventory);bad['recipe_count']=2
        with self.assertRaisesRegex(ValueError,'stale'):m.apply_review(self.base,bad,self.review)
        bad=copy.deepcopy(self.review);bad['decisions']=[]
        with self.assertRaisesRegex(ValueError,'omitted'):m.apply_review(self.base,self.inventory,bad)
        bad=copy.deepcopy(self.review);bad['new_items'][0]['occurrence_ids']=['fake:0']
        with self.assertRaisesRegex(ValueError,'invented'):m.apply_review(self.base,self.inventory,bad)
        bad=copy.deepcopy(self.base);bad['revision']=1
        with self.assertRaisesRegex(ValueError,'changed'):m.apply_review(bad,self.inventory,self.review)

    def test_ambiguity_remains_unmapped(self):
        review=copy.deepcopy(self.review);review['new_items']=[]
        review['ambiguity_additions']=[{'name':'西红柿','candidate_ids':[], 'reason':'假设方言证据不足','occurrence_ids':['r1:0']}]
        review['decisions'][0].update(verdict='ambiguous',item_id=None)
        dictionary=m.apply_review(self.base,self.inventory,review)
        ingredient=m.index_records(self.records,dictionary)[0]['ingredients'][0]
        self.assertIsNone(ingredient['canonical_id']);self.assertEqual(ingredient['mapping_status'],'ambiguous')
        self.assertEqual(ingredient['search_terms'],['西红柿'])

    def test_child_search_does_not_expand_to_sibling(self):
        dictionary={'schema_version':m.VERSION,'revision':1,'items':[
            {'id':'mushroom','name':'蘑菇','kind':'group','aliases':[],'parents':[]},
            {'id':'shiitake','name':'香菇','kind':'ingredient','aliases':[],'parents':['mushroom']},
            {'id':'seafood','name':'海鲜菇','kind':'ingredient','aliases':[],'parents':['mushroom']}],
            'ambiguities':[], 'history':[]}
        records=[{'id':'r','title':'香菇','ingredients':[{'name':'海鲜菇','role':'main','evidence':['source']}]}]
        ingredient=m.index_records(records,dictionary)[0]['ingredients'][0]
        self.assertIn('蘑菇',ingredient['search_terms']);self.assertNotIn('香菇',ingredient['search_terms'])
        self.assertNotIn('evidence',ingredient)

    def test_review_packet_contains_all_names_and_bounds_examples(self):
        records=[{'id':f'r{n}','title':'番茄','ingredients':[{'name':'西红柿','role':'main'}]} for n in range(20)]
        inventory=m.collect_records(records,self.base)
        packet=m.review_packet(inventory,self.base)
        self.assertEqual(len(packet['entries']),1)
        self.assertEqual(packet['entries'][0]['occurrence_count'],20)
        self.assertEqual(len(packet['entries'][0]['sample_occurrences']),3)
        self.assertEqual(packet['inventory_sha256'],m.fingerprint(inventory))

    def test_directory_rejects_unsafe_links_and_keeps_data_inert(self):
        with tempfile.TemporaryDirectory() as temp:
            parent=Path(temp);(parent/'recipe.html').write_text('fixture')
            record={'id':'r1','title':'fixture','page':'recipe.html','thumbnail':None,'ingredients':[{'name':'{{SCRIPT}}</script><script>evil()</script>','role':'main'}]}
            page=m.render_directory([record],parent)
            self.assertIn('\\u003c/script\\u003e',page)
            self.assertIn('{{SCRIPT}}',page)
            record['page']='javascript:evil()'
            with self.assertRaisesRegex(ValueError,'safe relative'):m.render_directory([record],parent)
            record['page']='missing.html'
            with self.assertRaisesRegex(ValueError,'missing'):m.render_directory([record],parent)

    def test_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'dictionary.json'
            m.write_new(path,{'first':True})
            with self.assertRaises(FileExistsError):m.write_new(path,{'second':True})
            self.assertEqual(m.load(path),{'first':True})
            self.assertEqual(list(Path(temp).iterdir()),[path])


if __name__=='__main__':unittest.main()
