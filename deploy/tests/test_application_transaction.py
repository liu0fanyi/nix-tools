from contextlib import closing
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from application_entry_transaction import ConfigurationTransaction, atomic, backup_state, offline_states

class Handover(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='entry-transaction-test-');self.root=Path(self.temp.name)
        self.state=self.root/'state';self.state.mkdir(mode=0o700)
        atomic(self.state/'instance.lock','')
        with closing(sqlite3.connect(self.state/'core.db')) as db, db:
            db.execute('CREATE TABLE items(value TEXT)');db.execute("INSERT INTO items VALUES ('before')")
        (self.state/'core.db').chmod(0o600)
        (self.state/'metadata').mkdir(mode=0o700);atomic(self.state/'metadata/identity','same-key')
    def tearDown(self):self.temp.cleanup()
    def test_controller_lock_not_replaced(self):
        from application_entry_transaction import create_lock, exclusive
        path=self.root/'controller.lock';create_lock(path);inode=path.stat().st_ino
        with exclusive(path):
            create_lock(path)
            with self.assertRaises(BlockingIOError):
                with exclusive(path):pass
        self.assertEqual(path.stat().st_ino,inode)
    def test_live_writer_lock_refuses_before_backup(self):
        with (self.state/'instance.lock').open('r+') as held:
            fcntl.flock(held,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                with offline_states([self.state],lambda:None):backup_state(self.state,self.root/'backup')
        self.assertFalse((self.root/'backup').exists())
    def test_unstopped_services_refuse(self):
        def refusal():raise ValueError('writer active')
        with self.assertRaises(ValueError):
            with offline_states([self.state],refusal):backup_state(self.state,self.root/'backup')
        self.assertFalse((self.root/'backup').exists())
    def test_offline_wal_and_metadata_backup_never_overwrites_source(self):
        db=sqlite3.connect(self.state/'core.db');db.execute('PRAGMA journal_mode=WAL')
        db.execute("INSERT INTO items VALUES ('wal')");db.commit()
        # Keep SQLite handle open to exercise a real nonempty WAL, but no process writer holds the instance lock.
        inode=(self.state/'core.db').stat().st_ino
        with offline_states([self.state],lambda:None):receipt=backup_state(self.state,self.root/'backup')
        with closing(sqlite3.connect(self.root/'backup/core.db')) as copy:self.assertEqual(copy.execute('SELECT value FROM items').fetchall(),[('before',),('wal',)])
        db.close();self.assertEqual((self.state/'core.db').stat().st_ino,inode)
        self.assertFalse(receipt['restore_on_rollback']);self.assertTrue(receipt['sqlite_integrity'])
    def test_configuration_rollback_keeps_new_writes_and_identity(self):
        config=self.root/'config';atomic(config,'old')
        candidate=self.root/'candidate';atomic(candidate,'new')
        from application_entry_transaction import digest
        unit=self.root/'unit';unit.symlink_to('/nix/store/old-unit')
        oldbridge=self.root/'bridge';oldbridge.symlink_to('/nix/store/old-bridge')
        desired={config:{'kind':'file','source':str(candidate),'sha256':digest(candidate)},
                 unit:{'kind':'symlink','target':'/nix/store/new-unit'},oldbridge:{'kind':'absent'}}
        tx=ConfigurationTransaction(self.root/'transaction',desired);tx.create(desired);tx.install()
        with closing(sqlite3.connect(self.state/'core.db')) as db, db:db.execute("INSERT INTO items VALUES ('after-activation')")
        tx.install(rollback=True)
        self.assertEqual(config.read_text(),'old');self.assertEqual(os.readlink(unit),'/nix/store/old-unit')
        self.assertEqual(os.readlink(oldbridge),'/nix/store/old-bridge')
        with closing(sqlite3.connect(self.state/'core.db')) as db, db:self.assertEqual(db.execute('SELECT value FROM items').fetchall(),[('before',),('after-activation',)])
        self.assertEqual((self.state/'metadata/identity').read_text(),'same-key')
    def test_corrupted_journal_or_candidate_refused(self):
        from application_entry_transaction import digest
        config=self.root/'config';atomic(config,'old');candidate=self.root/'candidate';atomic(candidate,'new')
        desired={config:{'kind':'file','source':str(candidate),'sha256':digest(candidate)}}
        tx=ConfigurationTransaction(self.root/'transaction',desired);tx.create(desired);atomic(candidate,'changed')
        with self.assertRaises(ValueError):tx.install()
        self.assertEqual(config.read_text(),'old')
        record=tx.load();record['records'][str(self.state/'core.db')]=record['records'].pop(str(config));tx.save(record)
        with self.assertRaises(ValueError):tx.install(rollback=True)
    def test_partial_install_failure_explicit_rollback(self):
        from application_entry_transaction import digest
        config=self.root/'a-config';atomic(config,'old');candidate=self.root/'candidate';atomic(candidate,'new')
        second=self.root/'z-config';atomic(second,'old-second')
        desired={config:{'kind':'file','source':str(candidate),'sha256':digest(candidate)},
                 second:{'kind':'file','source':str(candidate),'sha256':'0'*64}}
        tx=ConfigurationTransaction(self.root/'transaction',desired);tx.create(desired)
        with self.assertRaises(ValueError):tx.install()
        self.assertEqual(config.read_text(),'new');tx.install(rollback=True)
        self.assertEqual(config.read_text(),'old');self.assertEqual(second.read_text(),'old-second')
if __name__=='__main__':unittest.main()
