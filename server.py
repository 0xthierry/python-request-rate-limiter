import http.server
import socketserver
import json
import time
from collections import defaultdict

class RateLimiter:
    def __init__(self, max_requests, window_size):
        self.max_requests = max_requests
        self.window_size = window_size
        self.requests = defaultdict(int)
        self.windows = defaultdict(int)

    def allow_request(self, client_id):
        current_window = int(time.time() / self.window_size)
        if current_window != self.windows[client_id]:
            self.requests[client_id] = 0
            self.windows[client_id] = current_window

        if self.requests[client_id] < self.max_requests:
            self.requests[client_id] += 1
            return True
        return False

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Handle requests in a separate thread."""

class HTTPServer(http.server.SimpleHTTPRequestHandler):
    rate_limiter = RateLimiter(max_requests=10, window_size=60)  # 10 requests per 60 seconds

    def do_GET(self):
        client_ip = self.client_address[0]
        if self.path == '/status':
            if self.rate_limiter.allow_request(client_ip):
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = json.dumps({'ok': True})
                self.wfile.write(response.encode())
            else:
                self.send_response(429)  # Too Many Requests
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = json.dumps({'message': 'Rate limit exceeded. Try again later.'})
                self.wfile.write(response.encode())
        else:
            super().do_GET()

if __name__ == "__main__":
    PORT = 9000
    server = ThreadedHTTPServer(("", PORT), HTTPServer)
    print("Serving at port:", PORT)
    server.serve_forever()
