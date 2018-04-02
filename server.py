#!/usr/bin/env python3
import os
import sys
import subprocess

import yaml
from flask import Flask, request, jsonify
from werkzeug.exceptions import Unauthorized


config = None
app = Flask(__name__)


def _strip_quotes(s):
    if s and s[0] == s[-1] and s[0] in '\'"':
        return s[1:-1]
    return s


@app.route('/git', methods=('POST',))
def git_handler():
    auth = request.authorization
    if not auth or config['server']['username'] != auth.username or config['server']['password'] != auth.password:
        raise Unauthorized()
    payload = request.get_json()
    command = ['git'] + list(map(_strip_quotes, payload['args']))
    print(command)
    if payload['stdin']:
        print('STDIN', payload['stdin'])
    with subprocess.Popen(command, cwd=payload['path'], stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        try:
            stdout, stderr = process.communicate(payload['stdin'])
        except:
            process.kill()
            process.wait()
            raise
        rc = process.poll()
    if rc:
        print('exitcode:{}\nstdout:\n{}\n\nstderr:\n{}'.format(rc, stdout, stderr))
    return jsonify(stdout=str(stdout, 'utf-8'), stderr=str(stderr, 'utf-8'), exitcode=rc)


def main():
    global config

    exe_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
    config_file = os.path.join(exe_dir, 'gitremote.yaml')

    try:
        with open(config_file) as f:
            config = yaml.load(f)
    except FileNotFoundError:
        print('Config file not found: {}'.format(config_file))
        sys.exit(1)

    if not config['server']['username'] or not config['server']['password']:
        raise Exception('Server username/password is not set')

    app.run(config['server']['host'], config['server']['port'], threaded=True)


if __name__ == '__main__':
    main()
