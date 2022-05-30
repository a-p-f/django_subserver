import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')
django.setup()

from django import urls
from django.http import Http404, HttpResponse, JsonResponse
from django.test import Client, RequestFactory
from django import urls
from django_subserver import Router, SubRequest, sub_view_urls
from django_subserver.base import SubView
from django_subserver.pattern import Pattern
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
    urls.path('no_trailing_slash', urls.include(sub_view_urls(echoing_sub_view))),
    urls.path('echoing_sub_view/', urls.include(sub_view_urls(echoing_sub_view))),
    urls.path('<int:x>/echoing_sub_view/', urls.include(sub_view_urls(echoing_sub_view))),
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

    def test_root_urls(self):
        '''
        Note - here we're verifying that sub_view_urls works when installed at '/'.
        Unlike test_urls, which is a complete integration test relying on django being setup,
        here we hack into django internals and do our own url resolving.
        This is easier than trying to reconfigure django with a new set of urlpatterns.
        '''
        def sub_view(request, **kwargs):
            return 5
        from django.urls.resolvers import RegexPattern, URLResolver
        from django.urls import path, include
        r = URLResolver(RegexPattern(r'^/'), [
            path('', include(sub_view_urls(sub_view)))
        ])
        request = RequestFactory().get('/')
        match = r.resolve(request.path)
        response = match.func(request, **match.kwargs)
        self.assertEqual(response, 5)

    def test_sub_request(self):
        r = RequestFactory().post('/foo/bar/baz?x=1', data=dict(y=2))
        sr = SubRequest(r)

        self.assertEqual(sr.request, r)

        # Custom attribute setting/clearing
        sr.custom_property = 5
        self.assertEqual(sr.custom_property, 5)
        sr.clear_data_except()
        with self.assertRaises(AttributeError):
            sr.custom_property

        # HttpRequest attribute delegation
        for attr in SubRequest.PUBLIC_REQUEST_ATTRIBUTES :
            # These aren't available in all supported versions of django
            # Will raise AttributeError in some versions
            if attr in ['is_ajax', 'accepts'] :
                continue

            self.assertEqual(getattr(sr, attr), getattr(r, attr))

        # custom attributes can be set
        sr.foo = 1
        # class methods cannot be shadowed
        with self.assertRaises(AttributeError):
            sr.after = 1
        # class properties cannot be shadowed
        with self.assertRaises(AttributeError):
            sr.sub_path = 1
        # HttpRequest attributes cannot be shadowed
        with self.assertRaises(AttributeError):
            sr.path = 1
        # And new private properties cannot be added
        with self.assertRaises(AttributeError):
            sr._foo = 1

    def test_sub_request_clear_data(self):
        r = RequestFactory().post('/foo/bar/baz?x=1', data=dict(y=2))
        r.user = 'Alex'
        sr = SubRequest(r)
        self.assertEqual(sr.user, 'Alex')
        sr.foo = 5
        self.assertEqual(sr.foo, 5)
        sr.clear_data_except(common_middleware=True)
        self.assertEqual(sr.user, 'Alex')
        sr.clear_data_except()
        with self.assertRaises(AttributeError):
            sr.user

        sr.foo = 5
        sr.bar = 2
        sr.baz = 1
        sr.clear_data_except('foo', 'bar')
        self.assertEqual(sr.foo, 5)
        self.assertEqual(sr.bar, 2)
        with self.assertRaises(AttributeError):
            sr.baz

    def test_sub_request_after(self):
        r = RequestFactory().post('/foo/bar/baz?x=1', data=dict(y=2))
        sr = SubRequest(r)

        with self.assertRaises(ValueError) :
            sr.after('bar')
        with self.assertRaises(ValueError) :
            sr.after('foo')
        sr = sr.after('foo/bar/')
        self.assertEqual(sr.sub_path, 'baz')
        self.assertEqual(sr.parent_path+sr.sub_path, r.path)
        with self.assertRaises(ValueError):
            sr.after('baz')

        # Check that custom data is copied, and independent
        sr = SubRequest(r)
        sr.foo = 5
        sr.bar = 4
        sr2 = sr.after('foo/')
        sr2.clear_data_except('foo')
        self.assertEqual(sr2.foo, 5)
        with self.assertRaises(AttributeError):
            sr2.bar
        self.assertEqual(sr.bar, 4)

