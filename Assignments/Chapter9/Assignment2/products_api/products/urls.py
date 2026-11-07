from django.urls import re_path

from . import views

urlpatterns = [
    # Trailing slash is optional, so both /products and /products/ work.
    re_path(r"^products/?$", views.ProductListCreateView.as_view(), name="product-list"),
    re_path(r"^products/(?P<pk>\d+)/?$", views.ProductDetailView.as_view(), name="product-detail"),
]
