import unittest
from mathkit import bump

class Visible(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(bump(0), 0)