class TestPattern(unittest.TestCase):
    def test_format_errors(self):
        # should not raise
        Pattern('<int:x>/')

        # Must end in '/'
        with self.assertRaises(ValueError):
            Pattern('a')
        with self.assertRaises(ValueError):
            Pattern('<invalid_converter:x>')

        with self.assertRaises(ValueError):
            Pattern('<int>')
        with self.assertRaises(ValueError):
            Pattern('<int:>')

    def test_fixed(self):
        p = Pattern('a/')
        match, captures = p.match('a/')
        self.assertEqual(match, 'a/')
        self.assertEqual(captures, dict())

        match, captures = p.match('a/b/')
        self.assertEqual(match, 'a/')
        self.assertEqual(captures, dict())

        with self.assertRaises(ValueError):
            p.match('b/')

    def test_int(self):
        p = Pattern('<int:x>/')

        match, captures = p.match('1/')
        self.assertEqual(match, '1/')
        self.assertEqual(captures, dict(x=1))

        match, captures = p.match('-1/')
        self.assertEqual(match, '-1/')
        self.assertEqual(captures, dict(x=-1))

        match, captures = p.match('1/2/')
        self.assertEqual(match, '1/')
        self.assertEqual(captures, dict(x=1))

        with self.assertRaises(ValueError):
            p.match('a/')

    def test_date(self):
        from datetime import date

        p = Pattern('<date:x>/')
        d = date(2000, 1, 1)

        match, captures = p.match('2000-01-01/')
        self.assertEqual(match, '2000-01-01/')
        self.assertEqual(captures, dict(x=d))

        match, captures = p.match('2000-01-01/2/')
        self.assertEqual(match, '2000-01-01/')
        self.assertEqual(captures, dict(x=d))

        with self.assertRaises(ValueError):
            p.match('a/')
        with self.assertRaises(ValueError):
            p.match('2000-13-01/')

    def test_str(self):
        p = Pattern('<str:x>/')
        match, captures = p.match('foobar/1/')
        self.assertEqual(match, 'foobar/')
        self.assertEqual(captures, dict(x='foobar'))

    def test_multi(self):
        from datetime import date
        p = Pattern('prefix-<str:s>/<int:i>-<date:d>/suffix/')
        match, captures = p.match('prefix-string/-33-2000-01-01/suffix/other')
        self.assertEqual(match, 'prefix-string/-33-2000-01-01/suffix/')
        self.assertEqual(captures, dict(s='string', i=-33, d=date(2000,1,1)))

class TestRouter(unittest.TestCase):
    class EmptyRouter(Router):
        pass
    def returning_mock_sub_view(self, sub_request, **kwargs):
        return sub_request, kwargs
    def sub_request_factory(self, path):
        r = RequestFactory().get(path)
        return SubRequest(r)

    def test_empty(self):
        class R(Router):
            pass
        with self.assertRaises(Http404):
            R()(self.sub_request_factory('/foo/'))

    def test_root(self):
        class R(Router):
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

        class R(Router):
            cascade = [
                match_1,
                match_2,
            ]

        self.assertEqual(R()(self.sub_request_factory('/1')), 1)
        self.assertEqual(R()(self.sub_request_factory('/2')), 2)
        with self.assertRaises(Http404):
            R()(self.sub_request_factory('/3'))

    def test_routes(self):
        class R(Router):
            routes = {
                '<int:x>/': self.returning_mock_sub_view,
            }
            cascade = [
                lambda r, **kwargs: 'CASCADE',
            ]

        response = R()(self.sub_request_factory('/5/foo'))
        sr, kwargs = response
        self.assertEqual(sr.sub_path, 'foo')
        self.assertEqual(kwargs, dict(x=5))

        r = R()(self.sub_request_factory('xyz/'))
        self.assertEqual(r, 'CASCADE')

    def test_path(self):
        def match_a(request):
            if request.sub_path == 'a' :
                return 'CASCADE'
            raise Http404()
        class R(Router):
            cascade = [
                match_a,
            ]
            path_view = lambda r, **kwargs: r.sub_path

        self.assertEqual(
            R()(SubRequest(RequestFactory().get('/a'))),
            'CASCADE',
        )
        self.assertEqual(
            R()(SubRequest(RequestFactory().get('/foobar'))),
            'foobar',
        )

    def test_view_spec(self):
        class R(Router):
            routes = {
                # Defined in same module
                'a/': 'ReturnA',
                # Defined in external module
                'b/': 'tests.hello_world_sub_view.View',
            }

        r = R()
        self.assertEqual(
            r(SubRequest(RequestFactory().get('/a/'))),
            'A',
        )
        self.assertEqual(
            r(SubRequest(RequestFactory().get('/b/'))),
            'Hello, World!',
        )

class ReturnA(SubView):
    def __call__(self, *args, **kwargs):
        return 'A'

class TestModuleView(unittest.TestCase):
    def test(self):
        from django_subserver.module_view import package_view_importer
        importer = package_view_importer('tests.view_modules')

        view = importer('hello_world')

        rf = RequestFactory()

        # test get
        self.assertEqual(
            view(rf.get('/')),
            'Hello, World!',
        )
        # Not Allowed
        self.assertEqual(
            view(rf.post('/')).status_code,
            405,
        )
        # Options
        self.assertEqual(
            view(rf.options('/')).get('allow'),
            'GET, OPTIONS',
        )

if __name__ == '__main__':
    unittest.main()
