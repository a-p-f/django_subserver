import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')
django.setup()

from django import urls
from django.http import Http404, HttpResponse, JsonResponse
from django.test import Client, RequestFactory
from django import urls
import django_subserver as dss
import json
import unittest

def home_page(request):
    return HttpResponse('HOME', content_type='text/plain')
def echoing_sub_view(sub_request, **kwargs):
    return JsonResponse(dict(
        request_path=sub_request.request.path,
        parent_path=sub_request.parent_path,
        sub_path=sub_request.sub_path,
        kwargs=kwargs,
    ))
urlpatterns = [
    urls.path('', home_page),
    urls.path('no_trailing_slash', urls.include(dss.sub_view_urls(echoing_sub_view))),
    urls.path('echoing_sub_view/', urls.include(dss.sub_view_urls(echoing_sub_view))),
    urls.path('<int:x>/echoing_sub_view/', urls.include(dss.sub_view_urls(echoing_sub_view))),
]
def get_json_data(url):
    c = Client()
    r = c.get(url)
    return json.loads(r.content.decode())

class TestBasic(unittest.TestCase):
    def test_urls(self):
        with self.assertRaises(urls.Resolver404):
            urls.resolve('fakepath')

        client = Client()

        # Ordinary view (registered before sub view) should work
        r = client.get('/')
        self.assertEqual(r.content, b'HOME')

        # sub view installed incorrectly (no trailing slash) should raise ValueError
        with self.assertRaises(ValueError) :
            client.get('/no_trailing_slash')

        data = get_json_data('/echoing_sub_view/')
        self.assertEqual(data['request_path'], '/echoing_sub_view/')
        self.assertEqual(data['parent_path'], '/echoing_sub_view/')
        self.assertEqual(data['sub_path'], '')
        self.assertEqual(data['kwargs'], dict())

        data = get_json_data('/echoing_sub_view/foo/bar')
        self.assertEqual(data['sub_path'], 'foo/bar')

        data = get_json_data('/1/echoing_sub_view/')
        self.assertEqual(data['request_path'], '/1/echoing_sub_view/')
        self.assertEqual(data['parent_path'], '/1/echoing_sub_view/')
        self.assertEqual(data['sub_path'], '')
        self.assertEqual(data['kwargs'], dict(x=1))

    def test_sub_request(self):
        r = RequestFactory().post('/foo/bar/baz?x=1', data=dict(y=2))
        sr = dss.SubRequest(r)
        self.assertEqual(sr.request, r)

        self.assertEqual(sr.headers , r.headers)
        self.assertEqual(sr.GET.get('x') , '1')
        self.assertEqual(sr.POST.get('y') , '2')
        self.assertEqual(len(sr.FILES) , 0)
        self.assertEqual(sr.method , 'POST')

        with self.assertRaises(ValueError) :
            sr._advance('bar')
        with self.assertRaises(ValueError) :
            sr._advance('foo')

        sr._advance('foo/bar/')
        self.assertEqual(sr.sub_path, 'baz')
        self.assertEqual(sr.parent_path+sr.sub_path, r.path)

        with self.assertRaises(ValueError):
            sr._advance('baz')

class TestRouter(unittest.TestCase):
    class EmptyRouter(dss.Router):
        pass
    def returning_mock_sub_view(self, sub_request, **kwargs):
        return sub_request, kwargs
    def sub_request_factory(self, path):
        r = RequestFactory().get(path)
        return dss.SubRequest(r)

    def test_empty(self):
        class R(dss.Router):
            pass
        with self.assertRaises(Http404):
            R()(self.sub_request_factory('/foo/'))

    def test_root(self):
        class R(dss.Router):
            root_view = lambda sr: 1
        self.assertEqual(R()(self.sub_request_factory('/')), 1)

    def test_cascade(self):
        def match_1(sr):
            if sr.sub_path == '1' :
                return 1
            raise Http404()
        def match_2(sr):
            if sr.sub_path == '2' :
                return 2
            raise Http404()

        class R(dss.Router):
            cascade = [
                match_1,
                match_2,
            ]

        self.assertEqual(R()(self.sub_request_factory('/1')), 1)
        self.assertEqual(R()(self.sub_request_factory('/2')), 2)
        with self.assertRaises(Http404):
            R()(self.sub_request_factory('/3'))

    # TODO - pattern matching tests


if __name__ == '__main__':
    unittest.main()
