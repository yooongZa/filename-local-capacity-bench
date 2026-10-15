#!/usr/bin/env python3
"""TEST ONLY: local HTTP fixture, no model or accelerator. Never use for capacity claims."""
import argparse
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

if "--help" in sys.argv:
    print("--fit --no-context-shift --image-max-tokens --chat-template-kwargs")
    sys.exit(0)

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--port", type=int, required=True)
parser.add_argument("-c", type=int, default=4096)
parser.add_argument("-np", type=int, default=1)
args, _ = parser.parse_known_args()
active = 0
lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        try:
            self.wfile.write(json.dumps(body).encode())
        except BrokenPipeError:
            pass

    def do_GET(self):
        if self.path == "/slots":
            with lock:
                count = active
            self.send([{"n_ctx": args.c // args.np, "is_processing": i < count} for i in range(args.np)])
        elif self.path == "/props":
            self.send({"total_slots": args.np, "default_generation_settings": {"n_ctx": args.c // args.np}})
        else:
            self.send({"status": "ok"})

    def do_POST(self):
        global active
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/tokenize":
            self.send({"tokens": list(range(len(body["content"])))})
            return
        with lock:
            active += 1
        try:
            time.sleep(.05)
            items = body["messages"][0]["content"]
            raw = json.dumps({"keywords": ["테스트"], "reason": "HTTP 테스트 응답", "place_name": None}, ensure_ascii=False)
            self.send({"choices": [{"message": {"content": raw}, "finish_reason": "stop"}],
                       "usage": {"prompt_tokens": len(items[-1]["text"]) + 100, "completion_tokens": 30},
                       "test_message_count": len(body["messages"]),
                       "test_image_count": len(items) - 1, "test_text_last": items[-1]["type"] == "text"})
        finally:
            with lock:
                active -= 1


ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
