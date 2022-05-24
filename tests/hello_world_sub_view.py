from django_subview.base import SubView

class View(SubView):
    def __call__(self, *args, **kwargs):
        return 'Hello, World!'