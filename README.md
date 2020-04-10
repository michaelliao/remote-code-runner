# Remote Code Runner

Remote Code Runner is a simple service for running code on remote server side. Docker is used to execute untrusted code in a sandbox environment.

# Install

Environment:

- Ubuntu Linux 18.04
- Docker 19.x
- Python 3.8

```
$ sudo apt install git docker.io python3.8
```

Get source:

```
$ pwd
/srv
$ sudo git clone https://github.com/michaelliao/remote-code-runner.git
```

Generate all from source:

```
$ cd /srv/remote-code-runner
$ sudo python3.8 generate.py
```

Download required docker images by warm up script (this may take a long time):

```
$ cd /srv/remote-code-runner/bin
$ sudo sh warm-up-docker.sh
```

Start server:

```
$ cd /srv/remote-code-runner/bin
$ sudo start-runner.sh
```

# Usage

Using simple HTTP JSON API:

```
$ curl http://server-ip:8080/run -H 'Content-Type: application/json' -d '{"language":"python","code":"import math\nprint(math.pi)"}'
{"error": false, "timeout": false, "truncated": false, "output": "3.141592653589793\n"}
```

API input:

- language: language name, lowercase: `java`, `python`, `ruby`.
- code: language code as JSON string: `import math\nprint(math.pi)`

API output:

- timeout: boolean, is execution timeout.
- error: boolean, is error output. e.g. compile failed or syntax error.
- truncated: boolean, is output was truncated for too many characters.
- output: string, the output of execution.

# Execution

How code are executed on the remote server side:

1. Http server `runner.py` got language name and code from API;
2. Write code into a temperary directory like `/tmp/remote-code-runner/1`;
3. Execute command like `sudo docker run -t --rm -w /app -v /tmp/dir:/app <image-tag> python3 main.py`;
4. Write output into API response;
5. Clean up temperary directory.

# Limitation

- Multiple files are not supported.
- There is no way to read input from console. Any user input code will cause timeout.

# Security

Remote code runner should only be served in private network. User identity check, rate limit must be done in application server or reverse proxy like Nginx.

# Extension

How to add a new language:

1. Add configuration in `config.json`:

```
{
    ...
    "languages": {
        ...
        "node": {
            "file": "main.js",
            "image": "node:13.12-slim",
            "command": "node main.js"
        }
    }
}
```

The key `node` is the language name.

2. Make sure image is downloaded on local:

```
$ sudo docker run -t --rm node:13.12-slim ls
```

3. Restart `start-runner.sh`.
