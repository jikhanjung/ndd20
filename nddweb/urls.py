from django.urls import path

from viewer import views
from viewer import review_views

urlpatterns = [
    path("", review_views.queue, name="review_queue"),
    path("browse", views.index, name="index"),
    path("review/<int:pk>", review_views.detail, name="review_detail"),
    path("review/<int:pk>/image", review_views.review_image, name="review_image"),
    path("ind/<str:ind>", views.individual, name="individual"),
    path("img/<str:kind>/<path:key>", views.image, name="image"),
]
