from datetime import date
from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse

from festivals.models import Festival, FestivalBase


def create_festival(mnemonic, start_date_str, end_date_str, edition=None):
    """
    Create a festival with the given arguments in the database.
    """
    base = FestivalBase.festival_bases.create(name='The Good Festival', mnemonic=mnemonic)
    start_date = date.fromisoformat(f'{start_date_str}')
    end_date = date.fromisoformat(f'{end_date_str}')
    year = start_date.year
    festival_color = 'turquoise'
    return Festival.festivals.create(
        base=base, year=year, start_date=start_date, end_date=end_date,
        festival_color=festival_color, edition=edition
    )


def base_festival_mnemonic():
    return 'Berlinale'


class FestivalModelTests(TestCase):

    def test_number_of_festivals_migrated(self):
        """
        All festivals have been created with admin, so zero have been
        migrated.
        """
        festival_count = Festival.festivals.count()
        self.assertEqual(festival_count, 0)

    def test_no_festivals(self):
        """
        If no festival exist, an appropriate message is displayed.
        """
        response = self.client.get(reverse('festivals:index'))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, "No festivals are available.")
        self.assertQuerysetEqual(response.context['festival_list'], [])

    def test_one_festival(self):
        """
        A single festival is displayed on the index page.
        """
        festival = create_festival('IFFR', '2021-01-27', '2021-02-06', 'July')
        response = self.client.get(reverse('festivals:index'))
        self.assertQuerysetEqual(
            response.context['festival_list'],
            [festival],
        )

    def test_two_festivals(self):
        """
        Two festivals are displayed on the index page, most recent
        first.
        """
        festival_1 = create_festival('IFFR', '2021-01-27', '2021-02-06')
        festival_2 = create_festival('IDFA', '2022-07-17', '2022-07-27')
        response = self.client.get(reverse('festivals:index'))
        self.assertQuerysetEqual(
            response.context['festival_list'],
            [festival_2, festival_1],
        )
