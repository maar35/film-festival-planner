import inspect
from datetime import datetime


def caller():
    frame = inspect.currentframe().f_back
    return frame.f_code.co_name if frame.f_code is not None else 'code'


def debug(frame=inspect.currentframe().f_back):
    lineno = frame.f_lineno
    code = frame.f_code.co_name if frame.f_code is not None else 'code'
    return f'@@ {code}:{lineno:4}'


def pr_debug(message, with_time=False):
    if with_time:
        message = f'{datetime.now():%Y-%m-%d %H:%M:%S.%f}  {message}'
    print(f'{debug(frame=inspect.currentframe().f_back)} {message}')
