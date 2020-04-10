#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'a remote code running service'

import os, sys, time, json, shutil, subprocess, threading
from urllib import parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

class Dict(dict):
    def __init__(self, **kw):
        super().__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

def configHook(d):
    kw = dict()
    for k, v in d.items():
        if isinstance(v, str):
            kw[k] = os.path.expandvars(v)
        else:
            kw[k] = v
    return Dict(**kw)

APP_DIR = os.path.dirname(os.path.normpath(os.path.abspath(__file__)))

with open(os.path.join(APP_DIR, 'config.json'), 'r', encoding='utf-8') as f:
    CONFIG = json.load(f, object_hook=configHook)

print('load config:\n%s' % json.dumps(CONFIG, indent=4))

HTML_INDEX = '''
<html>
    <head>
        <title>Remote Code Runner</title>
        <script src="https://code.jquery.com/jquery-3.4.1.min.js"></script>
        <script>
            $(function () {
                $('#codeForm').submit(function (e) {
                    e.preventDefault();
                    $('#timeout').text('');
                    $('#response').text('');
                    var data = {
                        language: $('#language').val(),
                        code: $('#code').val()
                    };
                    $.ajax({
                        type: 'POST',
                        url: '/run',
                        data: JSON.stringify(data),
                        contentType: 'application/json',
                        dataType: 'json',
                        success: function (resp) {
                            $('#timeout').text(resp.timeout);
                            $('#response').text(resp.output==='' ? '(EMPTY)' : resp.output);
                        },
                        error: function (jqXHR, status, err) {
                            $('#response').text('ERROR: ' + status);
                        }
                    });
                });
            });
        </script>
    </head>
    <body>
        <form id="codeForm" action="/run">
            <p><select id="language" name="language">
''' + ''.join(sorted(['<option value="%s">%s</option>' % (lang, lang.capitalize()) for lang in CONFIG.languages.keys()])) + '''
            </select></p>
            <textarea id="code" name="code" style="width:90%;height:300px"></textarea>
            <p><button type="submit">Run</button></p>
        </form>
        <p>Timeout: <span id="timeout" style="color:red"></span></p>
        <p>Response:</p>
        <pre><code id="response"></code></pre>
    </body>
</html>
'''

globalIdCounter = 0
globalIdCounterLock = threading.Lock()

def nextId():
    global globalIdCounter
    with globalIdCounterLock:
        globalIdCounter += 1
        return globalIdCounter

def run(cmd, cwd, timeout):
    result = dict(error=False, timeout=False, truncated=False, output='')
    try:
        output = subprocess.check_output(cmd.split(' '), cwd=cwd, stderr=subprocess.STDOUT, timeout=timeout)
        output = decode(output)
        if len(output) > 4000:
            result['output'] = output[:4000]
            result['truncated'] = True
        else:
            result['output'] = output
    except subprocess.TimeoutExpired:
        result['timeout'] = True
    except subprocess.CalledProcessError as e:
        result['error'] = True
    return result

def decode(s):
    try:
        return s.decode('utf-8')
    except UnicodeDecodeError:
        return s.decode('gbk')

class RunnerHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.sendResponse(HTML_INDEX, 'text/html')
        elif self.path == '/health':
            self.sendResponse(b'{"status":"UP"}')
        else:
            self.responseError(404)

    def do_POST(self):
        if self.path != '/run':
            return self.responseError(404)
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])).decode('utf-8'))
        lang = body['language']
        code = body['code']
        if not lang in CONFIG.languages:
            raise KeyError('language not found: ' + lang)
        start = time.time()
        print('[%s] prepare...' % lang)
        tempDir = self.createTempDir()
        print('[%s] create temp dir: %s' % (lang, tempDir))
        try:
            cfg = CONFIG.languages[lang]
            tempFile = os.path.join(tempDir, cfg.file)
            with open(tempFile, 'w', encoding='utf-8') as f:
                f.write(code)
            print('[%s] write file: %s' % (lang, tempFile))
            # execute:
            cmd = 'timeout %s %s' % (CONFIG.timeout, cfg.command)
            if 'docker' in CONFIG:
                img = cfg.image
                cmd = CONFIG.docker % (tempDir, img, cmd)
            print('[%s] command: %s' % (lang, cmd))
            result = run(cmd, tempDir, int(CONFIG.timeout))
        finally:
            shutil.rmtree(tempDir)
            print('[%s] remove temp dir: %s' % (lang, tempDir))
            print('[%s] executed in %s.' % (lang, time.time() - start))
        self.sendResponse(result)

    def responseError(self, errorCode, body=None):
        self.close_connection = True
        self.send_response(errorCode)
        if body:
            data = self.toJsonBytes(body)
            self.send_header('Content-Type')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    def sendResponse(self, body, contentType='application/json'):
        data = self.toJsonBytes(body)
        self.close_connection = True
        self.send_response(200)
        self.send_header('Content-Type', contentType)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def toJsonBytes(self, data):
        if isinstance(data, bytes):
            return data
        elif isinstance(data, str):
            return data.encode('utf-8')
        else:
            return json.dumps(data).encode('utf-8')

    def createTempDir(self):
        dirName = str(nextId())
        fp = os.path.join(CONFIG.tempdir, dirName)
        os.mkdir(fp)
        return fp

    def writeTempFile(self, path, content):
        with open(os.path.join(path, filename), 'w', encoding='utf-8') as f:
            f.write(content)

def main():
    print('Prepare temporary dir %s for code runner...' % CONFIG.tempdir)
    if not os.path.isdir(CONFIG.tempdir):
        os.makedirs(CONFIG.tempdir)
    httpd = ThreadingHTTPServer((CONFIG.ip, int(CONFIG.port)), RunnerHTTPRequestHandler)
    print('Ready for code runner on %s:%s...' % (CONFIG.ip, CONFIG.port))
    print('Press Ctrl + C to exit...')
    httpd.serve_forever()

if __name__ == '__main__':
    main()
