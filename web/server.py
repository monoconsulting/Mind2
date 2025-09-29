#!/usr/bin/env python3
"""
Mind2 Documentation Web Server (mind-docs)
A simple web server for serving test documentation and results.
"""

import os
import sys
import json
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Try to import configuration, fallback to defaults
try:
    from config import PORT, HOST, DOCS_DIR as CONFIG_DOCS_DIR, DATA_DIR as CONFIG_DATA_DIR, AUTO_OPEN_BROWSER, LOG_REQUESTS, ENABLE_CORS
    DOCS_DIR = Path(CONFIG_DOCS_DIR) if CONFIG_DOCS_DIR else Path(__file__).parent
    DATA_DIR = Path(CONFIG_DATA_DIR) if CONFIG_DATA_DIR else DOCS_DIR / 'data'
except ImportError:
    # Default configuration if config.py doesn't exist
    PORT = 9091
    HOST = '0.0.0.0'
    DOCS_DIR = Path(__file__).parent
    DATA_DIR = DOCS_DIR / 'data'
    AUTO_OPEN_BROWSER = True
    LOG_REQUESTS = True
    ENABLE_CORS = True

class MindDocsHandler(SimpleHTTPRequestHandler):
    """Custom handler for Mind2 documentation server."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DOCS_DIR), **kwargs)

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)

        # API endpoints
        if parsed_path.path.startswith('/api/'):
            self.handle_api_request(parsed_path)
        else:
            # Serve static files
            super().do_GET()

    def do_POST(self):
        """Handle POST requests for API endpoints."""
        parsed_path = urlparse(self.path)

        if parsed_path.path.startswith('/api/'):
            self.handle_api_request(parsed_path, is_post=True)
        else:
            self.send_error(404, "Not Found")

    def handle_api_request(self, parsed_path, is_post=False):
        """Handle API requests."""
        if parsed_path.path == '/api/test-results':
            if is_post:
                self.handle_add_test_result()
            else:
                self.handle_get_test_results()
        elif parsed_path.path == '/api/health':
            self.handle_health_check()
        else:
            self.send_error(404, "API endpoint not found")

    def handle_get_test_results(self):
        """Get test results."""
        try:
            data_file = DATA_DIR / 'test-results.json'
            if data_file.exists():
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {'tests': []}

            self.send_json_response(data)
        except Exception as e:
            self.send_error(500, f"Error reading test results: {str(e)}")

    def handle_add_test_result(self):
        """Add a new test result."""
        try:
            content_length = int(self.headers.get('content-length', 0))
            post_data = self.rfile.read(content_length)
            test_result = json.loads(post_data.decode('utf-8'))

            # Validate required fields
            required_fields = ['testFile', 'description', 'successPercentage', 'score', 'maxScore']
            missing_fields = [field for field in required_fields if field not in test_result]

            if missing_fields:
                self.send_error(400, f"Missing required fields: {', '.join(missing_fields)}")
                return

            # Add timestamp if not provided
            if 'timestamp' not in test_result:
                test_result['timestamp'] = datetime.now().isoformat()

            # Ensure data directory exists
            DATA_DIR.mkdir(exist_ok=True)

            # Load existing data or create new
            data_file = DATA_DIR / 'test-results.json'
            if data_file.exists():
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {'tests': []}

            # Add new test result
            data['tests'].insert(0, test_result)  # Insert at beginning

            # Save updated data
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.send_json_response({'success': True, 'message': 'Test result added successfully'})

        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON data")
        except Exception as e:
            self.send_error(500, f"Error adding test result: {str(e)}")

    def handle_health_check(self):
        """Health check endpoint."""
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'server': 'mind-docs',
            'port': PORT
        }
        self.send_json_response(health_data)

    def send_json_response(self, data):
        """Send JSON response."""
        response_data = json.dumps(data, indent=2, ensure_ascii=False)
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response_data.encode('utf-8'))))

        # Add CORS headers if enabled
        if ENABLE_CORS:
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')

        self.end_headers()
        self.wfile.write(response_data.encode('utf-8'))

    def log_message(self, format, *args):
        """Custom log format."""
        if LOG_REQUESTS:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            message = format % args
            print(f"[{timestamp}] mind-docs: {message}")

def create_default_data():
    """Create default data files if they don't exist."""
    DATA_DIR.mkdir(exist_ok=True)

    # Create default test results file
    test_results_file = DATA_DIR / 'test-results.json'
    if not test_results_file.exists():
        default_data = {
            'tests': [],
            'created': datetime.now().isoformat(),
            'version': '1.0'
        }
        with open(test_results_file, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=2, ensure_ascii=False)

def start_server():
    """Start the documentation server."""
    create_default_data()

    try:
        server = HTTPServer((HOST, PORT), MindDocsHandler)
        print(f"Mind2 Documentation Server (mind-docs) starting...")
        print(f"Server listening on http://{HOST}:{PORT}")
        print(f"Documentation directory: {DOCS_DIR}")
        print("Press Ctrl+C to stop the server")

        # Open browser automatically (optional)
        if AUTO_OPEN_BROWSER and '--no-browser' not in sys.argv:
            def open_browser():
                webbrowser.open(f'http://localhost:{PORT}')

            # Open browser after a short delay
            timer = threading.Timer(2.0, open_browser)
            timer.start()

        server.serve_forever()

    except KeyboardInterrupt:
        print("\nShutting down mind-docs server...")
        server.shutdown()
    except OSError as e:
        if e.errno == 10048:  # Port already in use on Windows
            print(f"Error: Port {PORT} is already in use.")
            print("Please stop the existing server or change the PORT in server.py")
        else:
            print(f"Error starting server: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    start_server()