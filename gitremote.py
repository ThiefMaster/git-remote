#!/usr/bin/env python3
import json
import os
import posixpath
import shlex
import sys
import subprocess
import yaml

import paramiko
import requests

config = None


def fix_makac_args(arg):
    if arg.startswith('MaKaC'):
        return 'indico/{}'.format(arg)
    elif 'MaKaC/' in arg:
        return arg.replace('MaKaC/', 'indico/MaKaC/')
    return arg


def fix_makac_result(data):
    return data.replace(b'indico/MaKaC', b'MaKaC')


def run_git_remote(repo_dir, args):
    # Try our server first
    url = 'http://{}:{}/git'.format(config['server']['host'], config['server']['port'])
    try:
        response = requests.request('POST', url,
                                    data=json.dumps({'path': repo_dir, 'args': args}),
                                    headers={'Content-type': 'application/json'},
                                    auth=(config['server']['username'], config['server']['password']),)
    except Exception:
        # TODO: log it
        raise
        # return run_git_remote_ssh(repo_dir, args)
    else:
        payload = response.json()
        sys.stderr.write(payload['stderr'])
        return payload['stdout'].encode(sys.stdout.encoding), payload['exitcode']


def run_git_remote_ssh(repo_dir, args):
    ssh_conn = paramiko.SSHClient()
    ssh_conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_conn.connect(config['ssh']['host'], username=config['ssh']['user'], allow_agent=True)
    cmdline = 'cd {}; git {}'.format(repo_dir, ' '.join(args))
    chan = ssh_conn.get_transport().open_session()
    chan.exec_command(cmdline)
    stdin = chan.makefile('wb')
    stdout = chan.makefile('r')
    stderr = chan.makefile_stderr('r')
    stdin.close()
    sys.stderr.write(str(stderr.read(), sys.stderr.encoding))
    output = stdout.read()
    rc = chan.recv_exit_status()
    ssh_conn.close()
    return output, rc


def run_git_local(args):
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

    args = list(map(shlex.quote, map(fix_makac_args, sys.argv[1:])))
    cwd = os.path.normcase(os.getcwd())
    for base, remote in config['repos'].items():
        base = os.path.normcase(base)
        if cwd.startswith(base):
            sub = os.path.relpath(cwd, base).replace(os.sep, posixpath.sep)
            remote_cwd = posixpath.join(remote, sub)
            output, rc = run_git_remote(remote_cwd, args)
            break
    else:
        output, rc = run_git_local(args)

    sys.stdout.write(str(fix_makac_result(output), sys.stdout.encoding))
    sys.exit(rc)


if __name__ == '__main__':
    main()
