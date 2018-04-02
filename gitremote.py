#!/usr/bin/env python3
import json
import os
import posixpath
import shlex
import sys
import subprocess
import yaml

import requests

config = None


def run_git_remote(repo_dir, args, stdin):
    # Try our server first
    url = 'http://{}:{}/git'.format(config['server']['host'], config['server']['port'])
    try:
        response = requests.request('POST', url,
                                    data=json.dumps({'path': repo_dir, 'args': args, 'stdin': stdin}),
                                    headers={'Content-type': 'application/json'},
                                    auth=(config['server']['username'], config['server']['password']),)
    except Exception:
        # TODO: log it
        raise
    else:
        payload = response.json()
        sys.stderr.write(payload['stderr'])
        try:
            return payload['stdout'].encode(sys.stdout.encoding), payload['exitcode']
        except UnicodeEncodeError:
            return payload['stdout'].encode('utf-8'), payload['exitcode']


def run_git_local(args, stdin):
    assert not stdin  # TODO: implement this...
    try:
        return subprocess.check_output(['F:/Git/bin/git.exe'] + args), 0
    except subprocess.CalledProcessError as e:
        return e.output, e.returncode


def main():
    global config

    exe_dir = os.path.dirname(os.path.realpath(sys.executable if hasattr(sys, 'frozen') else sys.argv[0]))
    config_file = os.path.join(exe_dir, 'gitremote.yaml')

    try:
        with open(config_file) as f:
            config = yaml.load(f)
    except FileNotFoundError:
        print('Config file not found: {}'.format(config_file))
        sys.exit(1)

    args = list(map(shlex.quote, sys.argv[1:]))
    cwd = os.path.normcase(os.getcwd())
    stdin = sys.stdin.read() if '--stdin' in sys.argv[1:] else None
    for base, remote in config['repos'].items():
        base = os.path.normcase(base)
        if cwd.startswith(base):
            sub = os.path.relpath(cwd, base).replace(os.sep, posixpath.sep)
            remote_cwd = posixpath.join(remote, sub)
            output, rc = run_git_remote(remote_cwd, args, stdin)
            break
    else:
        output, rc = run_git_local(args, stdin)

    sys.stdout.write(str(output, sys.stdout.encoding))
    sys.exit(rc)


if __name__ == '__main__':
    main()
