"""Local research demonstration, bound to loopback and read-only study artifacts."""
from __future__ import annotations

import argparse
import json
import mimetypes
from pathlib import Path
import secrets
import threading

from flask import Flask, jsonify, request, send_file, render_template
from werkzeug.exceptions import HTTPException

from engine import StudyEngine, ROOT
from realdata_engine import RealDataEngine, Unavailable

HERE = Path(__file__).resolve().parent
mimetypes.add_type('text/javascript', '.mjs')
mimetypes.add_type('application/wasm', '.wasm')
_frozen_pairs = []


class LazyStudy:
    """Stands in for the classic StudyEngine and builds it on first use. Building it verifies the frozen files and
    loads every classic model, which neither the new console nor a health check should wait for."""

    def __init__(self, factory):
        self._factory = factory
        self._instance = None
        self._guard = threading.Lock()

    def __getattr__(self, name):
        if name.startswith('_'):  # dunder probes (copy, pickle, ...) must not trigger the load
            raise AttributeError(name)
        if self._instance is None:
            with self._guard:
                if self._instance is None:
                    self._instance = self._factory()
        return getattr(self._instance, name)


def frozen_case_count():
    """Case count of the frozen classic study, read from its results record so that /api/health never loads the
    classic engine (which re-derives and asserts the same number when it does load)."""
    if not _frozen_pairs:
        try:
            record = json.loads((ROOT / 'research/confirmation/results.json').read_text(encoding='utf-8'))
            _frozen_pairs.append(int(record['coverage']['retained_pairs']))
        except (OSError, ValueError, KeyError, TypeError):
            return None
    return _frozen_pairs[0]


def parse_flips(raw):
    """'0,3' -> [0, 3]; empty -> None. Anything else is a client error."""
    if raw == '':
        return None
    parts = raw.split(',')
    if len(parts) > 60 or not all(part.isascii() and part.isdigit() for part in parts):
        raise ValueError('Tham số flips phải là các vị trí nguyên không âm cách nhau bằng dấu phẩy (tối đa 60).')
    return [int(part) for part in parts]


