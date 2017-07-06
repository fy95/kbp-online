"""service URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import include, url
from django.contrib import admin, staticfiles
from registration.backends.hmac.views import RegistrationView

from web.forms import UserForm
from . import settings

class RedirectRegistrationView(RegistrationView):
    def get_success_url(self, request, user):
        return "/accounts/login/"

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^accounts/register/$', RegistrationView.as_view(form_class=UserForm, success_url='/submissions/'),
        name='registration_register',
       ),
    url(r'^accounts/register/complete$', RegistrationView.as_view(form_class=UserForm, success_url='/submissions/'),
        name='registration_register_complete',
       ),
    url(r'^accounts/', include('registration.backends.hmac.urls')),
    url(r'', include('web.urls')),
]
if settings.DEBUG and hasattr(staticfiles, 'views'):
    urlpatterns += [
        url(r'^static/(?P<path>.*)$', staticfiles.views.serve),
    ]
handler404 = 'web.views.handle404'
handler500 = 'web.views.handle500'
