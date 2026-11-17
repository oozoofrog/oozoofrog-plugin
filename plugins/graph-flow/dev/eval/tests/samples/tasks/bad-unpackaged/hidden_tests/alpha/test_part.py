import unittest
from mathkit import twice

class Hidden(unittest.TestCase):
    def test_behavior(self): self.assertEqual(twice(2), 4)
