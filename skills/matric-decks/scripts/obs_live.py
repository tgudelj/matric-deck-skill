#!/usr/bin/env python3
"""Take a read-only OBS WebSocket 5 JSON snapshot using Python's standard library."""
import argparse
import base64
from collections import deque
from datetime import datetime, timezone
import getpass
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import ssl
import struct
import sys
import time
from urllib.parse import urlsplit


READ_REQUESTS = frozenset({
    "GetVersion", "GetSceneCollectionList", "GetSceneList", "GetGroupList",
    "GetSceneItemList", "GetGroupSceneItemList", "GetInputList", "GetSpecialInputs",
    "GetSourceFilterList", "GetInputMute", "GetInputVolume",
    "GetSceneTransitionList", "GetStudioModeEnabled", "GetHotkeyList",
    "GetStreamStatus", "GetRecordStatus", "GetVirtualCamStatus", "GetReplayBufferStatus",
})
MAX_MESSAGE = 8 * 1024 * 1024
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class DiscoveryError(ValueError):
    """A connection, protocol or snapshot cannot be used for discovery."""


class RequestError(DiscoveryError):
    """OBS rejected a read request; exclude arbitrary server comments from diagnostics."""

    def __init__(self, request, code):
        self.code = code
        super().__init__(f"{request} failed (OBS status {code})")


def authentication(password, salt, challenge):
    """Produce the v5 challenge response without retaining credentials in the inventory."""
    secret = base64.b64encode(hashlib.sha256((password + salt).encode()).digest()).decode()
    return base64.b64encode(hashlib.sha256((secret + challenge).encode()).digest()).decode()


