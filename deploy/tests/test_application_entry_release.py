import copy, json, os
from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import application_entry_release as release

class ReleaseTests(unittest.TestCase):
    def model(self):
        volume=lambda target:{'type':'bind','source':'/runtime/'+target.split('/')[-1],'target':target,'read_only':target not in ('/data/caddy','/config/caddy')}
        services={name:{'image':'sha256:'+'1'*64} for name in release.KEEP|release.REMOVED}
        services['caddy'].update(depends_on={name:{} for name in ['dufs','tag-server','dufs-readonly','tag-server-readonly','authelia']},
          volumes=[volume(t) for t in ['/etc/caddy/Caddyfile','/data/caddy','/config/caddy','/run/secrets/tag-peer-admin.env','/srv/dist','/run/host-ttyd']],
          ports=[{'target':5006,'published':5006},{'target':5009,'published':5009}],entrypoint=['/bin/sh','-ec'],command=['. admin.env; caddy run'],environment={'TAG_PEER_ADMIN_TOKEN':'synthetic'})
        services['readonly-gateway'].update(ports=[{'target':5008,'published':5008}],depends_on={'caddy':{}})
        return {'services':services,'networks':{'app':{'ipam':{'config':[{'subnet':'10.89.50.0/24'}]}}}}
    def test_complete_composition_removes_old_writers_and_preserves_unowned(self):
        model=self.model();saved=copy.deepcopy(model);out=release.application_compose(model)
        self.assertEqual(model,saved);self.assertEqual(set(out['services']),release.KEEP)
        for name in ['authelia','ddns-go']:self.assertEqual(out['services'][name],model['services'][name])
        caddy=out['services']['caddy'];self.assertEqual(set(caddy['depends_on']),{'authelia'})
        self.assertNotIn('TAG_PEER_ADMIN_TOKEN',caddy['environment']);self.assertEqual(caddy['entrypoint'],['caddy'])
        self.assertEqual(caddy['ports'],[{'target':5009,'published':5009}])
        targets={v['target'] for v in caddy['volumes']}
        self.assertIn('/run/secrets/caddy_lan_basic_auth',targets);self.assertNotIn('/run/secrets/tag-peer-admin.env',targets)
        self.assertNotIn('/srv/dist',targets);self.assertNotIn('/run/host-ttyd',targets)
        self.assertEqual(out['networks'],model['networks'])
    def test_unreviewed_inputs_fail_closed(self):
        for mutate in [lambda s:s.pop('authelia'),lambda s:s.update(unrelated={}),lambda s:s['caddy'].update(env_file=['unreviewed.env']),lambda s:s['caddy'].update(volumes=['ambiguous:/target']),lambda s:s['caddy'].update(ports=[{'target':9999,'published':9999}]),lambda s:s['authelia'].update(image='latest')]:
            model=self.model();mutate(model['services'])
            with self.assertRaises(ValueError):release.application_compose(model)
    def test_handover_requires_exclusive_writer_and_no_db_restore(self):
        manifest={'target_roots':release.ROOTS,'state_policy':'reuse-current-database-metadata-ca-and-identity-no-restore'}
        for target in ['pc','nuc']:
            for direction in ['update','rollback']:
                out=release.handover_plan(manifest,target,direction,units_stopped=True,ports_released=True)
                self.assertFalse(out['restore_old_database']);self.assertFalse(out['restore_old_metadata_or_ca'])
                for units,ports in [(False,True),(True,False)]:
                    with self.assertRaises(ValueError):release.handover_plan(manifest,target,direction,units_stopped=units,ports_released=ports)
    def test_startup_control_hashes_follow_reviewed_entry_and_preserve_original_images(self):
        runtime=release.RUNTIME
        before={'root':release.ROOTS['nuc'],'hostname':'nuc','uid':1000,'source_images':{'dufs-plus_'+name+'_1':'1'*64 for name in release.KEEP|release.REMOVED},'files':{runtime+'/compose.env':'1'*64,runtime+'/Caddyfile':'2'*64},'compose':['podman','compose','--env-file',runtime+'/compose.env','-f',runtime+'/old.json']}
        reviewed={runtime+'/application-compose.json':'3'*64,runtime+'/Caddyfile':'4'*64}
        after=release.rebind_startup_control(before,reviewed)
        self.assertEqual(after['source_images'],before['source_images'])
        self.assertEqual(after['files'][runtime+'/Caddyfile'],'4'*64)
        self.assertEqual(before['files'][runtime+'/Caddyfile'],'2'*64)
        self.assertEqual(after['compose'][-1],runtime+'/application-compose.json')
        incomplete=copy.deepcopy(before);incomplete['source_images'].pop(next(iter(incomplete['source_images'])))
        with self.assertRaises(ValueError):release.rebind_startup_control(incomplete,reviewed)
        for bad in [{runtime+'/application-compose.json':'3'*64},{**reviewed,'/outside/private':'5'*64},{**reviewed,runtime+'/Caddyfile':'invalid'}]:
            with self.assertRaises(ValueError):release.rebind_startup_control(before,bad)

    def test_live_inventory_is_readonly_and_refuses_writer_or_unknown_owner(self):
        records=[{'Name':'dufs-plus_'+name+'_1','Image':'1'*64,'Config':{'Labels':{'io.podman.compose.project':'dufs-plus'},'Env':['secret-not-returned']},'State':{'Running':name in release.KEEP},'HostConfig':{'RestartPolicy':{'Name':'no'}}} for name in release.KEEP|release.REMOVED]
        images,retained=release.inventory_fingerprint(records)
        self.assertEqual(len(images),9);self.assertEqual(set(retained),release.KEEP)
        self.assertNotIn('secret',json.dumps([images,retained]))
        for mutate in [lambda items:items.pop(),lambda items:items[0]['Config']['Labels'].update({'io.podman.compose.project':'other'}),lambda items:next(r for r in items if r['Name']=='dufs-plus_tag-server_1')['State'].update(Running=True)]:
            bad=copy.deepcopy(records);mutate(bad)
            with self.assertRaises(ValueError):release.inventory_fingerprint(bad)

    def test_staging_permissions_and_refusal(self):
        with tempfile.TemporaryDirectory(prefix='entry-update-dry-run-') as name:
            root=Path(name);root.chmod(0o700)
            source=root/'synthetic.entries';source.write_text('synthetic $2a$14$'+'a'*53+'\n');source.chmod(0o600)
            config={'private':'lan=true\n','readonly':'lan=true\n','pc':'peer_write_delegation=true\n'}
            result=release.prepare_synthetic_configuration(root,config,{'private':source,'readonly':source})
            self.assertFalse(result['database_copy'])
            for role in config:
                entry=root/role/'config/application-entry.toml';self.assertEqual(entry.stat().st_mode&0o777,0o600)
            with self.assertRaises(FileExistsError):release.prepare_synthetic_configuration(root,config,{'private':source,'readonly':source})
        with tempfile.TemporaryDirectory(prefix='unowned-') as name:
            with self.assertRaises(ValueError):release.prepare_synthetic_configuration(name,{}, {})

if __name__=='__main__':unittest.main()
