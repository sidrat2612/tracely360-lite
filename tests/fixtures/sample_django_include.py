from django.urls import include, path


urlpatterns = [
    path('api/', include('sample_django_nested')),
]