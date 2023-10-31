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

    Note: we used to implement this with urls.path, instead of urls.re_path.
    That approach required two separate paths.
    However, it was actually broken, so we switched to re_path.
    For backward compatibility, we're not changing our signature.
    We could, however, _add_ a simpler sub_view_path(SubView)->URLPattern function to this module.
    '''
    def view(request, sub_path='', **other_url_kwargs):
        sub_request = SubRequest(request)

        path = request.path
        handled = path[:len(path)-len(sub_path)]

        if not handled.endswith('/') :
            raise ValueError(f'Invalid parent path: "{handled}". Any prefix you include() sub_view_urls() underneath MUST end in "/".')

        # handled startswith '/', but that '/' is already part of sub_request.parent_path, not sub_request.sub_path
        to_advance = handled[1:]
        if to_advance :
            sub_request = sub_request.after(to_advance)
        return sub_view(sub_request, **other_url_kwargs)

    return [
        # Match anything, including newlines (which might be encoded in URL as %0A)
        urls.re_path(r'^(?P<sub_path>[\s\S]*)$', view),
    ]
