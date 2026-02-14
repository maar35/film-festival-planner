import copy
from datetime import datetime

from django import forms
from django.core.validators import RegexValidator
from django.db import transaction, IntegrityError
from django.forms import CharField

from authentication.models import FilmFan
from festival_planner.cache import FilmRatingCache
from festival_planner.fan_action import RatingAction
from festival_planner.tools import add_log
from festivals.config import Config
from festivals.models import rating_action_key, current_festival
from films.models import fan_rating_str, FIELD_BY_POST_ATTENDANCE, \
    MANAGER_BY_POST_ATTENDANCE, Film, FilmFanFilmRating, UNRATED_RATING

MEDIUM_CATEGORY_EVENT = Config().config['MediumCategories']['Events']
SEARCH_TEXT_VALIDATOR = RegexValidator(r'^\w+$', 'Type letters and digits only')
"""
No spaces allowed (yet) to discourage entering articles while searching and
sorting is based on sort_title.
"""


def eligible_fans():
    return [(fan.name, fan) for fan in FilmFan.film_fans.order_by('seq_nr')]


class UserForm(forms.Form):
    selected_fan = forms.ChoiceField(
        label='Select a film fan',
        choices=eligible_fans,
    )


class PickRating(forms.Form):
    search_text = CharField(
        label='Find a title by entering a snippet of it',
        required=False,
        validators=[SEARCH_TEXT_VALIDATOR],
        min_length=2,
    )
    film_rating_cache = None
    rating_action_by_field = {key: RatingAction(key) for key in FIELD_BY_POST_ATTENDANCE.values()}

    @classmethod
    def update_rating(cls, session, film, fan, rating_value, post_attendance=False):
        field = FIELD_BY_POST_ATTENDANCE[post_attendance]
        old_rating_str = fan_rating_str(fan, film, post_attendance=post_attendance)
        new_rating = None

        # Account for possible alternative titles. These always include the given film.
        alternative_films = cls.get_alternative_films(film, post_attendance)
        for alt_film in alternative_films:
            new_rating = cls.update_one_rating(session, alt_film, fan, rating_value, post_attendance)

        # Prepare the rating change being displayed.
        init_rating_action(session, old_rating_str, new_rating, field)

    @classmethod
    def update_one_rating(cls, session, film, fan, rating_value, post_attendance=False):
        field = FIELD_BY_POST_ATTENDANCE[post_attendance]
        manager = MANAGER_BY_POST_ATTENDANCE[post_attendance]

        # Remember original rating if applicable.
        org_rating = None
        if not post_attendance:
            rating = FilmFanFilmRating.film_ratings.filter(film=film, film_fan=fan).first()
            org_rating = rating.original_rating if rating else UNRATED_RATING

        # Update the indicated rating.
        upd_kwargs = {
            'film': film,
            'film_fan': fan,
            'defaults': {field: rating_value},
        }
        if not post_attendance:
            upd_kwargs['defaults'] |= {'original_rating': org_rating}
        new_rating, created = manager.update_or_create(**upd_kwargs)

        # Remove zero-ratings (unrated), for post_attendance False, also consider original rating.
        zero_kwargs = {'film': film, 'film_fan': fan, field: UNRATED_RATING}
        if not post_attendance:
            zero_kwargs |= {'original_rating': UNRATED_RATING}
        zero_ratings = manager.filter(**zero_kwargs)
        if zero_ratings.count():
            zero_ratings.delete()

        # Update cache if applicable.
        if not post_attendance and cls.film_rating_cache:
            cls.film_rating_cache.update_festival_caches(session, film, fan, rating_value)

        return new_rating

    @classmethod
    def get_alternative_films(cls, film, post_attendance):
        """Return the given film, plus alternative titles if any, as a list"""
        if post_attendance:
            return [film]

        manager = Film.films
        main_film = film.main_title
        default_film = main_film if main_film else film
        alternative_films = {default_film}
        alternative_films |= set(list(manager.filter(main_title=default_film)))
        return alternative_films

    @classmethod
    def invalidate_festival_caches(cls, session, errors=None):
        errors = errors or []
        if not PickRating.film_rating_cache:
            PickRating.film_rating_cache = FilmRatingCache(session, errors)
        PickRating.film_rating_cache.invalidate_festival_caches(current_festival(session))


