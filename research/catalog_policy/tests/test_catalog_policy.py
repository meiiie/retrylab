import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import CATALOG, TASKS, Filter, State, Student, WORLDS, logs, fit, nll, HORIZON


class CatalogPolicyTests(unittest.TestCase):
    def test_catalog_contract(self):
        self.assertEqual(len(TASKS),12)
        self.assertEqual(len({t['id'] for t in TASKS}),12)
        for task in TASKS:
            self.assertIn(task['skill'],range(3))
            self.assertTrue(task['description'] and task['hints'] and task['starter'])
            self.assertEqual(len(task['tests']),8)
        self.assertEqual([sum(t['skill']==k for t in TASKS) for k in range(3)],[4,4,4])

    def test_prefix_prediction_has_no_future_label(self):
        model=Filter(.1,.2,.1,.6)
        a,b=State(),State()
        for action,y in [(0,0),(0,1),(5,0)]:
            a.observe(model,action,y)
            b.observe(model,action,y)
        p0,after0=model.observe(a.beliefs,a.counts,10,0)
        p1,after1=model.observe(b.beliefs,b.counts,10,1)
        self.assertEqual(p0,p1)
        self.assertNotEqual(after0,after1)
        self.assertEqual(a.features(),b.features())

    def test_repeat_pass_gives_less_mastery_credit(self):
        naive,aware=Filter(.1,.2,.1,0),Filter(.1,.2,.1,.7)
        beliefs,counts=[.3]*3,[2]+[0]*11
        self.assertLess(aware.observe(beliefs,counts,0,1)[1][0],naive.observe(beliefs,counts,0,1)[1][0])

    def test_action_mask_excludes_solved_and_three_failures(self):
        state,model=State(),Filter(.1,.2,.1,.6)
        state.observe(model,0,1)
        for _ in range(3):
            state.observe(model,1,0)
        self.assertNotIn(0,state.legal())
        self.assertNotIn(1,state.legal())
        self.assertEqual(len(state.features()),28)

    def test_repair_only_changes_responses_not_transfer(self):
        for seed in range(30):
            student=Student(WORLDS[1],seed)
            for _ in range(HORIZON):
                student.step(0)
            self.assertEqual(student.probe_expectation(),student.initial)

    def test_train_validation_eval_namespaces_disjoint(self):
        config=json.loads(Path(__file__).resolve().parents[1].joinpath('protocol.json').read_text())
        partitions=[]
        for offset,n in [(1000000,config['settings']['model_train_episodes']),
                         (10000000,config['settings']['model_validation_episodes']),
                         (30000000,config['settings']['training_steps']//12+1)]:
            partitions.append({offset+s*10000+i for s in config['seeds'] for i in range(n)})
        partitions.append({90000000+w*100000+i for w in range(5) for i in range(config['settings']['evaluation_learners'])})
        for i,part in enumerate(partitions):
            for other in partitions[i+1:]:
                self.assertFalse(part & other)

    def test_grid_fit_and_probabilities(self):
        histories=logs(42,8)
        model=fit(histories,True)
        self.assertLess(nll(model,histories),2)
        state=State()
        for a,y in histories[0]:
            p=state.observe(model,a,y)
            self.assertTrue(0<p<1)
            self.assertTrue(all(0<=b<=1 for b in state.beliefs))


if __name__=='__main__':
    unittest.main()
