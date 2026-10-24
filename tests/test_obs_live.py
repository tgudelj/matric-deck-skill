"""Exercise discovery over real loopback WebSockets using synthetic OBS data only."""
import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "skills/matric-decks/scripts/obs_live.py"
spec = importlib.util.spec_from_file_location("obs_live", SCRIPT)
obs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(obs)


def frame(payload, opcode=1, final=True):
    header = bytes([(0x80 if final else 0) | opcode])
    if len(payload) < 126:
        return header + bytes([len(payload)]) + payload
    if len(payload) <= 65535:
        return header + bytes([126]) + struct.pack("!H", len(payload)) + payload
    return header + bytes([127]) + struct.pack("!Q", len(payload)) + payload


def wire_json(value):
    return frame(json.dumps(value, ensure_ascii=False).encode())


def exact(sock, size):
    data = bytearray()
    while len(data) < size:
        part = sock.recv(size - len(data))
        if not part:
            raise EOFError()
        data.extend(part)
    return bytes(data)


def client_frame(sock):
    first, second = exact(sock, 2)
    if not second & 0x80:
        raise AssertionError("Client frames must be masked")
    size = second & 127
    if size == 126:
        size = struct.unpack("!H", exact(sock, 2))[0]
    elif size == 127:
        size = struct.unpack("!Q", exact(sock, 8))[0]
    mask = exact(sock, 4)
    payload = exact(sock, size)
    return first & 15, bytes(v ^ mask[i % 4] for i, v in enumerate(payload))


def scene_item(name, item_id, kind=None, group=False):
    return {"sourceName": name, "sourceUuid": "uuid-" + name, "sceneItemId": item_id,
            "sceneItemIndex": item_id, "sceneItemEnabled": True, "sceneItemLocked": False,
            "inputKind": kind, "isGroup": group,
            "sourceType": "OBS_SOURCE_TYPE_SCENE" if kind is None else "OBS_SOURCE_TYPE_INPUT",
            "sceneItemTransform": {"privateFixture": "not-for-report"}}


