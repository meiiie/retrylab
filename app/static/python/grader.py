"""Practice feedback inside a disposable browser Python runtime, not an exam judge."""
import copy
import io
import json
import traceback
from contextlib import redirect_stdout, redirect_stderr


class LimitedOutput(io.StringIO):
    def write(self, text):
        remaining = max(0, 8000-self.tell())
        if remaining:
            super().write(text[:remaining])
        return len(text)


def grade_submission(source, function_name, cases):
    output = LimitedOutput()
    scope = {'__name__': '__practice__'}
    results = []
    try:
        with redirect_stdout(output), redirect_stderr(output):
            exec(compile(source, '<bai-lam>', 'exec'), scope)
            function = scope.get(function_name)
            if not callable(function):
                return {'status':'error', 'error':f'Chưa tìm thấy hàm {function_name}. Giữ đúng tên hàm trong đề bài.', 'line':None, 'tests':[], 'passed':0, 'total':len(cases)}
            for index, case in enumerate(cases):
                try:
                    actual = function(*copy.deepcopy(case['args']))
                    expected = case['expected']
                    passed = type(actual) is type(expected) and actual == expected
                    results.append({'index':index+1, 'input':repr(case['args'][0])[:500],
                                    'expected':repr(expected)[:500], 'actual':repr(actual)[:500], 'passed':bool(passed)})
                except BaseException as exception:
                    frames = traceback.extract_tb(exception.__traceback__)
                    line = next((frame.lineno for frame in reversed(frames) if frame.filename=='<bai-lam>'), None)
                    results.append({'index':index+1, 'input':repr(case['args'][0])[:500],
                                    'expected':repr(case['expected'])[:500], 'actual':f'{type(exception).__name__}: {exception}'[:500], 'passed':False, 'line':line})
        count = sum(result['passed'] for result in results)
        return {'status':'passed' if count==len(cases) else 'failed', 'tests':results,
                'passed':count, 'total':len(cases), 'stdout':output.getvalue()}
    except BaseException as exception:
        line = getattr(exception, 'lineno', None)
        if line is None:
            frames = traceback.extract_tb(exception.__traceback__)
            line = next((frame.lineno for frame in reversed(frames) if frame.filename=='<bai-lam>'), None)
        return {'status':'error', 'error':f'{type(exception).__name__}: {exception}'[:800],
                'line':line, 'tests':[], 'passed':0, 'total':len(cases), 'stdout':output.getvalue()}
