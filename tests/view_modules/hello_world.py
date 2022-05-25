def handle_auth(request):
    if request.path == '/deny' :
        return 'DENIED'
def handle_get(request):
    return 'Hello, World!'