class WebSocket:
    """Small RFC 6455 JSON client: TLS verification, masking, fragmentation and ping/pong."""

    def __init__(self, url, timeout=5, snapshot_timeout=60):
        if not all(math.isfinite(v) and v > 0 for v in (timeout, snapshot_timeout)):
            raise DiscoveryError("Timeouts must be positive finite seconds")
        self.timeout = timeout
        self.total_deadline = time.monotonic() + snapshot_timeout
        self.sock = None
        self.upgraded = False
        self.buffer = bytearray()
        self.begin()
        try:
            parts = urlsplit(url)
            if (parts.scheme not in ("ws", "wss") or not parts.hostname or
                    parts.username is not None or parts.password is not None or parts.query or parts.fragment or
                    any(ord(c) < 33 or ord(c) > 126 for c in url)):
                raise ValueError()
            port = parts.port or (443 if parts.scheme == "wss" else 80)
        except ValueError:
            raise DiscoveryError("Use a ws:// or wss:// URL without credentials, query or fragment") from None
        try:
            self.sock = socket.create_connection((parts.hostname, port), self.remaining())
            if parts.scheme == "wss":
                self.sock.settimeout(self.remaining())
                self.sock = ssl.create_default_context().wrap_socket(self.sock, server_hostname=parts.hostname)
            host = f"[{parts.hostname}]" if ":" in parts.hostname else parts.hostname
            key = base64.b64encode(os.urandom(16)).decode()
            upgrade = (f"GET {parts.path or '/'} HTTP/1.1\r\nHost: {host}:{port}\r\n"
                       "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                       f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n"
                       "Sec-WebSocket-Protocol: obswebsocket.json\r\n\r\n")
            self.send_bytes(upgrade.encode("ascii"))
            while b"\r\n\r\n" not in self.buffer:
                self.sock.settimeout(self.remaining())
                data = self.sock.recv(4096)
                if not data:
                    raise DiscoveryError("OBS disconnected during WebSocket upgrade")
                self.buffer.extend(data)
                if len(self.buffer) > 65536:
                    raise DiscoveryError("WebSocket upgrade headers are too large")
            raw, tail = bytes(self.buffer).split(b"\r\n\r\n", 1)
            self.buffer = bytearray(tail)
            lines = raw.decode("iso-8859-1").split("\r\n")
            headers = {}
            for line in lines[1:]:
                name, sep, value = line.partition(":")
                if not sep or name.lower() in headers:
                    raise DiscoveryError("Malformed WebSocket upgrade headers")
                headers[name.lower()] = value.strip()
            accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()
            if (lines[0].split()[:2] != ["HTTP/1.1", "101"] or
                    headers.get("upgrade", "").lower() != "websocket" or
                    "upgrade" not in [v.strip().lower() for v in headers.get("connection", "").split(",")] or
                    headers.get("sec-websocket-accept") != accept or
                    headers.get("sec-websocket-protocol", "obswebsocket.json") != "obswebsocket.json" or
                    "sec-websocket-extensions" in headers):
                raise DiscoveryError("OBS did not accept the WebSocket JSON upgrade; check the endpoint/port")
            self.upgraded = True
        except BaseException:
            self.close()
            raise

    def begin(self):
        """Set one deadline for a whole handshake or request, including control frames."""
        self.deadline = min(self.total_deadline, time.monotonic() + self.timeout)

    def remaining(self):
        """Return the remaining operation budget, preventing ping/fragment timeout resets."""
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("OBS discovery timed out")
        return remaining

    def send_bytes(self, data):
        self.sock.settimeout(self.remaining())
        self.sock.sendall(data)

    def read(self, size):
        """Read exactly size bytes, keeping any coalesced handshake/frame data."""
        while len(self.buffer) < size:
            self.sock.settimeout(self.remaining())
            data = self.sock.recv(min(65536, size - len(self.buffer)))
            if not data:
                raise DiscoveryError("OBS disconnected before discovery completed")
            self.buffer.extend(data)
        data = bytes(self.buffer[:size])
        del self.buffer[:size]
        return data

    def send_frame(self, opcode, data):
        """Mask every outgoing client frame with fresh random bytes."""
        size = len(data)
        if size > MAX_MESSAGE:
            raise DiscoveryError("Outgoing WebSocket message is too large")
        header = bytes([0x80 | opcode])
        if size < 126:
            header += bytes([0x80 | size])
        elif size <= 65535:
            header += bytes([0xFE]) + struct.pack("!H", size)
        else:
            header += bytes([0xFF]) + struct.pack("!Q", size)
        mask = os.urandom(4)
        self.send_bytes(header + mask + bytes(v ^ mask[i % 4] for i, v in enumerate(data)))

    def send_json(self, value):
        self.send_frame(1, json.dumps(value, ensure_ascii=False, allow_nan=False).encode())

    def receive_json(self):
        """Assemble one text message; service ping/pong and reject malformed frames."""
        message = bytearray()
        started = False
        while True:
            self.remaining()
            first, second = self.read(2)
            final, opcode = bool(first & 0x80), first & 15
            if first & 0x70 or second & 0x80:
                raise DiscoveryError("Unsupported WebSocket flags or masked server frame")
            size = second & 127
            if size == 126:
                size = struct.unpack("!H", self.read(2))[0]
                if size < 126:
                    raise DiscoveryError("Invalid WebSocket frame length")
            elif size == 127:
                size = struct.unpack("!Q", self.read(8))[0]
                if size <= 65535 or size >> 63:
                    raise DiscoveryError("Invalid WebSocket frame length")
            if opcode >= 8:
                if not final or size > 125:
                    raise DiscoveryError("Invalid WebSocket control frame")
            elif size + len(message) > MAX_MESSAGE:
                raise DiscoveryError("OBS WebSocket message exceeds the 8 MiB limit")
            payload = self.read(size)
            if opcode == 8:
                if len(payload) == 1:
                    raise DiscoveryError("Invalid WebSocket close frame")
                code = struct.unpack("!H", payload[:2])[0] if payload else None
                if code == 4009:
                    raise DiscoveryError("OBS authentication failed; check the WebSocket password")
                raise DiscoveryError(f"OBS closed the WebSocket (code {code})")
            if opcode == 9:
                self.send_frame(10, payload)
                continue
            if opcode == 10:
                continue
            if opcode not in (0, 1) or (opcode == 0) != started:
                raise DiscoveryError("Expected a WebSocket text message or continuation")
            started = True
            message.extend(payload)
            if final:
                try:
                    value = json.loads(message.decode("utf-8"), parse_constant=_invalid_constant)
                except (ValueError, UnicodeError, RecursionError):
                    raise DiscoveryError("OBS sent invalid UTF-8 JSON") from None
                if not isinstance(value, dict) or not isinstance(value.get("d"), dict):
                    raise DiscoveryError("OBS sent an invalid message envelope")
                return value

    def close(self):
        """Close resources even when authentication or discovery fails."""
        if self.sock is not None:
            try:
                if self.upgraded:
                    self.begin()
                    self.send_frame(8, struct.pack("!H", 1000))
            except (OSError, ValueError):
                pass
            self.sock.close()
            self.sock = None


