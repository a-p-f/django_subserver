from django import urls
from typing import Any, Mapping, Optional, Sequence

from .base import SubView, SubRequest

def sub_view_urls(sub_view:SubView) -> Sequence[urls.URLPattern]:
    '''
    Provides a means of "installing" a SubView via django urls.

    Returns a list of URLPatterns that will invoke the given SubView
    with an appropriate SubRequest.

    These should be "included" in your url patterns.

    If you "include" under a non-empty prefix, that prefix MUST end with '/'

    You may capture url parameters, and they will be passed to the SubView.
    Any such parameters must be named (not positional), and you cannot 
    name any of them "sub_path" (since we use that).

    Sample usage:

    url_patterns = [
        path('my_sub_app', include(dss.sub_view_urls(my_sub_app))),
    ]
    '''
    def view(request, sub_path='', **other_url_kwargs):
        sub_request = SubRequest(request)
        parent_path = request.path[:len(sub_path)]

        if not parent_path.endswith('/') :
            raise ValueError(f'Invalid parent path: "{parent_path}". Any prefix you include() sub_view_urls() underneath MUST end in "/".')

        sub_request.advance(parent_path)
        return sub_view(sub_request, **other_url_kwargs)

    return [
        # The empty sub_path case
        urls.path(pattern, view),
        # The non-empty sub_path case
        urls.path(pattern+'<path:sub_path>', view),
    ]