class FakeOBS:
    """One connection per instance; verify protocol envelopes, auth and every request."""

    def __init__(self, password=None, missing=(), fail=None, changed=False, mode=None, studio=True):
        self.password = password
        self.available = obs.READ_REQUESTS - set(missing)
        self.fail = fail or {}
        self.changed = changed
        self.mode = mode
        self.studio = studio
        self.requests = []
        self.identify = None
        self.error = None
        self.collection_reads = 0
        self.pongs = []

    def __enter__(self):
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(1)
        self.listener.settimeout(3)
        self.url = "ws://127.0.0.1:" + str(self.listener.getsockname()[1])
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.thread.join(4)
        self.listener.close()
        if self.thread.is_alive():
            raise AssertionError("Synthetic OBS server did not stop")
        if self.error:
            raise self.error

    def run(self):
        try:
            with self.listener.accept()[0] as sock:
                sock.settimeout(2)
                header = bytearray()
                while b"\r\n\r\n" not in header:
                    header.extend(exact(sock, 1))
                headers = dict(line.split(": ", 1) for line in header.decode().split("\r\n")[1:] if ": " in line)
                if headers.get("Sec-WebSocket-Protocol") != "obswebsocket.json":
                    raise AssertionError("Expected JSON subprotocol")
                accept = base64.b64encode(hashlib.sha1((headers["Sec-WebSocket-Key"] + obs.WS_GUID).encode()).digest()).decode()
                if self.mode == "bad_upgrade":
                    accept = "invalid"
                upgrade = ("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: keep-alive, Upgrade\r\n"
                           f"Sec-WebSocket-Accept: {accept}\r\nSec-WebSocket-Protocol: obswebsocket.json\r\n\r\n").encode()
                hello = {"op": 0, "d": {"rpcVersion": 1, "obsWebSocketVersion": "5.5.0"}}
                if self.password is not None:
                    hello["d"]["authentication"] = {"salt": "synthetic-salt", "challenge": "synthetic-challenge"}
                # Hello may arrive in the same TCP read as the upgrade headers.
                sock.sendall(upgrade + wire_json(hello))
                if self.mode == "bad_upgrade":
                    return
                opcode, payload = client_frame(sock)
                if opcode == 8:  # Missing password: client closes without sending Identify.
                    return
                message = json.loads(payload)
                self.identify = message
                if message["op"] != 1 or message["d"].get("eventSubscriptions") != 0:
                    raise AssertionError("Unexpected Identify/subscriptions")
                if self.password is not None:
                    expected = obs.authentication(self.password, "synthetic-salt", "synthetic-challenge")
                    if message["d"].get("authentication") != expected:
                        sock.sendall(frame(struct.pack("!H", 4009) + b"do-not-copy-server-reason", 8))
                        return
                sock.sendall(wire_json({"op": 2, "d": {"negotiatedRpcVersion": 1}}))
                while True:
                    opcode, payload = client_frame(sock)
                    if opcode == 8:
                        return
                    if opcode == 10:
                        self.pongs.append(payload)
                        continue
                    message = json.loads(payload)
                    if message["op"] != 6:
                        raise AssertionError("Only individual requests are allowed")
                    data = message["d"]
                    request = data["requestType"]
                    if request not in self.available:
                        raise AssertionError("Unavailable or mutating request sent: " + request)
                    self.requests.append((request, data.get("requestData", {})))
                    if self.mode == "timeout":
                        time.sleep(0.15)
                        return
                    if self.mode == "disconnect":
                        return
                    if self.mode == "masked_server":
                        sock.sendall(b"\x81\x80")
                        return
                    if self.mode == "oversized":
                        sock.sendall(b"\x81\x7f" + struct.pack("!Q", obs.MAX_MESSAGE + 1))
                        return
                    if self.mode == "bad_json":
                        sock.sendall(frame(b'{"op":NaN,"d":{}}'))
                        return
                    if self.mode == "bad_fragment":
                        sock.sendall(frame(b"{}", opcode=0))
                        return
                    if self.mode == "bad_control":
                        sock.sendall(frame(b"x", opcode=9, final=False))
                        return
                    result = self.response(request, data.get("requestData", {}))
                    code = self.fail.get(request)
                    if request == "GetInputMute" and data["requestData"]["inputName"] != "Mic":
                        code = 604
                    response = {"op": 7, "d": {"requestType": request, "requestId": data["requestId"],
                                "requestStatus": {"result": code is None, "code": code or 100}, "responseData": result}}
                    if code:
                        response["d"]["requestStatus"]["comment"] = "private-server-comment"
                    if self.mode == "mismatch":
                        response["d"]["requestId"] = "wrong-id"
                    if self.mode == "wrong_type":
                        response["d"]["requestType"] = "WrongRequest"
                    if self.mode == "large" and request == "GetVersion":
                        response["d"]["responseData"]["ignored"] = "X" * 70000
                    encoded = json.dumps(response, ensure_ascii=False).encode()
                    # Fragment data with an interleaved ping; pong is read before the next request.
                    sock.sendall(frame(encoded[:11], final=False) + frame(b"probe", 9) + frame(encoded[11:], 0))
        except (EOFError, ConnectionResetError, BrokenPipeError):
            pass
        except BaseException as error:
            self.error = error

    def response(self, request, data):
        if request == "GetVersion":
            return {"obsVersion": "30.synthetic", "obsWebSocketVersion": "5.5.0", "rpcVersion": 1,
                    "availableRequests": sorted(self.available) + ["SetCurrentProgramScene", "StartStream"]}
        if request == "GetSceneCollectionList":
            self.collection_reads += 1
            return {"currentSceneCollectionName": "Changed" if self.changed and self.collection_reads > 1 else "Synthetic",
                    "sceneCollections": ["Synthetic", "Inactive"]}
        if request == "GetSceneList":
            return {"currentProgramSceneName": "Main", "currentPreviewSceneName": "Holding" if self.studio else None,
                    "scenes": [{"sceneName": "Main", "sceneUuid": "uuid-Main", "sceneIndex": 1},
                               {"sceneName": "Holding", "sceneUuid": "uuid-Holding", "sceneIndex": 0}]}
        if request == "GetGroupList":
            return {"groups": ["Group", "Unused"]}
        if request == "GetInputList":
            return {"inputs": [{"inputName": "Mic", "inputUuid": "uuid-Mic", "inputKind": "audio"},
                               {"inputName": "Cam", "inputKind": "video"},
                               {"inputName": "Café", "inputKind": "browser"}]}
        if request == "GetSpecialInputs":
            return {"desktop1": None, "desktop2": None, "mic1": "Mic", "mic2": None, "mic3": None, "mic4": None}
        if request == "GetSceneItemList":
            if data["sceneName"] == "Main":
                return {"sceneItems": [scene_item("Mic", 1, "audio"), scene_item("Mic", 2, "audio"),
                                       scene_item("Group", 3, group=True), scene_item("Holding", 4)]}
            return {"sceneItems": [scene_item("Main", 5)]}
        if request == "GetGroupSceneItemList":
            return {"sceneItems": [scene_item("Cam", 10, "video")] if data["sceneName"] == "Group" else []}
        if request == "GetSourceFilterList":
            return {"filters": [{"filterName": "Clean", "filterKind": "noise_suppress_filter", "filterEnabled": True,
                                  "filterIndex": 0, "filterSettings": {"private": "not-for-report"}}]}
        if request == "GetInputMute":
            return {"inputMuted": True}
        if request == "GetInputVolume":
            return {"inputVolumeMul": 0.5, "inputVolumeDb": -6.02}
        if request == "GetSceneTransitionList":
            return {"currentSceneTransitionName": "Fade", "transitions": [{"transitionName": "Fade", "transitionKind": "fade_transition"}]}
        if request == "GetStudioModeEnabled":
            return {"studioModeEnabled": self.studio}
        if request == "GetHotkeyList":
            return {"hotkeys": ["OBSBasic.StartStreaming"]}
        if request in {"GetStreamStatus", "GetRecordStatus", "GetVirtualCamStatus", "GetReplayBufferStatus"}:
            return {"outputActive": False, "outputPaused": False, "outputPath": "private-path"}
        raise AssertionError("Missing synthetic handler: " + request)