def _invalid_constant(value):
    raise ValueError("Non-finite JSON number")


class OBSClient:
    """OBS RPC 1 client restricted to the exact discovery request allowlist."""

    def __init__(self, websocket, password=None):
        self.ws = websocket
        self.available = None
        self.requests = 0
        self.ws.begin()
        hello = self.ws.receive_json()
        if hello.get("op") != 0 or hello["d"].get("rpcVersion", 0) < 1:
            raise DiscoveryError("Expected OBS WebSocket 5 Hello with RPC 1 support")
        identify = {"rpcVersion": 1, "eventSubscriptions": 0}
        auth = hello["d"].get("authentication")
        if auth is not None:
            if password is None:
                raise DiscoveryError("OBS requires authentication; set OBS_WEBSOCKET_PASSWORD or use --ask-password")
            if not isinstance(auth, dict) or not all(isinstance(auth.get(k), str) for k in ("salt", "challenge")):
                raise DiscoveryError("Malformed OBS authentication challenge")
            identify["authentication"] = authentication(password, auth["salt"], auth["challenge"])
        self.ws.send_json({"op": 1, "d": identify})
        identified = self.ws.receive_json()
        if identified.get("op") != 2 or identified["d"].get("negotiatedRpcVersion") != 1:
            raise DiscoveryError("OBS did not identify the client using RPC 1")
        self.version = self.request("GetVersion")
        available = self.version.get("availableRequests")
        if not isinstance(available, list) or not all(isinstance(v, str) for v in available):
            raise DiscoveryError("GetVersion did not report availableRequests")
        self.available = frozenset(available)

    def request(self, request, data=None):
        """Check capability, correlate the response, and never send mutations or batches."""
        if request not in READ_REQUESTS:
            raise DiscoveryError(f"Request is outside read-only discovery: {request}")
        if self.available is not None and request not in self.available:
            raise RequestError(request, "unavailable")
        self.requests += 1
        if self.requests > 10000:
            raise DiscoveryError("OBS discovery exceeded the 10000 request limit")
        request_id = str(self.requests)
        self.ws.begin()
        self.ws.send_json({"op": 6, "d": {"requestType": request, "requestId": request_id, "requestData": data or {}}})
        while True:
            response = self.ws.receive_json()
            if response.get("op") == 5:
                continue
            body = response["d"]
            if response.get("op") != 7 or body.get("requestId") != request_id or body.get("requestType") != request:
                raise DiscoveryError("Unexpected or mismatched OBS request response")
            status = body.get("requestStatus")
            if not isinstance(status, dict) or type(status.get("result")) is not bool:
                raise DiscoveryError("Malformed OBS request status")
            if not status["result"]:
                code = status.get("code")
                raise RequestError(request, code if type(code) is int else "unknown")
            result = body.get("responseData", {})
            if not isinstance(result, dict):
                raise DiscoveryError("Malformed OBS response data")
            return result


def fields(value, *names):
    """Keep only requested metadata; never copy settings or protocol credentials."""
    return {name: value[name] for name in names if name in value}


def array(data, name):
    value = data.get(name)
    if not isinstance(value, list):
        raise DiscoveryError(f"OBS response is missing the {name} array")
    return value


