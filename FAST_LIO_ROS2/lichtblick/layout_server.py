#!/usr/bin/env python3
"""Serve Lichtblick layout files over HTTP with CORS enabled.

Lichtblick imports a layout from a URL (lichtblick://open?layoutUrl=...) using
fetch() inside the Electron renderer, so the response must carry an
Access-Control-Allow-Origin header. Only Python standard library is used.
"""

import argparse
import functools
import http.server


class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format, *args):
        pass  # keep launch output clean


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--directory", required=True,
                        help="Directory containing the layout JSON files")
    args = parser.parse_args()

    handler = functools.partial(CORSRequestHandler, directory=args.directory)
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
