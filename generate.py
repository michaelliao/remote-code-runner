#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'a remote code running service tool'

import os, sys, json, subprocess

def main():
    cwd = os.path.dirname(os.path.normpath(os.path.abspath(__file__)))
    print('Set remote code runner path = %s' % cwd)
    print('Check system requirement:')
    run('sudo docker -v', 'Try install docker by command: sudo apt install docker.io')
    run('sudo python3.8 --version', 'Try install python 3.8 by command: sudo apt install python3.8')
    settings = {}
    settings['$RCR_PATH'] = cwd
    settings['$RCR_IP'] = getInput('Remote code runner listening IP', '127.0.0.1')
    settings['$RCR_PORT'] = getInput('Remote code runner listening port', '8080')
    settings['$RCR_TIMEOUT'] = getInput('Remote code runner execution timeout in seconds', '5')
    settings['$RCR_TEMP'] = getInput('Remote code runner temporary directory', '/tmp/remote-code-runner')
    yn = input('Generate release? [yN] ')
    if yn.lower() != 'y':
        exit(1)
    print('generate config.json...')
    generateFile(cwd, 'src/config.json', 'bin/config.json', settings)
    print('copy runner.py...')
    generateFile(cwd, 'src/runner.py', 'bin/runner.py', settings)
    print('generate start-runner.sh...')
    generateFile(cwd, 'src/start-runner.sh', 'bin/start-runner.sh', settings)
    print('generate warm-up-docker.sh...')
    warmUps = []
    configJson = json.loads(readFile(cwd, 'src/config.json'))
    for lang, conf in configJson['languages'].items():
        warmUps.append('echo ">>> sudo docker run -t --rm %s ls"' % conf['image'])
        warmUps.append('sudo docker run -t --rm %s ls' % conf['image'])
    writeFile(cwd, 'bin/warm-up-docker.sh', '\n'.join(warmUps))

def run(cmd, msgOnError=''):
    print('[execute] %s' % cmd)
    code = subprocess.call(cmd, shell=True)
    if code != 0:
        print(msgOnError)
        exit(1)

def getInput(prompt, default=None):
    if default:
        s = input('%s [%s]: ' % (prompt, default)).strip()
        if s == '':
            s = default
        return s
    else:
        s = input('%s: ' % prompt).strip()
        return s

def generateFile(cwd, source, dest, settings):
    content = readFile(cwd, source)
    content = replaceAll(content, settings)
    writeFile(cwd, dest, content)

def readFile(cwd, fname):
    with open(os.path.join(cwd, fname), 'r', encoding='utf-8') as f:
        return f.read()

def writeFile(cwd, fname, content):
    with open(os.path.join(cwd, fname), 'w', encoding='utf-8') as f:
        f.write(content)

def replaceAll(s, settings):
    for k, v in settings.items():
        s = s.replace(k, v)
    return s

if __name__ == '__main__':
    main()
