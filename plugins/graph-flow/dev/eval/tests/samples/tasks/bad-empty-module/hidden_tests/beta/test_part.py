import unittest
from mathkit import negate

class Hidden(unittest.TestCase):
    def test_behavior(self): self.assertEqual(negate(2), -2)
