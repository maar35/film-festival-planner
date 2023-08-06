import inspect
import re
from os import path

from festivals.models import current_festival

from films.models import current_fan, get_user_fan

RE_APP_NAME = re.compile(r'([a-z])([A-Z])')
REPL_APP_NAME = r'\1 \2'


def application_name():
    base_name = path.basename(path.dirname(path.dirname(__file__)))
    name = RE_APP_NAME.sub(REPL_APP_NAME, base_name)
    return name


def caller():
    frame = inspect.currentframe().f_back
    return frame.f_code.co_name if frame.f_code is not None else 'code'


def initialize_log(session, action='Load'):
    """
    Initialize log cookie.
    """
    session['log'] = {'results': [], 'action': action}


def add_log(session, text):
    """
    Add text to the results of the log cookie.
    """
    session['log']['results'].append(text)


def get_log(session):
    """
    Get the log cookie.
    """
    return session.get('log')


def unset_log(session):
    """
    Unset the log cookie.
    """
    session['log'] = None


def wrap_up_form_errors(form_errors):
    """
    Support printing form errors.
    """
    messages = ['Form is invalid']
    for subject, errors in form_errors.items():
        messages.append(f'{subject}: {",".join([error for error in errors])}')
    return messages


# Define common parameters for the base template.
def user_is_admin(request):
    user_fan = get_user_fan(request.user)
    if user_fan is None:
        return False
    return user_fan.is_admin


def user_represents_fan(request, fan):
    if fan is None:
        return False
    user_fan = get_user_fan(request.user)
    if user_fan is None:
        return False
    return fan != user_fan and user_fan.is_admin


def add_base_context(request, param_dict):
    festival = current_festival(request.session)
    festival_color = festival.festival_color if festival is not None else None
    background_image = festival.base.image if festival is not None else None
    fan = current_fan(request.session)

    base_param_dict = {
        'app_name': application_name(),
        'festival_color': festival_color,
        'background_image': background_image,
        'festival': festival,
        'current_fan': fan,
        'user_is_admin': user_is_admin(request),
        'user_represents_fan': user_represents_fan(request, fan),
    }
    return {**base_param_dict, **param_dict}
