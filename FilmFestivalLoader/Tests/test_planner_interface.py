import tempfile
import unittest

import Shared.application_tools as application_tools
from Shared.planner_interface import FestivalData, Section


class SectionsTestCase(unittest.TestCase):
    def setUp(self):
        self.city = 'Venezia'
        self.temp_dir = tempfile.TemporaryDirectory()
        self.festival_data = FestivalData(self.city, self.temp_dir.name, self.temp_dir.name)
        self.festival_data.write_verbose = False

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sections_do_not_need_to_be_present(self):
        # Arrange.
        data = self.festival_data

        # Act.
        self.festival_data.read_sections()

        # Assert.
        self.assertEqual(len(data.section_by_name), 0)

    def test_subsections_do_not_need_to_be_present(self):
        # Arrange.
        data = self.festival_data

        # Act.
        data.read_subsections()

        # Assert.
        self.assertEqual(len(data.subsection_by_name), 0)

    def test_sections_can_be_read(self):
        # Arrange.
        data = self.festival_data
        section_1 = Section(1, 'Mainstream', 'blue')
        section_2 = Section(2, 'Arti Farti', 'dark_grey')
        data.section_by_id[section_1.section_id] = section_1
        data.section_by_id[section_2.section_id] = section_2
        data.write_sections()
        data.section_by_id = {}

        # Act.
        data.read_sections()

        # Assert.
        self.assertEqual(len(data.section_by_name), 2)


class ScreensTestCase(unittest.TestCase):
    def setUp(self):
        application_tools.SUPPRESS_INFO_PRINTS = True
        self.city = 'Amsterdam'
        self.temp_dir = tempfile.TemporaryDirectory()
        self.festival_data = FestivalData(self.city, self.temp_dir.name, self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_screens_can_be_read(self):
        # Arrange.
        data = self.festival_data
        theater_name = 'Kriterion'
        screen_1 = data.get_screen(self.city, 'Kriterion Grote Zaal', theater_name)
        screen_2 = data.get_screen(self.city, 'Kriterion Kleine Zaal', theater_name)
        screen_1.abbr = 'krgr'
        screen_2.abbr = 'krkl'
        data.write_new_screens()

        # Act.
        data.read_screens()

        # Assert.
        self.assertEqual(len(data.screen_by_location), 2)
        self.assertEqual(len(data.theater_by_location), 1)


if __name__ == '__main__':
    unittest.main()
