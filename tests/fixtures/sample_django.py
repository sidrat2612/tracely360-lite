from django.urls import path


def health(request):
    return None


def users(request):
    return None


urlpatterns = [
    path('/health', health),
    path('/users', users),
]