"""Only app-authored reference code is executed here; no downloaded/student code."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'app/static/python'))
sys.path.insert(0,str(ROOT/'app/tests'))
sys.path.insert(0,str(ROOT/'research/catalog_policy'))
from grader import grade_submission
from practice_browser_check import SOLUTIONS
from core import TASKS


class ReferenceSolutions(unittest.TestCase):
    def test_all_96_cases(self):
        self.assertEqual(set(SOLUTIONS),{task['id'] for task in TASKS})
        for task in TASKS:
            with self.subTest(task=task['id']):
                result=grade_submission(SOLUTIONS[task['id']],task['functionName'],task['tests'])
                self.assertEqual(result['status'],'passed',result)


if __name__=='__main__':
    unittest.main()
