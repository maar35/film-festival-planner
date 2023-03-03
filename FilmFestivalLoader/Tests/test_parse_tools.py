import unittest
from tempfile import TemporaryFile

from Shared.application_tools import DebugRecorder
from Shared.parse_tools import BaseHtmlPageParser


class StateStackTestCase(unittest.TestCase):
    def setUp(self):
        self.debug_file = TemporaryFile()
        self.debugger = DebugRecorder(self.debug_file)
        self.parser = BaseHtmlPageParser(self.debugger, 'TEST')
        self.print_debug = self.parser.print_debug

    def tearDown(self):
        self.debug_file.close()

    def arrange_get_state_stack(self, initial_state):
        return self.parser.StateStack(self.print_debug, initial_state)

    def test_state_stack_push(self):
        # Arrange.
        state_stack = self.arrange_get_state_stack('waiting')

        # Act.
        state_stack.push('found it')

        # Assert.
        self.assertEqual(state_stack.state_is('found it'), True)

    def test_state_stack_pop_from_initial_state(self):
        # Arrange.
        state_stack = self.arrange_get_state_stack('none')

        # Act & Assert.
        with self.assertRaises(IndexError):
            state_stack.pop()

    def test_state_stack_change(self):
        # Arrange.
        state_stack = self.arrange_get_state_stack(0)

        # Act.
        state_stack.change('eating')

        # Assert.
        self.assertEqual(state_stack.state_is('eating'), True)

    def test_state_stack_combination(self):
        # Arrange.
        state_stack = self.arrange_get_state_stack('0')

        # Act.
        state_stack.push('1')
        state_stack.push('2')
        state_stack.change('b')
        state_stack.push('3')
        state_stack.change('c')
        state_stack.pop()

        # Assert.
        self.assertEqual(state_stack.state_is('b'), True)


if __name__ == '__main__':
    unittest.main()
