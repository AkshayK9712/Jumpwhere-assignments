from rest_framework.test import APITestCase

from .models import Product


class ProductApiTests(APITestCase):
    def setUp(self):
        self.product = Product.objects.create(name="Mug", description="Ceramic", price="9.99", stock=5)
        self.list_url = "/products"
        self.detail_url = f"/products/{self.product.pk}"
        self.missing_url = "/products/99999"

    # --- Read ---
    def test_list_returns_200(self):
        r = self.client.get(self.list_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 1)

    def test_retrieve_returns_200(self):
        r = self.client.get(self.detail_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["name"], "Mug")

    def test_retrieve_missing_returns_404(self):
        self.assertEqual(self.client.get(self.missing_url).status_code, 404)

    # --- Create ---
    def test_create_returns_201(self):
        r = self.client.post(self.list_url, {"name": "Pen", "price": "1.50", "stock": 10}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Product.objects.count(), 2)
        self.assertIn("Location", r.headers)

    def test_create_is_not_idempotent(self):
        payload = {"name": "Pen", "price": "1.50"}
        self.client.post(self.list_url, payload, format="json")
        self.client.post(self.list_url, payload, format="json")
        self.assertEqual(Product.objects.filter(name="Pen").count(), 2)

    def test_create_missing_required_fields_returns_400(self):
        r = self.client.post(self.list_url, {"description": "x"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("name", r.json())
        self.assertIn("price", r.json())

    def test_create_invalid_values_returns_400(self):
        r = self.client.post(self.list_url, {"name": "Bad", "price": "-5", "stock": -1}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("price", r.json())
        self.assertIn("stock", r.json())

    def test_create_wrong_types_returns_400(self):
        r = self.client.post(self.list_url, {"name": "Bad", "price": "abc"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_create_malformed_json_returns_400(self):
        r = self.client.post(self.list_url, data="{not json", content_type="application/json")
        self.assertEqual(r.status_code, 400)

    # --- Update ---
    def test_put_returns_200(self):
        r = self.client.put(self.detail_url, {"name": "Big Mug", "price": "12.00", "stock": 3}, format="json")
        self.assertEqual(r.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Big Mug")

    def test_put_is_idempotent(self):
        payload = {"name": "Big Mug", "price": "12.00", "stock": 3}
        first = self.client.put(self.detail_url, payload, format="json").json()
        second = self.client.put(self.detail_url, payload, format="json").json()
        self.assertEqual(first["name"], second["name"])
        self.assertEqual(Product.objects.count(), 1)

    def test_put_missing_field_returns_400(self):
        r = self.client.put(self.detail_url, {"name": "Only name"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_patch_returns_200_and_keeps_other_fields(self):
        r = self.client.patch(self.detail_url, {"stock": 42}, format="json")
        self.assertEqual(r.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 42)
        self.assertEqual(self.product.name, "Mug")

    def test_patch_invalid_returns_400(self):
        r = self.client.patch(self.detail_url, {"price": "0"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_update_missing_returns_404(self):
        self.assertEqual(self.client.put(self.missing_url, {"name": "x", "price": "1"}, format="json").status_code, 404)
        self.assertEqual(self.client.patch(self.missing_url, {"stock": 1}, format="json").status_code, 404)

    # --- Delete ---
    def test_delete_returns_204_then_404(self):
        self.assertEqual(self.client.delete(self.detail_url).status_code, 204)
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())
        # Same end state on repeat; the resource is simply gone now.
        self.assertEqual(self.client.delete(self.detail_url).status_code, 404)

    def test_delete_missing_returns_404(self):
        self.assertEqual(self.client.delete(self.missing_url).status_code, 404)
