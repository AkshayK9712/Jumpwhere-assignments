Request-response cycle observed

Each time I visited a URL or ran curl, my client (browser/curl) sent an HTTP GET request to the Flask dev server at 127.0.0.1:5000. Flask matched the URL path against the routes registered with @app.route, ran the matching Python function, and turned its return value into an HTTP response: a status line, headers, and a body. The client then received and displayed that response.

GET / → 200 OK, text/html body with the greeting.
GET /api/time → 200 OK, application/json body containing the current server time.
GET /greet?name=Sam → 200 OK, personalized HTML. The query string after ? is passed to the server and read via request.args.
GET /does-not-exist → 404 NOT FOUND, because no route matched the path.

Using curl -i made the status line and headers visible, which a browser normally hides. The Flask console also logged each request with its status code.