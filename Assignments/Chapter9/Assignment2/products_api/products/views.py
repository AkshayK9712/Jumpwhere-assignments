from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Product
from .serializers import ProductSerializer


class ProductListCreateView(APIView):
    """GET /products  -> list (200)
    POST /products -> create (201, or 400 on invalid JSON/data)
    """

    def get(self, request):
        serializer = ProductSerializer(Product.objects.all(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # -> 400 with field errors
        product = serializer.save()
        headers = {"Location": f"/products/{product.pk}"}
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class ProductDetailView(APIView):
    """GET /products/<id>    -> read (200 / 404)
    PUT /products/<id>    -> full update (200 / 400 / 404)
    PATCH /products/<id>  -> partial update (200 / 400 / 404)
    DELETE /products/<id> -> delete (204 / 404)
    """

    def get_object(self, pk):
        # Raises Http404, which DRF turns into a JSON 404 instead of crashing.
        return get_object_or_404(Product, pk=pk)

    def get(self, request, pk):
        return Response(ProductSerializer(self.get_object(pk)).data)

    def put(self, request, pk):
        serializer = ProductSerializer(self.get_object(pk), data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        serializer = ProductSerializer(self.get_object(pk), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        self.get_object(pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
