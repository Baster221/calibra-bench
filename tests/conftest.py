"""Windows cleanup workaround for genlayer-test 0.29.2; real SDK unchanged."""
import os

if os.name == "nt":
    from gltest.direct import loader
    _inject = loader._inject_message_to_fd0
    _deferred = []

    def _windows_inject(vm):
        try:
            _inject(vm)
        except PermissionError as exc:
            if getattr(exc, "winerror", None) != 32 or vm._original_stdin_fd is None:
                raise
            _deferred.append(exc.filename)

    loader._inject_message_to_fd0 = _windows_inject

def pytest_sessionfinish(session, exitstatus):
    if os.name == "nt":
        for path in _deferred:
            try:
                os.unlink(path)
            except (PermissionError, FileNotFoundError):
                pass
