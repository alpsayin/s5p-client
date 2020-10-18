#!/usr/bin/env python3
"""
 Copyright (c) 2020 Alp Sayin <alpsayin@alpsayin.com>, Novit.ai <info@novit.ai>
 
 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:
 
 The above copyright notice and this permission notice shall be included in all
 copies or substantial portions of the Software.
 
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 SOFTWARE.
 
"""

import http.server
import socketserver
from pathlib import Path
import traceback

REACT_APP_DIR = 'reactapp/build'
PORT = 8080

class ReactRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        print(f'request path: {self.path}')
        print(f'potential host path: {Path(f"{REACT_APP_DIR}/"+self.path)}')
        if self.path == '/':
            self.path = f'{REACT_APP_DIR}/index.html'
        elif Path(f"{REACT_APP_DIR}/"+self.path).exists():
            self.path = f'{REACT_APP_DIR}/' + self.path
        else:
            self.path = f'{REACT_APP_DIR}/index.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

if __name__ == "__main__":
    server_address = ('127.0.0.1', PORT)
    handler_object = ReactRequestHandler
    react_server = http.server.ThreadingHTTPServer(server_address, handler_object)
    try:
        react_server.serve_forever()
    except KeyboardInterrupt as kie:
        print(f'\nCaught CTRL-C: {kie}')
    except Exception as ex:
        print(f'\nCaught exception {ex}')
        traceback.print_exc()
    finally:
        react_server.shutdown()
        react_server.server_close()
        print(f'\nServerSocket closed: {react_server}')
