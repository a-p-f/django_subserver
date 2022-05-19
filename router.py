from django.http import HttpResponse, Http404
from typing import Optional

class Router(SubView):
    def prepare(self, request: SubRequest, **captured_params:Any) -> Optional[HttpResponse] :
        '''
        Subclasses may override.

        If you receive any captured_params, you probably want to interpret and
        attach to request.

        You perform auth here. You may return an HttpResponse to prevent any
        further processing.
        '''
        pass

    root_view: Optional[SubView] = None

    def routes() -> dict[str, SubView]:
        '''
        Subclasses may override.
        Note - we'll always call this as if it was a staticmethod 
        (no cls or self argument).
        You can use the @staticmethod decorator if you want to be explicit,
        but it's not necessary.
        We recommend saving yourself a line, and leaving it off.
        '''
        return dict()

    path_view: Optional[SubView] = None

    def cascade_to() -> list[SubView]:
        '''
        Subclasses may override.
        Note - we'll always call this as if it was a staticmethod 
        (no cls or self argument).
        You can use the @staticmethod decorator if you want to be explicit,
        but it's not necessary.
        We recommend saving yourself a line, and leaving it off.
        '''
        return []

    def dispatch(self, request:SubRequest, view:SubView) -> HttpResponse :
        '''
        Subclasses may override to provide response manipulation 
        or exception handling.
        '''
        return view(request)

    # Not to be overriden by sub classes
    def __init__(self):
        self.root_view = None
        # TODO - convert str keys to Patterns
        self.routes = [
            (Pattern(pattern), view)
            for pattern, view in self.__class__.routes().items()
        ]
        self.cascade_to = self.__class__.cascade_to()
    def __call__(self, request:SubRequest, **captured_params:[Any]) -> HttpResponse :
        possible_response = self.prepare(request, **captured_params)
        if possible_response :
            return possible_response
        return self.dispatch(request, self._route)
    def _route(self, request):
        if not request.sub_path and self.root_view :
            return self.root_view(request)
        for pattern, view in self.routes :
            try :
                match, captures = pattern.match(request.sub_path)
            except ValueError :
                continue
            else :
                request.advance(match)
                return view(request, **captures)
        if request.sub_path and self.path_view :
            return self.path_view(request)
        for view in self.cascade_to :
            try :
                return view(request)
            except Http404 :
                continue
        raise Http404()
