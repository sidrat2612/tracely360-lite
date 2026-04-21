from .sample_django_nested import urlpatterns as nested_patterns
from django.urls import include, path


urlpatterns = [
    path('tuple-api/', include((nested_patterns, 'nested'))),
]