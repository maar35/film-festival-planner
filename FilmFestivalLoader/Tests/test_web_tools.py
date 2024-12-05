import unittest

from Shared.web_tools import paths_eq


class UrlsPathsTestCase(unittest.TestCase):
    def test_paths_eq_full_url_vs_path(self):
        """
        Function paths_eq() compares a full url equal against its path part.
        """
        # Arrange.
        url_1 = 'https://iffr.com/nl/iffr/2025/events/vpro-reviewdag-2025'
        url_2 = '/nl/iffr/2025/events/vpro-reviewdag-2025'

        # Act.
        equivalent = paths_eq(url_1, url_2)

        # Assert.
        self.assertEqual(equivalent, True, 'Full url and its path part should evaluate equivalent')

    def test_paths_eq_iri_vs_uri(self):
        """
        Function paths_eq() compares an iri and an equivalent uri as equivalent.
        """
        # Arrange.
        iri = 'https://iffr.com/nl/iffr/2025/films/la-guitarra-flamenca-de-yerai-cortés'
        uri = 'https://iffr.com/nl/iffr/2025/films/la-guitarra-flamenca-de-yerai-cort%c3%a9s'

        # Act.
        equivalent = paths_eq(iri, uri)

        # Assert.
        self.assertEqual(equivalent, True, 'Iri and derived uri should evaluate equivalent')


if __name__ == '__main__':
    unittest.main()
