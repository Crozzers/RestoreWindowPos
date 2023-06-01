import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable


@dataclass(slots=True)
class ServiceCallback():
    default: Callable
    shutdown: Callable = None


class Service(ABC):
    def __init__(self, callback: ServiceCallback, lock=None):
        self.log = logging.getLogger(__name__).getChild(
            self.__class__.__name__).getChild(str(id(self)))
        self._callback = callback
        self._lock = lock or threading.RLock()
        self._kill_signal = threading.Event()
        self._thread = None

    def start(self, args=None):
        args = args or ()
        if self._thread is None:
            self._thread = threading.Thread(
                target=self._runner, args=args, daemon=True)

        self._thread.start()
        self.log.info('started thread')

    def stop(self, timeout=10):
        self.log.info('send kill signal')
        self._kill_signal.set()

        start = time.time()
        while self._thread.is_alive():
            time.sleep(0.5)
            if timeout is None:
                continue

            if (duration := time.time() - start) > timeout:
                self.log.info(f'kill signal timeout after {duration}s')
                return False

        self.log.info('thread exited')
        return True

    def shutdown(self):
        def func():
            self._kill_signal.set()
            self._run_callback('shutdown')

        threading.Thread(target=func).start()

    @abstractmethod
    def _runner(self):
        pass

    def pre_callback(self, *args, **kwargs) -> bool:
        self.log.debug('run pre_callback')

    def callback(self, *args, **kwargs):
        with self._lock:
            if self.pre_callback(*args, **kwargs):
                try:
                    self.log.info('run callback')
                    self._run_callback('default')
                except Exception:
                    self.log.exception('callback failed')
                    return False
            else:
                self.log.info('pre_callback returned False, skipping callback')
            self.post_callback(*args, **kwargs)

        return True

    def post_callback(self, *args, **kwargs):
        self.log.debug('run post_callback')

    def _run_callback(self, name, *args, threaded=False, **kwargs):
        if self._callback is None:
            return
        func = getattr(self._callback, name, None)
        if not callable(func):
            return

        if threaded:
            threading.Thread(target=func, args=args,
                             kwargs=kwargs, daemon=True).start()
        else:
            func(*args, **kwargs)
