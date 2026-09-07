from django.urls import path

from viewer import views

urlpatterns = [
    path("", views.index, name="index"),
    path("ind/<str:ind>", views.individual, name="individual"),
    path("img/<str:kind>/<path:key>", views.image, name="image"),
]
