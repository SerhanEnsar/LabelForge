import http.server
import os
import threading
import functools

from polyedit import download_file


def _serve(directory):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_download_writes_file_and_reports_progress(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    payload = os.urandom(300_000)
    (src / "model.pth").write_bytes(payload)
    srv = _serve(str(src))
    try:
        url = f"http://127.0.0.1:{srv.server_address[1]}/model.pth"
        dest = tmp_path / "models" / "model.pth"
        calls = []
        download_file(url, str(dest), lambda d, t: calls.append((d, t)))
    finally:
        srv.shutdown()
    assert dest.read_bytes() == payload
    assert not (tmp_path / "models" / "model.pth.part").exists()
    assert calls and calls[-1][0] == len(payload)
    assert calls[-1][1] == len(payload)
