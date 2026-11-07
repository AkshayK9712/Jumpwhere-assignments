# Products REST API (Django + DRF)

## Setup
```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
python manage.py test      # run the test suite
```

## Endpoints
| Method | URL | Action | Success | Errors |
|---|---|---|---|---|
| GET | `/products` | List | 200 | |
| POST | `/products` | Create | 201 (+ `Location` header) | 400 |
| GET | `/products/<id>` | Read | 200 | 404 |
| PUT | `/products/<id>` | Full update | 200 | 400, 404 |
| PATCH | `/products/<id>` | Partial update | 200 | 400, 404 |
| DELETE | `/products/<id>` | Delete | 204 | 404 |

Other status codes you may see: 415 for a non-JSON `Content-Type`, 405 for an unsupported method.

## Validation rules
- `name`: required, non-blank, max 200 chars
- `price`: required, decimal, must be > 0
- `stock`: optional integer, >= 0 (default 0)
- `description`: optional
- Malformed JSON returns 400 with a `detail` message.

## Try it
```bash
curl -i -X POST localhost:8000/products -H "Content-Type: application/json" \
     -d '{"name":"Mug","price":"9.99","stock":5}'
curl -i localhost:8000/products
curl -i localhost:8000/products/1
curl -i -X PATCH localhost:8000/products/1 -H "Content-Type: application/json" -d '{"stock":20}'
curl -i -X PUT localhost:8000/products/1 -H "Content-Type: application/json" \
     -d '{"name":"Big Mug","price":"12.00","stock":3}'
curl -i -X DELETE localhost:8000/products/1
curl -i localhost:8000/products/999          # 404
curl -i -X POST localhost:8000/products -H "Content-Type: application/json" -d '{"price":"-1"}'   # 400
```

## Idempotency notes
- POST is not idempotent: each call creates a new product.
- PUT and PATCH (with the same body) leave the same final state when repeated.
- DELETE is idempotent in effect: the product stays gone. The first call returns 204 and later calls return 404.
