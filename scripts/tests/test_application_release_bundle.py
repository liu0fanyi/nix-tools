import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

spec=importlib.util.spec_from_file_location('bundle',Path(__file__).resolve().parents[1]/'application_release_bundle.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.log=self.root/'runtime.log';self.log.write_text('synthetic runtime')
        self.bundle={'bundle_id':'fixture','controls':[], 'configuration':{'manager':'/fixed-manager','package':'/fixed-backend','frontend':'/fixed-frontend'}}
        self.report={'kind':'native-bundle-check-v1','bundle_id':'fixture','controls':[],'passed':True,'cases':sorted(b.CASES),'cleaned':True,'logs':[b.record(self.log)],'production_access':False,'daily_profile_used':False,'actual_rust_cli':True,'actual_frontend':True,'api_mocked':False}
        self.verifier=patch.object(b,'verify',return_value=self.bundle);self.verifier.start();self.addCleanup(self.verifier.stop)
    def test_valid_current_report(self):b.result_check(self.bundle,self.report)
    def test_report_rejections_before_manager(self):
        for field,value in [('kind','old-check'),('bundle_id','old'),('controls',[{}]),('passed',False),('cases',[]),('cleaned',False),('logs',[]),('production_access',True),('daily_profile_used',True),('actual_rust_cli',False),('actual_frontend',False),('api_mocked',True)]:
            with self.subTest(field=field):
                report={**self.report,field:value};run=Mock()
                with self.assertRaises(ValueError):b.prepare(self.bundle,report,'pc',perform=True,run=run)
                run.assert_not_called()
    def test_changed_runtime_log(self):
        self.log.write_text('changed')
        with self.assertRaises(ValueError):b.result_check(self.bundle,self.report)
    def test_input_drift_before_manager(self):
        with patch.object(b,'verify',side_effect=ValueError('drift')):
            run=Mock()
            with self.assertRaises(ValueError):b.prepare(self.bundle,self.report,'pc',run=run)
            run.assert_not_called()
    def test_fixed_preview_and_prepare(self):
        for perform in [False,True]:
            run=Mock();b.prepare(self.bundle,self.report,'nuc',perform=perform,run=run)
            expected=['/fixed-manager/bin/tag-native-release','--scope','nuc','--package','/fixed-backend','--frontend','/fixed-frontend']+(['--prepare'] if perform else [])
            run.assert_called_once_with(expected,check=True)
    def test_learning_registration_is_explicit_and_nuc_only(self):
        self.bundle['configuration']['register_learning_map']=True
        run=Mock();b.prepare(self.bundle,self.report,'nuc',perform=True,run=run)
        self.assertIn('--register-learning-map',run.call_args.args[0])
        run=Mock()
        with self.assertRaisesRegex(ValueError,'scoped to NUC'):b.prepare(self.bundle,self.report,'pc',run=run)
        run.assert_not_called()
    def test_learning_registration_rejects_truthy_non_boolean_values(self):
        import json
        for value in ('yes',1,[],None):
            config={k:'/fixed' for k in b.CONFIG_KEYS-{'schema'}}
            config.update(schema=1,register_learning_map=value)
            path=self.root/'config.json';path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError,'bundle-v1 configuration'):b.create(path)
    def test_reject_scope(self):
        run=Mock()
        with self.assertRaises(ValueError):b.prepare(self.bundle,self.report,'all',run=run)
        run.assert_not_called()
    def test_proof_escape(self):
        with self.assertRaises(ValueError):b.inside(self.log,self.root/'specs')
    def test_require_immutable_output(self):
        with self.assertRaises(ValueError):b.output(self.root)
    def test_tree_rejects_symlink(self):
        tree=self.root/'tree';tree.mkdir();(tree/'link').symlink_to(self.log)
        with self.assertRaises(ValueError):b.files(tree)
    def test_shared_revision_mismatch(self):
        guard=Mock();guard.consumer_revision.side_effect=['abc','def']
        with patch.object(b,'module',return_value=guard):
            with self.assertRaisesRegex(ValueError,'revision mismatch'):b.shared({'browser_source':str(self.root),'dufs_source':str(self.root)})
    def test_snapshot_drift(self):
        self.verifier.stop()
        with patch.object(b,'create',return_value={'bundle_id':'changed'}):
            with self.assertRaises(ValueError):b.verify({'config':{'path':'fixture'}})
    def test_frontend_source_drift(self):
        specs=self.root/'specs';specs.mkdir();src=self.root/'source.rs';src.write_text('current')
        proof=specs/'proof.json';proof.write_text(__import__('json').dumps({'frontend':'/fixed','source_sha256':{'source.rs':'old'},'built_artifacts_sha256':{'index.html':'old'}}))
        with self.assertRaisesRegex(ValueError,'source drift'):b.frontend({'dufs_source':str(self.root),'frontend_proof':str(proof),'frontend':'/fixed'})

