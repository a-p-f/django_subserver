from django_subserver.base import SubView

class View(SubView):
    def __call__(self, *args, **kwargs):
        return 'Hello, World!'