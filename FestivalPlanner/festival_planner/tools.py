from festivals.models import current_festival


# Support log cookie.
from films.models import current_fan, get_user_fan


def initialize_log(session, action='Load'):
    session['log'] = {'results': [], 'action': action}


def add_log(session, text):
    session['log']['results'].append(text)


def get_log(session):
    return session.get('log')


def unset_log(session):
    session['log'] = None


# Support printing form errors.
def wrap_up_form_errors(form_errors):
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
        'festival_color': festival_color,
        'background_image': background_image,
        'festival': festival,
        'current_fan': fan,
        'user_is_admin': user_is_admin(request),
        'user_represents_fan': user_represents_fan(request, fan),
    }
    return {**base_param_dict, **param_dict}
