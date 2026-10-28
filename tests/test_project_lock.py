import json
import multiprocessing
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from project_lock import project_lock,state_cas

def contend(path,queue):
    try:
        with project_lock(path):queue.put('acquired')
    except ValueError:queue.put('refused')

class ProjectLockTests(unittest.TestCase):
    def test_actual_process_contention_and_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            # spawn prevents inheritance of the current thread's reentrant map.
            context=multiprocessing.get_context('spawn');queue=context.Queue()
            with project_lock(tmp):
                with project_lock(tmp):pass
                process=context.Process(target=contend,args=(tmp,queue));process.start();process.join(10)
                self.assertFalse(process.is_alive());self.assertEqual(queue.get(timeout=2),'refused')
            process=context.Process(target=contend,args=(tmp,queue));process.start();process.join(10)
            self.assertEqual(queue.get(timeout=2),'acquired')
            self.assertTrue((Path(tmp)/'.workflow.lock').exists())
    def test_state_cas_rejects_stale_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'state.json').write_text(json.dumps({'receipts':[1]}))
            with project_lock(tmp),self.assertRaisesRegex(ValueError,'CAS'):state_cas(tmp,{'receipts':[]})
