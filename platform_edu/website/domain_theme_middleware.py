class DomainThemeMiddleware:
    """
    Detects the domain and assigns a theme identifier.
    Supports local testing via ?theme=example or ?theme=academy query parameter.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().lower()
        
        # FOR LOCAL TESTING: Check for query parameter override
        # Usage: http://localhost:8000/?theme=example or ?theme=apex or ?theme=topibtutors
        theme_override = request.GET.get('theme')
        if theme_override in ['academy', 'example', 'apex', 'iboost', 'topibtutors']:
            request.theme = theme_override
            request.show_home_as_landing = (theme_override in ['example', 'apex', 'topibtutors'])
            return self.get_response(request)
        
        # Normal domain detection for production
        if 'topibtutors' in host:
            request.theme = 'topibtutors'
            request.show_home_as_landing = True  # Show home page at root
        elif 'apex' in host:
            request.theme = 'apex'
            request.show_home_as_landing = True  # Show home page at root
        elif 'example.edunade.com' in host:
            request.theme = 'example'
            request.show_home_as_landing = True  # Show home page at root
        elif 'iboost' in host:
            request.theme = 'iboost'
            request.show_home_as_landing = False  # Show landing page at root
        elif 'academy.edunade.com' in host or '127.0.0.1' in host or 'localhost' in host:
            request.theme = 'academy'
            request.show_home_as_landing = False  # Show landing page at root
        else:
            # Default fallback
            request.theme = 'academy'
            request.show_home_as_landing = False
        
        return self.get_response(request)