def snapshot(client):
    """Inventory the active collection graph and current state without changing OBS."""
    started = datetime.now(timezone.utc).isoformat()
    warnings = []

    def optional(request, data=None, ignore_codes=()):
        try:
            return client.request(request, data)
        except RequestError as error:
            if error.code not in ignore_codes:
                warning = str(error)
                if data:
                    warning += " for " + json.dumps(data, ensure_ascii=False)
                if warning not in warnings:
                    warnings.append(warning)
            return None

    collections = client.request("GetSceneCollectionList")
    collection_name = collections.get("currentSceneCollectionName")
    if not isinstance(collection_name, str):
        raise DiscoveryError("OBS did not identify the active scene collection")
    names = array(collections, "sceneCollections")
    scenes = client.request("GetSceneList")
    inputs = array(client.request("GetInputList"), "inputs")
    sources = {}
    containers = []
    pending = deque()
    visited = set()

    def source(name, uuid=None, kind=None):
        if not isinstance(name, str):
            raise DiscoveryError("OBS reported a source without a name")
        if name not in sources:
            sources[name] = {"name": name, "uuid": uuid, "kind": kind, "filters": None}
        else:
            if uuid is not None:
                sources[name]["uuid"] = uuid
            if kind is not None:
                sources[name]["kind"] = kind
        return sources[name]

    scene_list = array(scenes, "scenes")
    for scene in scene_list:
        name = scene["sceneName"]
        source(name, scene.get("sceneUuid"), "scene")
        pending.append((name, "scene"))
    groups = optional("GetGroupList")
    if groups is not None:
        for name in array(groups, "groups"):
            source(name, kind="group")
            pending.append((name, "group"))
    for item in inputs:
        source(item["inputName"], item.get("inputUuid"), item.get("inputKind"))
    special = optional("GetSpecialInputs")
    special = fields(special, "desktop1", "desktop2", "mic1", "mic2", "mic3", "mic4") if special is not None else None
    special_names = [name for name in (special or {}).values() if isinstance(name, str)]
    for name in special_names:
        source(name)

    while pending:
        name, kind = pending.popleft()
        if name in visited:
            continue
        visited.add(name)
        request = "GetGroupSceneItemList" if kind == "group" else "GetSceneItemList"
        data = optional(request, {"sceneName": name})
        container = {"name": name, "uuid": sources[name]["uuid"], "kind": kind, "items": None}
        containers.append(container)
        if data is None:
            continue
        container["items"] = []
        for item in array(data, "sceneItems"):
            child_name = item["sourceName"]
            child_kind = "group" if item.get("isGroup") else item.get("inputKind")
            if not child_kind and item.get("sourceType") == "OBS_SOURCE_TYPE_SCENE":
                child_kind = "scene"
            source(child_name, item.get("sourceUuid"), child_kind)
            container["items"].append({
                "name": child_name, "source_uuid": item.get("sourceUuid"), "kind": child_kind,
                "item_id": item.get("sceneItemId"), "index": item.get("sceneItemIndex"),
                "visible": item.get("sceneItemEnabled"), "locked": item.get("sceneItemLocked"),
            })
            if child_kind in ("scene", "group"):
                pending.append((child_name, child_kind))

    for name, entry in sources.items():
        result = optional("GetSourceFilterList", {"sourceName": name})
        if result is not None:
            entry["filters"] = [fields(f, "filterName", "filterKind", "filterIndex", "filterEnabled")
                                for f in array(result, "filters")]
    for name in dict.fromkeys([item["inputName"] for item in inputs] + special_names):
        # InvalidResourceState (604) is normal for inputs without audio output.
        mute = optional("GetInputMute", {"inputName": name}, ignore_codes=(604,))
        if mute is not None:
            sources[name]["audio"] = fields(mute, "inputMuted")
            volume = optional("GetInputVolume", {"inputName": name})
            if volume is not None:
                sources[name]["audio"].update(fields(volume, "inputVolumeMul", "inputVolumeDb"))

    transitions = optional("GetSceneTransitionList")
    studio = optional("GetStudioModeEnabled")
    hotkeys = optional("GetHotkeyList")
    outputs = {}
    for name, request in (("stream", "GetStreamStatus"), ("record", "GetRecordStatus"),
                          ("virtual_camera", "GetVirtualCamStatus"), ("replay_buffer", "GetReplayBufferStatus")):
        result = optional(request)
        outputs[name] = fields(result, "outputActive", "outputPaused", "outputReconnecting") if result is not None else None
    # A collection change can make otherwise valid names belong to different collections.
    end = client.request("GetSceneCollectionList")
    if end.get("currentSceneCollectionName") != collection_name:
        raise DiscoveryError("The active OBS collection changed during discovery; retry when it is stable")
    collection = {
        "collection": collection_name, "origin": "obs_websocket", "live": True,
        # OBS assigns the highest sceneIndex to the first scene in its frontend list.
        "scene_order": [item["sceneName"] for item in sorted(scene_list, key=lambda s: s.get("sceneIndex", 0), reverse=True)],
        "current_program_scene": scenes.get("currentProgramSceneName"),
        "current_preview_scene": scenes.get("currentPreviewSceneName"),
        "studio_mode_enabled": studio.get("studioModeEnabled") if studio is not None else None,
        "containers": containers, "sources": list(sources.values()), "special_inputs": special,
        "transitions": [fields(t, "transitionName", "transitionKind", "transitionUuid")
                        for t in array(transitions, "transitions")] if transitions is not None else None,
        "current_transition": transitions.get("currentSceneTransitionName") if transitions is not None else None,
        "hotkey_identifiers": array(hotkeys, "hotkeys") if hotkeys is not None else None,
    }
    return {
        "origin": "obs_websocket", "live": True, "started_at": started,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "version": fields(client.version, "obsVersion", "obsWebSocketVersion", "rpcVersion"),
        "available_requests": sorted(client.available), "scene_collections": names,
        "collections": [collection], "outputs": outputs, "complete": not warnings,
        "warnings": warnings,
        "scope": "Active collection and default canvas only. Sequential snapshot; state can change during and after discovery. Hotkey identifiers are not keyboard bindings.",
    }


