import unittest
from mathkit import bump

class Hidden(unittest.TestCase):
    def test_two(self):
        self.assertEqual(bump(2), 3)

    def test_seven(self):
        self.assertEqual(bump(7), 8)
