import os
import django
from django.test import RequestFactory
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'JamboPOS.settings')
django.setup()

rf = RequestFactory()
req = rf.get('/sales/')
SessionMiddleware(lambda x: x)(req)
req.user = User(username='test')

from point_of_sale.views import sales_page
from django.template import Template, Context

# Test if we modify base.html
with open('templates/base.html', 'r') as f:
    text = f.read()

# Add {% csrf_token %} right after <body>
text = text.replace('<body hx-headers=', '{% csrf_token %}\n<body hx-headers=')
with open('templates/base_test.html', 'w') as f:
    f.write(text)

# We can't render base_test immediately because extends is hardcoded, but we can do a quick check via raw template:
t_str = "{% csrf_token %} <body hx-headers='{\"X-CSRFToken\": \"{{ csrf_token }}\"}'>"
t = Template(t_str)
from django.template.context_processors import csrf
c = Context(csrf(req))
out = t.render(c)
print('NOTPROVIDED' in out, 'X-CSRFToken' in out)
print("Rendered:", out)