class LiveDiscoveryTests(unittest.TestCase):
    def test_authenticated_snapshot_preserves_graph_and_exact_names(self):
        with FakeOBS(password="fixture-password") as server:
            report = obs.discover(server.url, "fixture-password")
        self.assertTrue(report["complete"], report["warnings"])
        self.assertTrue(report["live"])
        self.assertEqual(report["scene_collections"], ["Synthetic", "Inactive"])
        self.assertEqual(len(report["collections"]), 1)
        collection = report["collections"][0]
        self.assertEqual(collection["scene_order"], ["Main", "Holding"])
        self.assertEqual(collection["special_inputs"]["mic1"], "Mic")
        self.assertEqual(collection["current_preview_scene"], "Holding")
        containers = {v["name"]: v for v in collection["containers"]}
        self.assertEqual(len(containers), 4)  # Graph cycles don't repeat queries.
        self.assertEqual([v["item_id"] for v in containers["Main"]["items"][:2]], [1, 2])
        self.assertEqual(containers["Group"]["items"][0]["name"], "Cam")
        sources = {v["name"]: v for v in collection["sources"]}
        self.assertIn("Café", sources)
        self.assertTrue(sources["Mic"]["audio"]["inputMuted"])
        self.assertEqual(sources["Mic"]["audio"]["inputVolumeMul"], 0.5)
        self.assertNotIn("audio", sources["Cam"])
        self.assertEqual(sources["Cam"]["filters"][0]["filterName"], "Clean")
        self.assertEqual(collection["hotkey_identifiers"], ["OBSBasic.StartStreaming"])
        encoded = json.dumps(report)
        for excluded in ("fixture-password", "synthetic-salt", "synthetic-challenge", "authentication", "not-for-report", "private-path", server.url):
            self.assertNotIn(excluded, encoded)
        self.assertTrue(server.pongs)
        self.assertTrue(all(name in obs.READ_REQUESTS for name, _ in server.requests))
        self.assertFalse(any(name == "GetInputVolume" and data["inputName"] == "Cam" for name, data in server.requests))

    def test_no_auth_and_64_bit_frames(self):
        with FakeOBS(mode="large", studio=False) as server:
            report = obs.discover(server.url)
        self.assertNotIn("authentication", server.identify["d"])
        self.assertFalse(report["collections"][0]["studio_mode_enabled"])
        self.assertIsNone(report["collections"][0]["current_preview_scene"])

    def test_missing_capabilities_and_request_errors_are_partial(self):
        with FakeOBS(missing=("GetHotkeyList",), fail={"GetSourceFilterList": 600}) as server:
            report = obs.discover(server.url)
        self.assertFalse(report["complete"])
        self.assertIsNone(report["collections"][0]["hotkey_identifiers"])
        self.assertTrue(all(v["filters"] is None for v in report["collections"][0]["sources"]))
        self.assertNotIn("GetHotkeyList", [name for name, _ in server.requests])
        self.assertNotIn("private-server-comment", json.dumps(report))

    def test_required_requests_and_collection_change_fail(self):
        for options in ({"missing": ("GetSceneList",)}, {"fail": {"GetInputList": 600}}, {"changed": True}):
            with self.subTest(options=options), FakeOBS(**options) as server:
                with self.assertRaises(obs.DiscoveryError):
                    obs.discover(server.url)

    def test_credentials_missing_or_wrong(self):
        for password in (None, "wrong-password"):
            with self.subTest(password=password), FakeOBS(password="required-password") as server:
                with self.assertRaisesRegex(obs.DiscoveryError, "authentication") as raised:
                    obs.discover(server.url, password)
                self.assertNotIn("required-password", str(raised.exception))
                self.assertNotIn("do-not-copy", str(raised.exception))
                self.assertEqual(server.requests, [])

    def test_transport_and_response_failures(self):
        for mode in ("bad_upgrade", "disconnect", "masked_server", "oversized", "bad_json", "bad_fragment", "bad_control", "mismatch", "wrong_type"):
            with self.subTest(mode=mode), FakeOBS(mode=mode) as server:
                with self.assertRaises(obs.DiscoveryError):
                    obs.discover(server.url)

    def test_timeout(self):
        with FakeOBS(mode="timeout") as server:
            with self.assertRaises(TimeoutError):
                obs.discover(server.url, timeout=0.05)

    def test_authentication_with_independently_computed_digest(self):
        # Protocol sample inputs; expected digest independently checked with .NET SHA256.
        self.assertEqual(obs.authentication("supersecretpassword", "lM1GncleQOaCu9lT1yeUZhFYnqhsLLP1G5lAGo3ixaI=",
                                            "+IxH4CnCiqpX1rM9scsNynZzbOe4KhDeYcTNS3PDaeY="),
                         "1Ct943GAT+6YQUUX47Ia/ncufilbe6+oD6lY+5kaCu4=")

    def test_snapshot_deadline_is_not_reset_by_new_requests(self):
        with mock.patch.object(obs.time, "monotonic", return_value=100.0) as now:
            ws = obs.WebSocket.__new__(obs.WebSocket)
            ws.timeout, ws.total_deadline = 5, 102
            ws.begin()
            self.assertEqual(ws.remaining(), 2)
            now.return_value = 101.5
            ws.begin()
            self.assertEqual(ws.remaining(), 0.5)
            now.return_value = 102
            with self.assertRaises(TimeoutError):
                ws.remaining()

    def test_mutations_blocked_before_send(self):
        with FakeOBS() as server:
            ws = obs.WebSocket(server.url)
            try:
                client = obs.OBSClient(ws)
                for request in ("SetCurrentProgramScene", "StartStream", "GetStreamServiceSettings", "CallVendorRequest"):
                    with self.assertRaisesRegex(obs.DiscoveryError, "outside read-only"):
                        client.request(request)
            finally:
                ws.close()
        self.assertEqual([name for name, _ in server.requests], ["GetVersion"])

    def test_invalid_endpoints_and_timeouts_fail_before_network(self):
        with mock.patch.object(obs.socket, "create_connection") as connect:
            for url in ("http://localhost:4455", "ws://user:secret@localhost:4455", "ws://localhost:4455/?secret=x", "ws://localhost/#secret", "ws://localhost:bad", "ws://localhost/\r\n"):
                with self.subTest(url=url), self.assertRaises(obs.DiscoveryError):
                    obs.WebSocket(url)
            for timeout in (0, -1, float("nan"), float("inf")):
                with self.assertRaises(obs.DiscoveryError):
                    obs.WebSocket("ws://localhost:4455", timeout=timeout)
            connect.assert_not_called()

    def test_tls_uses_default_verification_and_closes_on_failure(self):
        connection = mock.Mock()
        with mock.patch.object(obs.socket, "create_connection", return_value=connection), mock.patch.object(obs.ssl, "create_default_context") as context:
            context.return_value.wrap_socket.side_effect = obs.ssl.SSLError("synthetic failure")
            with self.assertRaises(obs.ssl.SSLError):
                obs.WebSocket("wss://obs.example:4455")
            context.return_value.wrap_socket.assert_called_once_with(connection, server_hostname="obs.example")
            connection.close.assert_called_once()

    def test_cli_password_environment_output_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "inventory.json"
            with FakeOBS(password="cli-secret") as server:
                result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--url", server.url,
                                         "--password-env", "SYNTH_OBS_PASSWORD", "--output", str(output)],
                                        env={**os.environ, "SYNTH_OBS_PASSWORD": "cli-secret"}, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            report = output.read_text(encoding="utf-8")
            self.assertNotIn("cli-secret", report)
            self.assertTrue(json.loads(report)["live"])
            with mock.patch.object(obs, "discover") as discover, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    obs.main(["--output", str(output)])
                discover.assert_not_called()
            self.assertEqual(output.read_text(encoding="utf-8"), report)


if __name__ == "__main__":
    unittest.main()
