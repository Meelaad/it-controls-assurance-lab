import json
import os
import shutil
import subprocess
import tempfile

GRAPH = "https://graph.microsoft.com/v1.0"


def az_cmd():
    az = shutil.which("az")
    if not az:
        raise SystemExit("az cli not found, install it and run az login first")
    # az.cmd runs through cmd.exe, which splits URLs on & and eats the quotes in JSON.
    # The MSI install ships its own python so call that instead
    if az.lower().endswith(".cmd"):
        py = os.path.join(os.path.dirname(os.path.dirname(az)), "python.exe")
        if os.path.exists(py):
            return [py, "-IBm", "azure.cli"]
    return [az]


def call(method, path, body=None):
    cmd = az_cmd() + ["rest", "--method", method, "--url", GRAPH + path]
    body_file = None
    if body is not None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(body, f)
            body_file = f.name
        cmd += ["--body", "@" + body_file, "--headers", "Content-Type=application/json"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    finally:
        if body_file:
            os.remove(body_file)
    if out.returncode != 0:
        if "Not Found" in out.stderr or "Request_ResourceNotFound" in out.stderr:
            return None
        # signInActivity and the MFA report need P1/P2
        if "NonPremiumTenant" in out.stderr:
            return None
        raise SystemExit(f"az rest {method} {path} failed: {out.stderr.strip()[:300]}")
    return json.loads(out.stdout) if out.stdout.strip() else {}


def get(path):
    return call("get", path)


def post(path, body):
    return call("post", path, body)


def patch(path, body):
    return call("patch", path, body)


def get_all(path):
    items, data = [], get(path)
    while data:
        items += data.get("value", [])
        nxt = data.get("@odata.nextLink")
        data = get(nxt.replace(GRAPH, "")) if nxt else None
    return items
