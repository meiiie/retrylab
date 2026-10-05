"""Read every number the deck shows from the running app (which verifies the frozen v3 runs by hash) into data.json.

Usage: python gather_data.py <out.json> [--url http://127.0.0.1:8773]
"""
import argparse
import json
import urllib.request


def get(base, path):
    with urllib.request.urlopen(base + path, timeout=60) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('out')
    parser.add_argument('--url', default='http://127.0.0.1:8773')
    args = parser.parse_args()
    status = get(args.url, '/api/v3/status')
    if status.get('state') != 'ready':
        raise SystemExit(f'v3 models not ready: {status}')
    meta = get(args.url, '/api/v3/meta')

    def session(world, policy):
        body = json.dumps({'learner_id': status['demo_learner'], 'world': world, 'policy': policy}).encode()
        request = urllib.request.Request(args.url + '/api/v3/session', data=body, method='POST', headers={
            'Content-Type': 'application/json', 'X-RetryLab-Token': status['session_token']})
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)

    sessions = {f'{w}/{p}': session(w, p) for w, p in (('irt_B', 'ppo_kt'), ('afm_B', 'ppo_afm'))}
    data = {'runs': meta['runs'], 'demo_learner': status['demo_learner'], 'meta': meta, 'sessions': sessions}
    with open(args.out, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=1)
    print(args.out)


if __name__ == '__main__':
    main()
