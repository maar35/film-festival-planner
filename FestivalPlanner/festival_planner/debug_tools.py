import functools
import inspect
from datetime import datetime, timedelta

from django.views.generic import ListView

SUPPRESS_DEBUG_PRINT = False


def calling_func(frame_depth=0):
    try:
        frame = inspect.currentframe().f_back
        for _ in range(frame_depth):
            frame = frame.f_back
        code = frame.f_code.co_name if frame.f_code else 'code'
    finally:
        del frame
    return code


def debug(frame_depth=0):
    frame = inspect.currentframe().f_back
    for d in range(frame_depth):
        frame = frame.f_back

    try:
        lineno = frame.f_lineno
        code = frame.f_code.co_name if frame.f_code else 'code'
    finally:
        del frame
    return f'{code}:{lineno:4}'


def pr_debug(message, with_time=False, frame_depth=1):
    if SUPPRESS_DEBUG_PRINT:
        return
    time_str = f' {datetime.now():%Y-%m-%d %H:%M:%S.%f}' if with_time else ' '
    print(f'@@{time_str} {debug(frame_depth=frame_depth)} {message}')


def timed_method(func):
    """
    Enclose func between 'start' and 'dane' debug messages.
    Doesn't seem to work because functools.wraps doesn't work (yet?).
    """
    @functools.wraps(func)
    def time_wrapper(*args, **kwargs):
        frame_depth = 4
        pr_debug('START', with_time=True, frame_depth=frame_depth)
        result = func(*args, **kwargs)
        pr_debug('DONE', with_time=True, frame_depth=frame_depth)
        return result
    return time_wrapper


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


class DurationProfiler:
    props_by_label = {}
    objects = []

    def __init__(self, label, active=True, newline=False, caller_depth=0):
        self.label = label
        self.caller_depth = caller_depth
        self.props_by_label[label] = {
            'duration': timedelta(),
            'call_count': 0,
            'active': active,
            'props_by_caller': {},
            'newline': newline,
        }
        self.last_start_time = None
        DurationProfiler.objects.append(self)

    def start(self):
        self.last_start_time = datetime.now()
        self.props_by_label[self.label]['call_count'] += 1

    def done(self):
        last_duration = datetime.now() - self.last_start_time
        self.props_by_label[self.label]['duration'] += last_duration
        if self.caller_depth:
            caller = calling_func(frame_depth=self.caller_depth)
            try:
                self._caller_props(self.label)[caller]['duration'] += last_duration
                self._caller_props(self.label)[caller]['count'] += 1
            except KeyError:
                self._caller_props(self.label)[caller] = {
                    'duration': last_duration,
                    'count': 1,
                }

    @classmethod
    def report(cls):
        durations = [cls._label_report(label) for label in cls.props_by_label if cls.props_by_label[label]['active']]
        cls._reset()
        return durations

    @classmethod
    def _label_report(cls, label):
        duration = cls.props_by_label[label]['duration']
        count = cls.props_by_label[label]['call_count']
        newline = '\n' if cls.props_by_label[label]['newline'] else ''
        report = newline + f'{label:16}: {duration} {count:5}'
        for caller, props in cls._caller_props(label).items():
            caller_line = f"{label:16}from {caller:40}: {props['duration']} {props['count']}"
            report += '\n' + caller_line
        return report

    @classmethod
    def _caller_props(cls, label):
        return cls.props_by_label[label]['props_by_caller']

    @classmethod
    def _reset(cls):
        for obj in cls.objects:
            cls.props_by_label[obj.label]['duration'] = timedelta()
            cls.props_by_label[obj.label]['call_count'] = 0
            cls.props_by_label[obj.label]['props_by_caller'] = {}


SETUP_PROFILER = DurationProfiler('setup')
QUERY_PROFILER = DurationProfiler('queryset')
GET_CONTEXT_PROFILER = DurationProfiler('context', active=True)

SET_TICKET_STATUS_PROFILER = DurationProfiler('set_ticket_stat', active=False, newline=True, caller_depth=4)

SCREENING_DICT_PROFILER = DurationProfiler('screening_dict', newline=True, active=False)
FRAGMENT_PROFILER = DurationProfiler('fragment', active=False)

SCREEN_ROW_PROFILER = DurationProfiler('screen_row', active=False, newline=True, caller_depth=0)
SCREENING_WARNINGS_PROFILER = DurationProfiler('screening_warns', active=False)
FAN_ATTENDS_PROFILER = DurationProfiler('fan_attends', active=False)
ATTENDANTS_PROFILER = DurationProfiler('get_attendants', active=False)
SCREENING_STATUS_PROFILER = DurationProfiler('screening_status', active=False)
RATING_DATA_PROFILER = DurationProfiler('rating_data', active=False)
FAN_PROPS_PROFILER = DurationProfiler('fan_props', active=False)
TICKET_STATUS_PROFILER = DurationProfiler('ticket_status', active=False, caller_depth=3)

MULTI_ATTENDS_PROFILER = DurationProfiler('multi_attends', active=False, newline=True)
OVERLAP_PROFILER = DurationProfiler('overlap', active=True, caller_depth=3)
GET_AVAILABILITY_PROFILER = DurationProfiler('get_availability', active=False)
UNAVAILABLE_PROFILER = DurationProfiler('available', active=False)

SELECTED_PROPS_PROFILER = DurationProfiler('selected_props', active=False, newline=True, caller_depth=0)
FAN_RATING_PROFILER = DurationProfiler('fan_rating', active=False, caller_depth=0)
FILMSCREENINGS_PROFILER = DurationProfiler('filmscreenings', active=False, caller_depth=0)

GET_WARNINGS_PROFILER = DurationProfiler('get_warnings', newline=True, caller_depth=0)
WARNING_KEYS_PROFILER = DurationProfiler('warning_keys')
GET_AV_KEEPER_PROFILER = DurationProfiler('get_av_keeper')
FAN_WARNINGS_PROFILER = DurationProfiler('fan_warnings', caller_depth=2)

LISTVIEW_DISPATCH_PROFILER = DurationProfiler('list_dispatch', newline=True, caller_depth=3)


def profiled_method(duration_profiler: DurationProfiler):
    """Bookkeep duration of given duration profiles"""
    def decorator_profiled_method(func):
        @functools.wraps(func)
        def duration_wrapper(*args, **kwargs):
            duration_profiler.start()
            result = func(*args, **kwargs)
            duration_profiler.done()
            return result
        return duration_wrapper

    return decorator_profiled_method


class ProfiledListView(ListView):

    def render_to_response(self, context, **response_kwargs):
        """Defined here for debugging only"""
        response = super().render_to_response(context, **response_kwargs)
        if not SUPPRESS_DEBUG_PRINT:
            print(f'{"\n".join(DurationProfiler.report())}')
        return response
