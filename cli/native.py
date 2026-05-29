import contextlib
import ctypes
import os
from typing import Optional


_NOOP_LLAMA_LOG_CALLBACK = None


def _llama_cpp_module():
    try:
        import llama_cpp

        return llama_cpp
    except Exception:
        return None


def _install_noop_llama_logger() -> bool:
    global _NOOP_LLAMA_LOG_CALLBACK

    llama_cpp = _llama_cpp_module()
    if llama_cpp is None:
        return False

    setter = getattr(llama_cpp, "llama_log_set", None)
    if setter is None:
        inner = getattr(llama_cpp, "llama_cpp", None)
        setter = getattr(inner, "llama_log_set", None) if inner is not None else None
    if not callable(setter):
        return False

    if _NOOP_LLAMA_LOG_CALLBACK is None:
        callback_type = getattr(llama_cpp, "llama_log_callback", None)

        def _callback(level, text, user_data):
            return None

        try:
            _NOOP_LLAMA_LOG_CALLBACK = callback_type(_callback) if callable(callback_type) else None
        except Exception:
            _NOOP_LLAMA_LOG_CALLBACK = None
        if _NOOP_LLAMA_LOG_CALLBACK is None:
            _NOOP_LLAMA_LOG_CALLBACK = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)(_callback)

    try:
        setter(_NOOP_LLAMA_LOG_CALLBACK, None)
        return True
    except Exception:
        return False


@contextlib.contextmanager
def suppress_native_output():
    if os.environ.get("LIGHTWEIGHT_LLAMA_LOGS") == "1":
        yield
        return

    _install_noop_llama_logger()
    saved_stdout_fd: Optional[int] = None
    saved_stderr_fd: Optional[int] = None
    devnull_fd: Optional[int] = None
    redirected = False
    try:
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        saved_stdout_fd = os.dup(1)
        saved_stderr_fd = os.dup(2)
        os.dup2(devnull_fd, 1)
        os.dup2(devnull_fd, 2)
        redirected = True
    except Exception:
        redirected = False
    try:
        yield
    finally:
        if redirected:
            try:
                if saved_stdout_fd is not None:
                    os.dup2(saved_stdout_fd, 1)
                if saved_stderr_fd is not None:
                    os.dup2(saved_stderr_fd, 2)
            except Exception:
                pass
        for fd in (saved_stdout_fd, saved_stderr_fd, devnull_fd):
            if fd is not None:
                try:
                    os.close(fd)
                except Exception:
                    pass