def create_app(engine=None, realdata=None, warm=False):
    app = Flask(__name__, static_folder=str(HERE / 'static'), static_url_path='/static', template_folder=str(HERE / 'templates'))
    app.config.update(MAX_CONTENT_LENGTH=32_768, TEMPLATES_AUTO_RELOAD=True)
    app.json.ensure_ascii = False
    app.json.sort_keys = False
    # StudyEngine is looked up when first needed (not at import) so a replacement of the module global is honoured.
    engine = LazyStudy(lambda: StudyEngine()) if engine is None else engine
    realdata = RealDataEngine() if realdata is None else realdata
    app.extensions['study_engine'] = engine
    app.extensions['realdata_engine'] = realdata
    app_token = secrets.token_urlsafe(32)

    @app.before_request
    def restrict_local():
        if request.host.split(':')[0] not in ('127.0.0.1', 'localhost'):
            return jsonify(error='Ứng dụng chỉ phục vụ trên localhost.'), 403
        if request.method == 'POST' and request.headers.get('X-RetryLab-Token') != app_token:
            return jsonify(error='Phiên làm việc không hợp lệ. Vui lòng tải lại trang.'), 403

    @app.after_request
    def response_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; worker-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.errorhandler(Exception)
    def handle_error(error):
        if isinstance(error, HTTPException):
            return jsonify(error=error.description), error.code
        if isinstance(error, Unavailable):
            return jsonify(error=str(error), available=False), 503
        if isinstance(error, (ValueError, KeyError)):
            return jsonify(error=str(error).strip("'")), 400
        app.logger.exception('Application error')
        return jsonify(error='Không thể xử lý yêu cầu. Xem nhật ký ứng dụng.'), 500

    @app.get('/')
    def index():
        # The shell is a few KB: read it whole so no file handle stays open behind an unfinished response.
        shell = HERE / 'static/studio/index.html'
        if not shell.is_file():
            return jsonify(error='Chưa có giao diện mới.'), 404
        response = app.response_class(shell.read_bytes(), mimetype='text/html')
        response.headers['Cache-Control'] = 'no-cache'
        return response

    @app.get('/classic')
    def classic():
        return render_template('index.html')

    @app.get('/api/health')
    def health():
        payload = {'status': 'ready', 'app': 'RetryLab'}
        pairs = frozen_case_count()
        if pairs is not None:
            payload['pairs'] = pairs
        return jsonify(**payload, read_only_study=True)

    @app.get('/api/meta')
    def metadata():
        return jsonify(**engine.metadata(), session_token=app_token)

    @app.get('/api/cases')
    def cases():
        offset = max(0, int(request.args.get('offset', 0)))
        limit = min(40, max(1, int(request.args.get('limit', 8))))
        return jsonify(engine.list_cases(offset, limit, request.args.get('q', '')[:40],
                                         request.args.get('retries', 'all'), request.args.get('trend', 'all')))

    @app.get('/api/cases/<case_id>')
    def replay(case_id):
        return jsonify(engine.replay(case_id))

    @app.get('/api/cases/<case_id>/outcome')
    def outcome(case_id):
        return jsonify(engine.outcome(case_id))

    @app.post('/api/simulate')
    def simulate():
        payload = request.get_json()
        if not isinstance(payload, dict) or not isinstance(payload.get('case_id'), str):
            raise ValueError('Yêu cầu giả lập không hợp lệ.')
        return jsonify(engine.simulate(payload['case_id'], payload.get('outcomes')))

    @app.get('/api/screening')
    def screening():
        return jsonify(engine.screening(request.args.get('model', 'first_attempt'), float(request.args.get('threshold', '.5'))))

    @app.get('/api/v3/status')
    def realdata_status():
        state = realdata.state()
        if state['state'] == 'loading':
            realdata.start_warmup()  # idempotent: the UI polls this until 'ready'
        demo_learner = None
        if state['state'] == 'ready':
            try:
                demo_learner = realdata.learners()['demo_learner']
            except Exception:
                app.logger.exception('Learner summaries failed')
                state = realdata.state()
        return jsonify(**state, session_token=app_token, demo_learner=demo_learner)

    @app.get('/api/v3/meta')
    def realdata_meta():
        return jsonify(realdata.meta())

    @app.get('/api/v3/learners')
    def realdata_learners():
        return jsonify(realdata.learners())

    @app.get('/api/v3/learners/<learner_id>')
    def realdata_learner(learner_id):
        return jsonify(realdata.learner(learner_id))

    @app.get('/api/v3/learners/<learner_id>/explain')
    def realdata_explain(learner_id):
        policy = request.args.get('policy', '')
        if not policy:
            raise ValueError('Thiếu tham số policy.')
        return jsonify(realdata.explain(learner_id, policy, parse_flips(request.args.get('flips', ''))))

    @app.post('/api/v3/whatif')
    def realdata_whatif():
        payload = request.get_json()
        if not isinstance(payload, dict) or not isinstance(payload.get('learner_id'), str) \
                or not isinstance(payload.get('flips', []), list) or len(payload.get('flips', [])) > 60:
            raise ValueError('Yêu cầu thử nghiệm không hợp lệ.')
        return jsonify(realdata.learner(payload['learner_id'], payload.get('flips', [])))

    @app.post('/api/v3/simulate')
    def realdata_simulate():
        payload = request.get_json()
        if not isinstance(payload, dict) or not all(isinstance(payload.get(k), str) for k in ('learner_id', 'world', 'policy')):
            raise ValueError('Yêu cầu mô phỏng không hợp lệ.')
        return jsonify(realdata.simulate(payload['learner_id'], payload['world'], payload['policy']))

    @app.post('/api/v3/session')
    def realdata_session():
        payload = request.get_json()
        if not isinstance(payload, dict) or not all(isinstance(payload.get(k), str) for k in ('learner_id', 'world', 'policy')):
            raise ValueError('Yêu cầu phiên học không hợp lệ.')
        return jsonify(realdata.session(payload['learner_id'], payload['world'], payload['policy'], payload.get('forced')))

    documents = {'paper': ROOT / 'paper/manuscript.pdf',
                 'paper-v3': ROOT / 'output/pdf/retrylab-v3-manuscript.pdf',
                 'paper-v3-vi': ROOT / 'output/pdf/retrylab-v3-ban-thao-tieng-viet.pdf',
                 'report': ROOT / 'paper/BAO_CAO_NGHIEN_CUU.md',
                 'source': ROOT / 'paper/manuscript.tex',
                 'study-package': ROOT / 'research/reproducibility/study_source.zip'}
    viewable = {'paper', 'paper-v3', 'paper-v3-vi'}  # PDFs open in the window; the rest download

    @app.get('/documents/<name>')
    def document(name):
        if name not in documents or not documents[name].is_file():
            return jsonify(error='Không tìm thấy tài liệu.'), 404
        return send_file(documents[name], as_attachment=name not in viewable)

    if warm:
        realdata.start_warmup()
    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='RetryLab — local frozen-model research demonstration')
    parser.add_argument('--port', type=int, default=8773)
    args = parser.parse_args()
    print('Starting RetryLab; the frozen v3 study loads in the background...', flush=True)
    application = create_app(warm=True)
    print(f'RetryLab ready: http://127.0.0.1:{args.port}', flush=True)
    application.run(host='127.0.0.1', port=args.port, debug=False, threaded=True, use_reloader=False)
