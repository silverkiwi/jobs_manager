from django.test import TestCase

# Create your tests here.

import django

django.setup()  # Force initialization


class SimpleTest(TestCase):
    def test_basic(self):
        self.assertTrue(True)
