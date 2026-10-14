"""Select Actions checks. Unknown history or paths always run the full gate."""
import json
from fnmatch import fnmatchcase
import os
from pathlib import PurePosixPath
import re
import subprocess


# These paths are reviewed for this repository only. fnmatch * also crosses /.
DOC_PATHS = ()
SKIP_PATHS = ('README.md', 'CONTRIBUTING.md', 'CODE_OF_CONDUCT.md')

def classify(paths):
    if not paths:
        return 'none'
    docs = False
    for path in paths:
        name = PurePosixPath(path)
        if (name.is_absolute() or any(p in ('', '.', '..') for p in path.split('/'))):
            return 'full'
        if any(fnmatchcase(path, pattern) for pattern in SKIP_PATHS):
            continue
        if any(fnmatchcase(path, pattern) for pattern in DOC_PATHS):
            docs = True
            continue
        return 'full'
    return 'docs' if docs else 'none'


def mode(event, kind, successful_base='', attempt='1'):
    if attempt != '1':
        return 'full'
    if kind == 'pull_request':
        base = event.get('pull_request', {}).get('base', {}).get('sha', '')
    elif kind == 'push':
        # Never use push.before: it may contain code whose verify failed.
        base = successful_base
    else:
        return 'full'
    if not isinstance(base, str) or not re.fullmatch(r'[0-9a-f]{40}', base) or base == '0' * 40:
        return 'full'
    try:
        raw = subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', 'diff',
            '--raw', '-z', '--abbrev=40', '--no-renames', '--no-ext-diff', '--no-textconv',
            base, 'HEAD', '--'], stderr=subprocess.DEVNULL)
        fields = raw.split(b'\0')
        if fields[-1] != b'' or len(fields) % 2 != 1 or len(fields) > 20001:
            return 'full'
        paths = []
        for header, path in zip(fields[:-1:2], fields[1:-1:2]):
            match = re.fullmatch(rb':(\d{6}) (\d{6}) [0-9a-f]{40} [0-9a-f]{40} [ADMT]', header)
            if not match or not path or any(m not in (b'000000', b'100644') for m in match.groups()):
                return 'full'
            paths.append(path.decode('utf8'))
        return classify(paths)
    except (OSError, ValueError, subprocess.CalledProcessError):
        return 'full'


if __name__ == '__main__':
    try:
        with open(os.environ['GITHUB_EVENT_PATH']) as stream:
            event = json.load(stream)
        selected = mode(event, os.environ['GITHUB_EVENT_NAME'],
                        os.environ.get('CI_SUCCESSFUL_BASE_SHA', ''),
                        os.environ.get('GITHUB_RUN_ATTEMPT', '1'))
    except (OSError, KeyError, ValueError, TypeError):
        selected = 'full'
    print('mode=' + selected)
