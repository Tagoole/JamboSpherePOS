import os
import django
from django.test import RequestFactory
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from django.middleware.csrf import CsrfViewMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'JamboPOS.settings')
django.setup()

rf = RequestFactory()
req = rf.get('/sales/')
SessionMiddleware(lambda x: x)(req)
req.user = User(username='test')

from point_of_sale.views import sales_page
res = sales_page(req)
res = CsrfViewMiddleware(lambda r: res)(req)  # Simulate middleware call

body = str(res.content)
print("X-CSRFToken found:", "X-CSRFToken" in body)
print("NOTPROVIDED found:", "NOTPROVIDED" in body)
print("Token substring:", body[body.find("X-CSRFToken"):body.find("X-CSRFToken")+50])
