import inspect
from datetime import datetime

SUPPRESS_DEBUG_PRINT = False


def caller():
    frame = inspect.currentframe().f_back
    return frame.f_code.co_name if frame.f_code is not None else 'code'


def debug(frame=inspect.currentframe().f_back):
    try:
        lineno = frame.f_lineno
        code = frame.f_code.co_name if frame.f_code is not None else 'code'
    finally:
        del frame
    return f'{code}:{lineno:4}'


def pr_debug(message, with_time=False):
    if SUPPRESS_DEBUG_PRINT:
        return
    time_str = f' {datetime.now():%Y-%m-%d %H:%M:%S.%f}' if with_time else ' '
    print(f'@@{time_str} {debug(frame=inspect.currentframe().f_back)} {message}')


class ExceptionTracer:
    def __init__(self):
        self.errors = []

    def add_error(self, errors):
        def pr_trace():
            try:
                frame_infos = inspect.trace()
                for info in frame_infos:
                    self.errors.append(f'{info.filename} line {info.lineno} in {info.function}')
                    self.errors.extend(info.code_context)
                    skip_line()
            finally:
                del frame_infos

        def skip_line():
            self.errors.append('')

        self.errors.extend(errors)
        skip_line()
        pr_trace()

    def get_errors(self):
        return self.errors
