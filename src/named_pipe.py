import logging
import struct
import time
from enum import StrEnum
from typing import cast

import pywintypes
import win32file
import win32pipe
from services import Service

log = logging.getLogger(__name__)
PIPE = r'\\.\pipe\RestoreWindowPos'


class Messages(StrEnum):
    ACK = 'ack_'
    PING = 'ping'
    GUI = 'open_gui'


class PipeServer(Service):
    '''Service that creates and listens on a named PIPE and responds to messages'''

    def _runner(self):
        self.log.debug('starting pipe sever')
        # https://stackoverflow.com/questions/48542644/python-and-windows-named-pipes
        # https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createnamedpipea
        pipe = win32pipe.CreateNamedPipe(
            PIPE,
            win32pipe.PIPE_ACCESS_DUPLEX,
            win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
            1,  # max instances
            65536,  # out buffer size
            65536,  # in buffer size
            0,  # default timeout
            None,  # security attrs
        )
        self.log.debug(f'created pipe {PIPE!r}')

        while not self._kill_signal.wait(timeout=0.1):
            for _ in range(10):
                try:
                    win32pipe.ConnectNamedPipe(pipe, None)
                    break
                except Exception as e:
                    self.log.error(f'pipe connection failed: {e!r}')
                    time.sleep(1)
            else:
                continue

            self.log.info('pipe connected. Reading data...')

            try:
                message = readpipe(pipe)
            except pywintypes.error as e:
                if e.args[0] == 109:
                    self.log.info('broken pipe')
                else:
                    self.log.error(f'failed to read pipe: {e!r}')

                win32pipe.DisconnectNamedPipe(pipe)
                time.sleep(1)
                continue

            try:
                Messages(message)
            except Exception:
                self.log.debug(f'received and ignored message: {message[:128]!r}')
            else:
                if message == Messages.GUI:
                    self.log.debug('GUI requested via pipe')
                    self.callback(message)

                self.log.info(f'received message {message!r} and sent acknowledgement')
                writepipe(pipe, Messages.ACK + message)

        win32file.CloseHandle(pipe)
        self.log.info('pipe closed')


def readpipe(handle: int) -> str:
    '''Read data from a named pipe and return the decoded value'''
    msg_len = struct.unpack('I', win32file.ReadFile(handle, 4)[1])[0]
    return win32file.ReadFile(handle, msg_len)[1].decode()


def writepipe(handle: int, message: Messages | str):
    '''Write data to a named pipe'''
    # write data len so that `readpipe` knows how much to read
    data = struct.pack('I', len(message))
    win32file.WriteFile(handle, data)
    win32file.WriteFile(handle, message.encode())


def send_message(message: Messages):
    '''Sends a message on the named pipe and checks that the correct acknowledgment is received'''
    try:
        log.info(f'attempt to send {message!r} on pipe {PIPE!r}')
        # make sure we wait for it to be available
        win32pipe.WaitNamedPipe(PIPE, 2000)
        handle = win32file.CreateFile(
            PIPE, win32file.GENERIC_READ | win32file.GENERIC_WRITE, 0, None, win32file.OPEN_EXISTING, 0, None
        )
        # handle here is pyhandle. Consumer functions have `int` as the type hint. That is incorrect and can be ignored
        handle = cast(int, handle)
    except pywintypes.error as e:
        log.error(f'failed to connect to pipe: {e!r}')
        return False

    try:
        win32pipe.SetNamedPipeHandleState(handle, win32pipe.PIPE_READMODE_MESSAGE, None, None)
        writepipe(handle, message)
        time.sleep(1)
        response = readpipe(handle)
    except Exception as e:
        log.error(f'failed to write message {message!r} to pipe {PIPE!r}: {e!r}')
    finally:
        win32file.CloseHandle(handle)

    return response == Messages.ACK + message


def is_proc_alive():
    '''Pings the named pipe and listens for a response'''
    return send_message(Messages.PING)
