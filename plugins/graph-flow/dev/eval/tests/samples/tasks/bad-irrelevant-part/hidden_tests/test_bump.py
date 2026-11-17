import unittest
from mathkit import bump

class Hidden(unittest.TestCase):
    def test_behavior(self): self.assertEqual(bump(2), 3)
