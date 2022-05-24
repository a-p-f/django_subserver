# django_subserver

Allows you to compose your web app from a hierarchy of "sub views".

A standard django view is responsible for interpreting _all_ of the url parameters, and then returing a response. In crud/management apps, you often end up with many views that share common "preprocessing" steps.

The "sub view" approach is different. A sub view may return a response, or it may interpret only part of the url and then delegate the request (and the rest of the url) to another sub view.

Each sub view in the chain can preform any type of middleware action - attach data to the request, return early, manipulate the response from subsequent sub views, or handle exceptions from subsequent sub views.

## Intro

`SubRequest`: A simple wrapper around django's HttpRequest, which maintains a concept of "parent_path" (which has already been interpreted by higher sub views) and "sub_path" (which must still be interpreted). You won't likely ever have to create these, but you'll be using them instead of plain HttpRequests in your sub views.

`Router`: A sub view which performs pattern matching (on sub_path) and delegates to other sub views.

`MethodView`: A sub view which performs dispatch-by-method, similar to django.views.generic.View. 

`sub_view_urls(sub_view)`: A utility function for generating a list of (2) url patterns, for mapping a parent path to a particular sub view.

## Recommended (Basic) Setup

### urls.py
```py
from django_subview import sub_view_urls
from .routers import root_router

urlpatterns = [
    # standard django views here
    ...,

    path('', include(sub_view_urls(root_router))),
    # OR
    # path('my_sub_view_handled_section/', include(dsv.sub_view_urls(RouterRoot))),
]
```

### routers.py

We recommend:
- put all your routers in a single file
- use common prefix for related routers
- use a utility function to import views that are defined in a separate module, so you don't have to write module name twice
- use snake_case instead of CamelCase for your Router subclasses: you'll have a lot of routers, and the names will be easier to read this way (especially if you use code folding or some other editor feature to show a condensed list of all your routers)
- put all of your auth logic in routers.py: the final sub views you delegate to should be dumb

```py
from django_subview import Router
from importlib import import_module

def get_view(module_name):
    '''
    Simple helper for imorting sub views defined in the sub_views package
    '''
    return import_module('sub_views.'+module_name).View()

class root_router(Router):
    root_view = get_view('home')
    routes = {
        'admin/': admin_router(),
        'my_books/': 'my_books_router',
    }
class admin_router(Router):
    ...
class my_books_router(Router):
    def prepare(self, request):
        # ensure user is logged in...
        request.my_books = ...

    root_view = get_view('my_book_list')
    routes = {
        '<int:book_id>/': 'my_books_detail_router',
    }
    ...
class my_books_detail_router(Router):
    def prepare(self, request, book_id):
        request.book = get_object_or_404(request.my_books, pk=book_id)

    root_view = get_view('my_book_detail')
...
```

### sub_views/

sub_views/
    home.py
    my_books_list.py
    my_books_detail.py
    ...

home.py:
```
from django_subview import MethodView

class View(MethodView):
    def get(self, request):
        ...
```

## Documentation

Read the code.

## Credits / Similar Ideas

This is very similar to Dart's "shelf" package (https://pub.dev/packages/shelf). I've never used it, but did some take some inspiration from it after glancing it over.

I've had this concept in my mind for a long time, and there are probably other implementations of it.
