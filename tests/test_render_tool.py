import importlib.util
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path("skills/render-tool/scripts/render_tool.py")
spec = importlib.util.spec_from_file_location("render_tool", SCRIPT)
render_tool = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(render_tool)


class Handler(BaseHTTPRequestHandler):
    requests = []

    def do_GET(self):
        self.respond()

    def do_POST(self):
        self.respond()

    def respond(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length)) if length else None
        self.__class__.requests.append((self.command, self.path, dict(self.headers), body))
        payload = {"id": "job-123", "status": "queued"}
        encoded = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, *_args):
        pass


class RenderToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()

    def setUp(self):
        Handler.requests.clear()
        self.env = patch.dict(os.environ, {
            "RENDER_API_URL": f"http://127.0.0.1:{self.server.server_port}",
            "AGENT_API_KEY": "agent-secret",
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_image_create_uses_safe_defaults_and_auth(self):
        args = render_tool.parser().parse_args([
            "create", "--prompt", "fox astronaut", "--user-id", "telegram:42",
            "--source-platform", "telegram", "--source-channel-id", "42",
        ])
        result = render_tool.create(args)
        method, path, headers, body = Handler.requests[-1]
        self.assertEqual(result["id"], "job-123")
        self.assertEqual((method, path), ("POST", "/v1/jobs"))
        self.assertEqual(headers["Authorization"], "Bearer agent-secret")
        self.assertEqual(body["workflow_name"], "flux-image")
        self.assertEqual(body["preset"], {"quality": "draft", "aspect_ratio": "16:9"})
        self.assertEqual(body["negative_prompt"], "")
        self.assertEqual(body["parameters"], {})

    def test_video_create_sets_frames_and_optional_seed(self):
        args = render_tool.parser().parse_args([
            "create", "--prompt", "fox running", "--output-type", "video",
            "--seed", "123", "--user-id", "telegram:42",
            "--source-platform", "telegram", "--source-channel-id", "42",
        ])
        render_tool.create(args)
        body = Handler.requests[-1][3]
        self.assertEqual(body["workflow_name"], "wan22-video")
        self.assertEqual(body["parameters"], {"frames": 121, "seed": 123})

    def test_list_encodes_stable_user_and_status(self):
        render_tool.request("GET", "/v1/jobs?" + render_tool.urllib.parse.urlencode({
            "user_id": "telegram:42", "status": "running"
        }))
        self.assertEqual(Handler.requests[-1][1], "/v1/jobs?user_id=telegram%3A42&status=running")

    def test_missing_key_is_reported_without_network_request(self):
        with patch.dict(os.environ, {"AGENT_API_KEY": ""}):
            with self.assertRaisesRegex(render_tool.RenderAPIError, "not configured"):
                render_tool.request("GET", "/v1/jobs/job-1")
        self.assertEqual(Handler.requests, [])


if __name__ == "__main__":
    unittest.main()
