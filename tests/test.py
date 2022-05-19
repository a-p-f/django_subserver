import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')
django.setup()

from django import urls
from django.http import Http404, HttpResponse
from django.test import Client
from django import urls
import django_subserver as dss
import unittest

def home_page(request):
    pass

def returning_sub_view(request, **kwargs):
    return (request, kwargs)

url_patterns = [
    urls.path('', home_page),
    urls.path('returning_sub_view', urls.include(dss.sub_view_urls(returning_sub_view))),
]

def simple_subview(sub_request, )


class TestBasic(unittest.TestCase):
    def test_basic(self):
        with self.assertRaises(urls.Resolver404):
            urls.resolve('fakepath')
        self.assertEqual(urls.resolve('').func, home_page)

        match

if __name__ == '__main__':
    unittest.main()
