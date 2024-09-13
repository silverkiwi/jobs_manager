import django
from django.test import TestCase

# Create your tests here.


django.setup()  # Force initialization


class SimpleTest(TestCase):
    def test_basic(self) -> None:
        self.assertTrue(True)
