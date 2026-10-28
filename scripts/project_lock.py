"""Cooperative dossier single-writer lock and state CAS (not a multi-file transaction)."""
from contextlib import contextmanager
from functools import wraps
import fcntl
import json
import os
from pathlib import Path
import threading

_local = threading.local()

@contextmanager
def project_lock(path):
    path = Path(path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    target = path / '.workflow.lock'
    if target.is_symlink():
        raise ValueError('Workflow lock must not be a symlink')
    held = getattr(_local, 'held', {}) if getattr(_local, 'pid', None)==os.getpid() else {}
    _local.pid = os.getpid()
    _local.held = held
    key = str(target)
    if key in held:
        yield
        return
    fd = os.open(target, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another workflow writer holds the dossier lock') from None
        held[key] = fd
        yield
    finally:
        held.pop(key, None)
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    # Never unlink: another process can already hold an fd for this inode.

def state_cas(path, state):
    if json.loads((Path(path) / 'state.json').read_text()) != state:
        raise ValueError('Workflow state CAS failed; reload current state')

def locked_gate(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        # prepare/verify(root,path,state,...), dispatch/recover(path,state,...)
        offset = 1 if function.__name__ in ('prepare', 'verify') else 0
        path = args[offset] if len(args) > offset else kwargs['path']
        state = args[offset+1] if len(args) > offset+1 else kwargs['state']
        with project_lock(path):
            state_cas(path, state)
            return function(*args, **kwargs)
    return wrapped
