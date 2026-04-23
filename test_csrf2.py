import os
import django
from django.test import RequestFactory
from django.template import Template, Context
from django.middleware.csrf import CsrfViewMiddleware

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "JamboPOS.settings")
django.setup()

def get_response(request):
    t = Template("{% csrf_token %} {{ csrf_token }}")
    from django.template.context_processors import csrf
    c = Context(csrf(request))
    return django.http.HttpResponse(t.render(c))

request = RequestFactory().get("/")
def get_response2(request): return django.http.HttpResponse("")
mw = CsrfViewMiddleware(get_response2)
mw.process_view(request, get_response, (), {})
t = Template("{% csrf_token %} {{ csrf_token }}")
from django.template.context_processors import csrf
c = Context(csrf(request))
print("TOKEN:", t.render(c))