def discover(url="ws://127.0.0.1:4455", password=None, timeout=5, snapshot_timeout=60):
    """Connect, authenticate, take one snapshot, and close on every exit path."""
    ws = WebSocket(url, timeout, snapshot_timeout)
    try:
        return snapshot(OBSClient(ws, password))
    finally:
        ws.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="ws://127.0.0.1:4455", help="Enabled OBS WebSocket endpoint")
    credentials = parser.add_mutually_exclusive_group()
    credentials.add_argument("--password-env", metavar="NAME", help="Read password from this environment variable (default: OBS_WEBSOCKET_PASSWORD)")
    credentials.add_argument("--ask-password", action="store_true", help="Prompt privately for the password")
    parser.add_argument("--timeout", type=float, default=5, help="Seconds per connection/request (default: 5)")
    parser.add_argument("--snapshot-timeout", type=float, default=60, help="Total snapshot budget in seconds (default: 60)")
    parser.add_argument("--output", type=Path, help="Create a new JSON report; existing files are never overwritten")
    args = parser.parse_args(argv)
    if args.output and args.output.exists():
        parser.error("Output already exists; choose a new report filename")
    if args.password_env and args.password_env not in os.environ:
        parser.error("The named password environment variable is not set")
    if args.ask_password and not sys.stdin.isatty():
        parser.error("--ask-password needs an interactive terminal; use --password-env for automation")
    password = getpass.getpass("OBS WebSocket password: ") if args.ask_password else os.environ.get(args.password_env or "OBS_WEBSOCKET_PASSWORD")
    try:
        result = discover(args.url, password, args.timeout, args.snapshot_timeout)
        text = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as output:
                output.write(text)
        else:
            print(text, end="")
        return 0
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
        # Report controlled protocol diagnostics, never raw messages, credentials or URLs.
        if isinstance(error, DiscoveryError):
            message = str(error)
        elif isinstance(error, TimeoutError):
            message = "OBS discovery timed out; check OBS and the endpoint or increase the timeout"
        elif isinstance(error, OSError):
            message = "Cannot connect/read/write discovery data; check OBS WebSocket settings, network/TLS and output path"
        else:
            message = "OBS returned malformed or unsupported discovery data"
        print("ERROR: " + message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