class BackendEvidenceTests(unittest.TestCase):
    def test_full_and_incremental_bind_exact_source_and_packaged_cli(self):
        import json, sys, types
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);specs=root/'specs';specs.mkdir()
            package=root/'package';(package/'libexec').mkdir(parents=True)
            (package/'libexec/tag-server-workspace').write_text('actual binary')
            sha=b.digest(package/'libexec/tag-server-workspace');source={'src/main.rs':'a'*64}
            current={'full_tester_verified':True,'isolated_runtime_verified':True,
                     'sources_verified_in_tester':True,'full_tester_steps':39,
                     'source_manifest':source,'tester_image_id':'b'*64,'binary_sha256':sha}
            full=specs/'full.json';proof=specs/'package.json'
            packed={'verification_kind':'full-matrix','package':str(package),'application_entry':True,
                    'full_tester_reused_from':'specs/full.json','source_manifest':source,
                    'tester_image_id':'b'*64,'artifact_image_id':'b'*64,'binary_sha256':sha}
            config={'tag_source':str(root),'backend_proof':str(proof),'package':str(package)}
            policy=types.ModuleType('release_policy');policy.inventory=Mock(return_value=source)
            policy.verify_incremental=Mock(return_value={'binary_sha256':sha})
            def write(c=current,p=packed):
                full.write_text(json.dumps(c));proof.write_text(json.dumps(p))
            with patch.dict(sys.modules,{'release_policy':policy}):
                write();self.assertEqual(b.backend(config)['binary_sha256'],sha)
                policy.verify_incremental.assert_not_called()
                for key,value in [('full_tester_verified',False),('isolated_runtime_verified',False),
                                  ('sources_verified_in_tester',False),('full_tester_steps',38),
                                  ('source_manifest',{}),('tester_image_id','c'*64),('binary_sha256','d'*64)]:
                    with self.subTest(evidence=key):
                        write({**current,key:value})
                        with self.assertRaises(ValueError):b.backend(config)
                for key,value in [('verification_kind','unknown'),('package','/other'),('application_entry',False),
                                  ('source_manifest',{}),('artifact_image_id','c'*64),('binary_sha256','d'*64)]:
                    with self.subTest(package=key):
                        write(current,{**packed,key:value})
                        with self.assertRaises(ValueError):b.backend(config)
                write();policy.inventory.return_value={'new.rs':'f'*64}
                with self.assertRaisesRegex(ValueError,'inputs drifted'):b.backend(config)
                write(current,{**packed,'verification_kind':'native-incremental-v1',
                               'incremental_verification_from':'specs/full.json'})
                self.assertEqual(b.backend(config)['binary_sha256'],sha)
                policy.verify_incremental.assert_called_once_with(root,current)

class FixtureApplicationTests(unittest.TestCase):
    def test_reserved_assets_have_fixed_separate_roots(self):
        import sys, tomllib
        with patch.dict(sys.modules, {'application_release_bundle':b}):
            spec=importlib.util.spec_from_file_location('combination_fixture',Path(__file__).resolve().parents[1]/'check_application_bundle.py')
            fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            self.assertEqual(fixture.fixture_applications(root),'')
            for name in ('devices','recorder-bean','unknown'):(root/name).mkdir()
            apps=tomllib.loads(fixture.fixture_applications(root))['applications']
            self.assertEqual([a['name'] for a in apps],['devices','recorder-bean'])
            self.assertEqual([a['root'] for a in apps],[str(root/'devices'),str(root/'recorder-bean')])

    def test_learning_root_requires_explicit_registration_and_existing_directory(self):
        import sys, tomllib
        with patch.dict(sys.modules, {'application_release_bundle':b}):
            spec=importlib.util.spec_from_file_location('learning_fixture',Path(__file__).resolve().parents[1]/'check_application_bundle.py')
            fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            with self.assertRaisesRegex(ValueError,'root is missing'):fixture.fixture_applications(root,True)
            (root/'learning-map').mkdir()
            self.assertEqual(fixture.fixture_applications(root),'')
            apps=tomllib.loads(fixture.fixture_applications(root,True))['applications']
            self.assertEqual(apps,[{'name':'learning-map','root':str(root/'learning-map')}])

if __name__=='__main__':unittest.main()