class TitlesForm(forms.Form):
    search_text = CharField(
        label='Find a title by entering a snippet of it',
        required=False,
        validators=[SEARCH_TEXT_VALIDATOR],
        min_length=2,
    )

    @classmethod
    def update_alternative_film(cls, session, alternative_title_film_id, main_film):
        # Set the main title of the film with an alternative title.
        film_ = Film.films.filter(id=alternative_title_film_id)
        _ = film_.update(main_title=main_film)

        # Set the ratings of the alt film to those of the main film
        # after saving the original ratings.
        manager = FilmFanFilmRating.film_ratings
        alt_film = film_.first()
        alt_ratings = manager.filter(film_id=alternative_title_film_id)
        if main_film:
            # Alternative title is being linked to main film.
            try:
                with transaction.atomic():
                    cls._link_alt_film_to_main_film(session, alt_film, main_film, alt_ratings)
            except IntegrityError as e:
                handle_exception(session, e, alt_film)
        else:
            # Alternative title is being unlinked from main film.
            try:
                with transaction.atomic():
                    cls._unlink_alt_film(session, alt_film, alt_ratings)
            except IntegrityError as e:
                handle_exception(session, e, alt_ratings)

    @classmethod
    def _link_alt_film_to_main_film(cls, session, alt_film, main_film, alt_ratings):
        # Set the reviewer of the alt film.
        kwargs = {'id': alt_film.id, 'reviewer': None, 'medium_category': MEDIUM_CATEGORY_EVENT}
        Film.films.filter(**kwargs).update(reviewer=main_film.reviewer)

        # Set de ratings of the alt film.
        manager = FilmFanFilmRating.film_ratings
        main_ratings = manager.filter(film=main_film)
        alt_fans = [r.film_fan for r in alt_ratings]
        main_fans = [r.film_fan for r in main_ratings]
        fans = set(alt_fans) | set(main_fans)
        for fan in fans:
            match fan:
                case f if f in alt_fans and f in main_fans:
                    # Fan has rated both films.
                    cls._save_alt_rating(alt_ratings, f)
                    main_rating = main_ratings.get(film_fan=f)
                    _ = PickRating.update_one_rating(session, alt_film, f, main_rating.rating)
                case f if f in alt_fans and f not in main_fans:
                    # Fan has only rated the alternative title.
                    cls._save_alt_rating(alt_ratings, f)
                    _ = PickRating.update_one_rating(session, alt_film, f, UNRATED_RATING)
                case f if f not in alt_fans and f in main_fans:
                    # Fan has only rated the main film.
                    main_rating = main_ratings.get(film_fan=f)
                    _ = PickRating.update_one_rating(session, alt_film, f, main_rating.rating)

    @classmethod
    def _unlink_alt_film(cls, session, alt_film, alt_ratings):
        # Set reviewer of alt film to None.
        alt_film.reviewer = None if alt_film.medium_category == MEDIUM_CATEGORY_EVENT else alt_film.reviewer
        alt_film.save()

        # Save ratings of alt film.
        for alt_rating in alt_ratings:
            rating = alt_rating.original_rating
            alt_rating.original_rating = UNRATED_RATING
            alt_rating.save()
            fan = alt_rating.film_fan
            _ = PickRating.update_one_rating(session, alt_film, fan, rating)

    @classmethod
    def _save_alt_rating(cls, alt_ratings, fan):
        alt_rating = alt_ratings.get(film_fan=fan)
        alt_rating.original_rating = alt_rating.rating
        alt_rating.save()


def handle_exception(session, exception, obj):
    add_log(session, f'"{obj}" not processed.')
    add_log(session, f'Exception: {exception}')
    add_log(session, 'Database rolled back.')
    raise Exception(exception)


def init_rating_action(session, old_rating_str, new_rating, field):
    kwargs = {
        'old_rating_str': old_rating_str,
        'new_rating': new_rating,
        'field': field,
    }
    PickRating.rating_action_by_field[field].init_action(session, **kwargs)


def refreshed_rating_action(session, tag):
    key = rating_action_key(session, tag)
    if key in session:
        action = copy.deepcopy(session[key])
        action['action_time'] = datetime.fromisoformat(action['action_time'])
    else:
        action = None
    return action
