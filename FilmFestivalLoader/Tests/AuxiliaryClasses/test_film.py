import datetime

from Shared.planner_interface import Film


class TestFilm(Film):
    def __init__(self, film_id, title, url, minutes, description, festival_data):
        festival_data.film_seqnr += 1
        Film.__init__(self, festival_data.film_seqnr, film_id, title, url)
        self.film_id = film_id
        self.title = title
        self.url = url
        self.duration = datetime.timedelta(minutes=minutes)
        self.description = description
