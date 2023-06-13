from datetime import date

from django.test import TestCase
from django.urls import reverse

from festivals.models import Festival, FestivalBase
from theaters.models import City


def create_festival(mnemonic, city, start_date_str, end_date_str, edition=None):
    """
    Create a festival with the given arguments in the database.
    """
    base = FestivalBase.festival_bases.create(
        name='The Good Festival', mnemonic=mnemonic, home_city=city
    )
    start_date = date.fromisoformat(f'{start_date_str}')
    end_date = date.fromisoformat(f'{end_date_str}')
    year = start_date.year
    festival_color = 'turquoise'
    return Festival.festivals.create(
        base=base, year=year, start_date=start_date, end_date=end_date,
        festival_color=festival_color, edition=edition
    )


def mock_base_festival_mnemonic():
    return 'Berlinale'


class FestivalModelTests(TestCase):

    def setUp(self):
        super(FestivalModelTests, self).setUp()
        self.city = City.cities.create(city_id=1, name='Berlin', country='de')

    def tearDown(self):
        super(FestivalModelTests, self).tearDown()
        self.city.delete()

    def create_festival(self, mnemonic, start_date_str, end_date_str):
        return create_festival(mnemonic, self.city, start_date_str, end_date_str)

    def test_number_of_festivals_migrated(self):
        """
        All festivals have been created with admin, so zero have been
        migrated.
        """
        festival_count = Festival.festivals.count()
        self.assertEqual(festival_count, 0)

    def test_festival_sorting(self):
        """
        Three festivals are displayed on the index page, reversed
        chronologically.
        """
        festival_1 = self.create_festival('IFFR', '2021-01-27', '2021-02-06')
        festival_2 = self.create_festival('IDFA', '2025-07-17', '2022-07-27')
        festival_3 = self.create_festival('MTMF', '2020-04-12', '2022-07-27')
        response = self.client.get(reverse('festivals:index'))
        self.assertQuerysetEqual(
            response.context['festival_rows'],
            [festival_2, festival_1, festival_3],
        )
