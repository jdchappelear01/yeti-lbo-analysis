#!/usr/bin/env python3
import http.server
import socketserver
import subprocess
import os
import urllib.parse
import sys
import time

PORT = 8000

class AnalysisHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Serve the index.html file
        if self.path == '/' or self.path == '/index.html':
            self.path = '/index.html'
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        
        # Handle the analysis request
        elif self.path == '/run_analysis.py':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            
            try:
                # Create a devnull file object to suppress output
                with open(os.devnull, 'w') as devnull:
                    # Run the data extraction script with all output suppressed
                    subprocess.run(
                        [sys.executable, 'src/document_processing/data_extraction.py'],
                        stdout=devnull,
                        stderr=devnull
                    )
                
                # Give it a moment to ensure file writing is complete
                time.sleep(2)
                
                # Read and return only the final LBO analysis
                lbo_output_path = 'output/YETI_lbo_analysis.txt'
                if os.path.exists(lbo_output_path):
                    with open(lbo_output_path, 'r') as f:
                        lbo_analysis = f.read()
                        self.wfile.write(lbo_analysis.encode())
                else:
                    self.wfile.write("Analysis not yet available. Please try again in a few minutes.".encode())
                    
            except Exception as e:
                self.wfile.write(f"Error: {str(e)}".encode())
        
        # Serve other static files
        else:
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

def main():
    # Create the server
    handler = AnalysisHandler
    httpd = socketserver.TCPServer(("", PORT), handler)
    
    print(f"Server running at http://localhost:{PORT}")
    print("Press Ctrl+C to stop")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped")
        httpd.server_close()

if __name__ == "__main__":
    main() 