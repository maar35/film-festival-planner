import csv
import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from FilmRatings.tools import initialize_load_log, add_load_log, add_base_context, get_load_log
from festivals.models import Festival, current_festival
from film_list.models import Film, FilmFan, FilmFanFilmRating
from loader.forms.loader_forms import Loader


# View to start loading ratings of a specific festival.
@login_required
def load_festival_ratings(request):

    # Construct the context.
    title = 'Load Ratings'
    festivals = Festival.festivals.order_by('-start_date')
    submit_name_prefix = 'festival_'
    festival_data = [{
        'str': festival,
        'submit_name': f'{submit_name_prefix}{festival.id}',
        'color': festival.festival_color,
        'film_count_on_file': film_count_on_file(festival),
        'film_count': Film.films.filter(festival=festival).count,
        'rating_count_on_file': rating_count_on_file(festival),
        'rating_count': FilmFanFilmRating.fan_ratings.filter(film__festival=festival).count,
    } for festival in festivals]
    context = add_base_context(request, {
        'title': title,
        'festivals': festival_data,
    })

    # Check the request.
    if request.method == 'POST':
        festival_indicator = None
        names = [f'{submit_name_prefix}{festival.id}' for festival in festivals]
        for name in names:
            if name in request.POST:
                festival_indicator = name
                break
        form = Loader(request.POST)
        if form.is_valid():
            if festival_indicator is not None:
                keep_ratings = form.cleaned_data['keep_ratings']
                festival_id = int(festival_indicator.strip(submit_name_prefix))
                festival = Festival.festivals.get(pk=festival_id)
                festival.set_current(request.session)
                load_rating_data(request.session, festival, keep_ratings)
                return HttpResponseRedirect(reverse('film_list:film_list'))
            else:
                print(f"{title}: can't identify submit widget.")
        else:
            print(f'{title}: form not valid.')
    else:
        form = Loader(initial={'festival': current_festival(request.session).id})

    context['form'] = form
    return render(request, 'loader/ratings.html', context)


def load_rating_data(session, festival, keep_ratings):
    initialize_load_log(session)
    if FilmLoader(session, festival, keep_ratings).load_films():
        RatingLoader(session, festival, keep_ratings).load_ratings()


class BaseLoader:
    """
    Base class for loading objects such as films or ratings from CSV files.
    """
    expected_header = None

    def __init__(self, session, festival, file_required=True):
        """
        Initialize the member variables
        :param session: Session to store the log as a cookie
        :param festival: Film Festival to allow derived classes to filter data
        """
        self.session = session
        self.festival = festival
        self.file_required = file_required
        self.object_name = None
        self.objects_on_file = None

    def read_objects(self, objects_file, object_list):
        """
        Member method to be used by derived classes to read objects from files
        :param objects_file: The CSV file to read the objects form
        :param object_list: A list to receive the objects read
        :return: Whether reading objects was successful
        """
        # Initialize.
        self.objects_on_file = 0

        # Read the objects form the file.
        self.add_log(f'Reading from file {objects_file}.')
        try:
            with open(objects_file, newline='') as csvfile:
                object_reader = csv.reader(csvfile, delimiter=';', quotechar='"')

                # Read the header.
                if not self.check_header(objects_file, object_reader):
                    return False

                # Read the data rows.
                for row in object_reader:
                    self.objects_on_file += 1
                    object_read = self.read_row(row)
                    if object_read is not None:
                        object_list.append(object_read)

        except FileNotFoundError:
            if self.file_required:
                self.add_log(f'File {objects_file} not found.')
            return False

        except ValueError:
            self.add_log(f'Bad value in file {objects_file}.')
            return False

        return True

    def check_header(self, file, reader):
        header = reader.__next__()
        if header != self.expected_header:
            self.add_log(f'File {file} has an incompatible header.')
            return False
        return True

    def read_row(self, row):
        """
        "Virtual" method to read one object from file
        :param row: Line from the file being read
        :return: The object read, None if no object could be read
        """
        return None

    def delete_objects(self, objects):
        deleted_object_count, deleted_count_by_object_type = objects.delete()
        if deleted_object_count == 0:
            self.add_log(f'No existing {self.object_name}s need to be deleted.')
        for (object_type, deleted_count) in deleted_count_by_object_type.items():
            self.add_log(f'{deleted_count} existing {object_type.split(".")[-1]}s deleted.')

    def add_log(self, text):
        add_load_log(self.session, text)


