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

if __name__=='__main__':unittest.main()
