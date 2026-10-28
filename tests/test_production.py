import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from core import plan, reconcile, validate
from sync_tasks import sync


class Production(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.write('config/production.json', {'producers':['producer'], 'repository':'owner/repo'})
        self.write('episodes/GT-001/episode.json', {'episode_id':'GT-001','premise':'test','summary':'test','premise_approved':True,'summary_approved':True})
        self.scene = {'episode_id':'GT-001','scene_id':'S001','revision':1,'script_sha256':hashlib.sha256(b'story').hexdigest(),'status':'approved','approval':{'by':'producer','at':'2026-10-28T00:00:00Z','source_commit':'a'*40,'issue_number':1},'estimated_seconds':60,'characters':[],'reference_assets':[],'location':'ranch','continuity_notes':''}
        self.save_scene()
        (self.root/'episodes/GT-001/scenes/S001/script.md').write_bytes(b'story')

    def tearDown(self):
        self.temp.cleanup()

    def write(self,path,data):
        p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data))

    def save_scene(self):
        self.write('episodes/GT-001/scenes/S001/scene.json',self.scene)

    def planned(self):
        return plan(self.root,'GT-001','b'*40)

    def test_one_scene_seven_tasks(self):
        self.assertEqual(len(self.planned()['tasks']),7)

    def test_draft_never_gets_scene_tasks(self):
        self.scene['status']='draft';self.save_scene()
        self.assertFalse(any(t['scene'] for t in self.planned()['tasks']))

    def test_unapproved_packaging_does_not_get_tasks(self):
        self.scene['status']='draft';self.save_scene()
        self.write('episodes/GT-001/episode.json', {'episode_id':'GT-001','premise':'','summary':'','premise_approved':False,'summary_approved':False})
        self.assertEqual(self.planned()['tasks'],[])

    def test_missing_approver_rejected(self):
        self.scene['approval']['by']=None;self.save_scene()
        with self.assertRaisesRegex(ValueError,'Unauthorized'):self.planned()

    def test_changed_hash_rejected(self):
        (self.root/'episodes/GT-001/scenes/S001/script.md').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):self.planned()

    def test_runtime_limit(self):
        self.scene['estimated_seconds']=1801;self.save_scene()
        with self.assertRaisesRegex(ValueError,'30 minutes'):self.planned()

    def test_rerun_open_and_closed_reuses_all(self):
        p=self.planned()
        issues=[{'number':i,'state':'closed' if i%2 else 'open','body':'<!-- goody-task:'+t['key']+' -->\nsha256:'+str(t['script_sha256'])} for i,t in enumerate(p['tasks'],1)]
        existing,stale=reconcile(p,issues)
        self.assertEqual(len(existing),7);self.assertEqual(stale,[])

    def test_old_revision_stale(self):
        p=self.planned()
        self.scene['revision']=2;self.save_scene()
        old={'number':12,'body':'<!-- goody-task:GT-001:S001:r1:narration -->\nsha256:'+self.scene['script_sha256']}
        self.assertEqual(reconcile(self.planned(),[old])[1],[12])

    def test_same_revision_different_hash_fails(self):
        old={'number':12,'body':'<!-- goody-task:GT-001:S001:r1:narration -->\nsha256:wrong'}
        with self.assertRaisesRegex(ValueError,'increment revision'):reconcile(self.planned(),[old])

    def test_partial_failure_retry(self):
        planned=self.planned()
        planned['stale_issue_numbers']=[]
        class Fake:
            repo='owner/repo'
            def __init__(self):self.items=[];self.fail=True
            def call(self,method,path,payload=None):
                if path.startswith('/labels'):return [] if method=='GET' else payload
                if method=='POST':
                    if len(self.items)==2 and self.fail:
                        self.fail=False;raise RuntimeError('Simulated network failure')
                    item=dict(payload,number=len(self.items)+1,html_url='https://github.com/owner/repo/issues/'+str(len(self.items)+1));self.items.append(item);return item
                number=int(path.split('/')[-1]);item=self.items[number-1]
                if method=='PATCH':item.update(payload)
                return item
        api=Fake();report={'created':[],'reused':[],'stale':[]}
        base=Path(__file__).resolve().parents[1]
        old=os.getcwd()
        try:
            os.chdir(base)
            with self.assertRaises(RuntimeError):sync(api,planned,{},report,lambda:None)
            existing,_=reconcile(planned,api.items)
            sync(api,planned,existing,{'created':[],'reused':[],'stale':[]},lambda:None)
            self.assertEqual(len(api.items),7)
        finally:os.chdir(old)

    def test_second_scene_adds_two(self):
        other=copy.deepcopy(self.scene);other['scene_id']='S002'
        self.write('episodes/GT-001/scenes/S002/scene.json',other)
        (self.root/'episodes/GT-001/scenes/S002/script.md').write_bytes(b'story')
        self.assertEqual(len(self.planned()['tasks']),9)

    def test_live_approval_rejects_bot_and_missing_record(self):
        from core import verify_approval
        class Fake:
            def call(self,*args):return {'user':{'login':'producer','type':'Bot'},'body':''}
        with patch('subprocess.run'), patch('subprocess.check_output',return_value=b'story'):
            with self.assertRaisesRegex(ValueError,'authorized human'):
                verify_approval(Fake(),self.root,self.scene,'b'*40)
        class Human:
            def call(self,*args):return {'user':{'login':'producer','type':'User'},'body':'checked'}
        with patch('subprocess.run'), patch('subprocess.check_output',return_value=b'story'):
            with self.assertRaisesRegex(ValueError,'exact approval'):
                verify_approval(Human(),self.root,self.scene,'b'*40)

    def test_pagination_includes_closed(self):
        from core import API
        api=API('owner/repo','fake')
        batch=[{'number':n,'state':'closed'} for n in range(100)]
        with patch.object(api,'call',side_effect=[batch,[{'number':101,'state':'open'}]]) as request:
            self.assertEqual(len(api.issues()),101)
            self.assertIn('state=all',request.call_args_list[0].args[1])
            self.assertIn('page=2',request.call_args_list[1].args[1])

    def test_release_missing_assets(self):
        from check_release import check
        self.write('episodes/GT-001/assets.json',{'assets':[]})
        with self.assertRaisesRegex(ValueError,'Missing current scene assets'):check(self.root,'GT-001')

    def test_release_over_limit(self):
        from check_release import check
        assets=[]
        for kind in ['narration','flow']:
            assets.append({'type':kind,'status':'approved','reviewer':'producer','reviewed_at':'today','url':'https://example.com/asset','version':1,'sha256':'a'*64,'scene_id':'S001','revision':1,'script_sha256':self.scene['script_sha256']})
        for kind in ['thumbnail','title','description','hashtags']:
            assets.append({'type':kind,'status':'approved','reviewer':'producer','reviewed_at':'today','url':'https://example.com/asset','version':1,'sha256':'a'*64,'source_commit':'b'*40})
        self.write('episodes/GT-001/assets.json',{'source_commit':'b'*40,'assets':assets,'final_runtime_seconds':1801})
        with patch('core.git',return_value='b'*40), patch('subprocess.run'), patch('subprocess.check_output',side_effect=lambda args: (self.root/args[-1].split(':',1)[1]).read_bytes()):
            with self.assertRaisesRegex(ValueError,'Final runtime'):check(self.root,'GT-001')

if __name__=='__main__':unittest.main()