class FilmLoader(BaseLoader):
    expected_header = ['seqnr', 'filmid', 'sort', 'title', 'titlelanguage', 'section', 'duration', 'mediumcategory', 'url']

    def __init__(self, session, festival, keep_ratings):
        super().__init__(session, festival)
        self.keep_ratings = keep_ratings
        self.object_name = 'film'
        self.films = None

    def load_films(self):
        # Read the films of the given festival.
        if not self.read_films():
            return False

        # Save ratings if the Keep Ratings flag is set.
        if self.keep_ratings:
            if not self.save_ratings():
                return False

        # Delete existing films of the given festival.
        existing_films = Film.films.filter(festival_id=self.festival.id)
        self.delete_objects(existing_films)

        # Load the new films.
        Film.films.bulk_create(self.films)
        self.add_log(f'{len(self.films)} films loaded.')

        return True

    def read_films(self):
        # Initialize.
        films_file = self.festival.films_file
        self.films = []

        # Read films from file.
        if not self.read_objects(films_file, self.films):
            return False

        # Add result statistics to the log.
        films_count = len(self.films)
        if films_count == 0:
            self.add_log(f'No films found in file{films_file}')
            return False
        self.add_log(f'{films_count} films read.')
        return True

    def read_row(self, row):
        seq_nr = int(row[0])
        film_id = int(row[1])
        film = Film(festival=self.festival, film_id=film_id, seq_nr=seq_nr)
        film.sort_title = row[2]
        film.title = row[3]
        film.title_language = row[4]
        film.section = row[5]
        film.duration = datetime.timedelta(minutes=int(row[6].rstrip("′")))
        film.medium_category = row[7]
        film.url = row[8]
        return film

    def save_ratings(self):
        festival = self.festival
        ratings = FilmFanFilmRating.fan_ratings.filter(film__festival_id=festival.id)

        try:
            with open(festival.ratings_cache, 'w', newline='') as csvfile:
                rating_writer = csv.writer(csvfile, delimiter=';', quotechar='"')
                rating_writer.writerow(RatingLoader.expected_header)
                for rating in ratings:
                    row = [rating.film.film_id, rating.film_fan.name, rating.rating]
                    rating_writer.writerow(row)
        except FileNotFoundError:
            self.add_log(f'Cache file {festival.ratings_cache} not found.')
            return False
        else:
            self.add_log(f'{len(ratings)} existing ratings saved.')

        return True


class RatingLoader(BaseLoader):
    expected_header = ['filmid', 'filmfan', 'rating']

    def __init__(self, session, festival, keep_ratings):
        super().__init__(session, festival, file_required=False)
        self.keep_ratings = keep_ratings
        self.object_name = 'rating'
        self.ratings_file = self.festival.ratings_file
        self.ratings_cache = self.festival.ratings_cache
        self.ratings = None

    def load_ratings(self):
        # Read the ratings.
        if not self.read_ratings():
            return

        # Delete existing ratings.
        existing_ratings = FilmFanFilmRating.fan_ratings.filter(film__festival_id=self.festival.id)
        self.delete_objects(existing_ratings)

        # Load the new ratings.
        FilmFanFilmRating.fan_ratings.bulk_create(self.ratings)
        self.add_log(f'{len(self.ratings)} ratings loaded.')

    def read_ratings(self):
        # Initialize.
        ratings_file = self.ratings_cache if self.keep_ratings else self.ratings_file
        self.ratings = []

        # Read the ratings from file.
        if not self.read_objects(ratings_file, self.ratings):
            self.add_log('No ratings read.')
            return False

        # Log results
        self.add_log(f'{self.objects_on_file} ratings read, {len(self.ratings)} accepted.')
        return True

    def read_row(self, row):
        film_id = int(row[0])
        film_fan_name = row[1]
        rating_value = int(row[2])
        try:
            film = Film.films.get(festival_id=self.festival.id, film_id=film_id)
        except Film.DoesNotExist:
            self.add_log(f'Film not found: #{film_id}.')
            return None
        try:
            film_fan = FilmFan.film_fans.get(name=film_fan_name)
        except FilmFan.DoesNotExist:
            self.add_log(f'Fan not found: {film_fan_name}.')
            return None
        rating = FilmFanFilmRating(film=film, film_fan=film_fan)
        rating.rating = rating_value
        return rating


def film_count_on_file(festival):
    try:
        with open(festival.films_file, newline='') as films_file:
            film_count = len(films_file.readlines()) - 1    # Exclude header.
    except FileNotFoundError:
        film_count = 0
    return film_count


def rating_count_on_file(festival):
    try:
        with open(festival.ratings_file, newline='') as ratings_file:
            rating_count = len(ratings_file.readlines()) - 1    # Exclude header.
    except FileNotFoundError:
        rating_count = 0
    return rating_count
