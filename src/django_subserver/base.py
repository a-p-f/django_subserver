from abc import ABC
from django.http import HttpRequest, HttpResponse

class SubRequest:
    '''
    Very similar to HttpRequest, with the ability to keep track of
    "parent_path" and "sub_path".

    SubRequests wrap HttpRequests, and expose most of the important
    HttpRequest properties from the request.

    The wrapped request can be accessed directly, if needed.

    This interface is considered final.
    We'll never add any more (public) attributes.
    All of our own attributes are either prefixed with '_', or are
    implemented via properties (which cannot accidentally be replaced).

    Users of SubRequests should feel free to add attributes at will, 
    to pass information from one "sub view" to another
    (just don't add anything prefixed with '_').
    '''
    def __init__(self, request: HttpRequest): 
        self._request = request
        self._parent_path_length = 1

    @property
    def request(self) -> HttpRequest:
        '''
        Returns the HttpRequest associated with this SubRequest.
        We have properties to expose the most commonly needed attributes from this request,
        but users can always access the request directly, if needed.
        '''
        return self._request

    @property
    def parent_path(self):
        '''
        Returns the portion of the url path that has already been interpreted.
        Guarantee: 
        parent_path.endswith('/')
        '''
        return self._request.path[:self._parent_path_length]

    @property
    def sub_path(self):
        '''
        Returns the part of the path that has not yet been interpreted.
        Guarantee:
        parent_path + sub_path = request.path
        '''
        return self._request.path[self._parent_path_length:]

    def _advance(self, path_portion: str):
        '''
        Note: _advance _is_ considered public 
        (though end users aren't likely to need it).

        The main reason it's prefixed with _ is to ensure that end users 
        don't accidentally overwrite it.
        '''
        if not path_portion.endswith('/') :
            raise ValueError('path_portion must end with "/"')
        if not self.sub_path.startswith(path_portion) :
            raise ValueError('path_portion is not a prefix of sub_path')
        self._parent_path_length += len(path_portion)

    # Expose various useful request properties
    @property 
    def headers(self):
        '''Returns self.request.headers'''
        return self._request.headers
    @property 
    def method(self):
        '''Returns self.request.method'''
        return self._request.method
    @property 
    def GET(self):
        '''Returns self.request.GET'''
        return self._request.GET
    @property 
    def POST(self):
        '''Returns self.request.POST'''
        return self._request.POST
    @property 
    def FILES(self):
        '''Returns self.request.FILES'''
        return self._request.FILES

class SubView(ABC):
    '''
    This is just a description of what a "sub view" is.

    A standard django view function takes:
    - an HttpRequest
    - ALL captured url parameters

    A "sub view" is similar. It takes:
    - a SubRequest
    - parameters captured by the parent Router only
    '''
    def __call__(self, request: SubRequest, **captured_params) -> HttpResponse :
        pass