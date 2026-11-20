import sys

import bootstrap


def test_missing_reports_only_absent_packages():
    specs = [("json", "json-pkg"), ("definitely_not_a_module_xyz", "ghost-pkg")]
    assert bootstrap.missing(specs) == ["ghost-pkg"]


def test_pip_install_uses_current_interpreter_and_reports_lines(monkeypatch):
    seen = {}

    class FakeProc:
        def __init__(self, cmd, **kw):
            seen["cmd"] = cmd
            self.stdout = iter(["Collecting x\n", "\n", "Successfully installed x\n"])

        def wait(self):
            return 0

    monkeypatch.setattr(bootstrap.subprocess, "Popen", FakeProc)
    lines = []
    ok, last = bootstrap.pip_install(["x"], lines.append)
    assert ok is True
    assert seen["cmd"][:4] == [sys.executable, "-m", "pip", "install"]
    assert seen["cmd"][-1] == "x"
    assert lines == ["Collecting x", "Successfully installed x"]
    assert last == "Successfully installed x"


def test_pip_install_failure_is_reported(monkeypatch):
    class FailProc:
        def __init__(self, cmd, **kw):
            self.stdout = iter(["ERROR: no such package\n"])

        def wait(self):
            return 1

    monkeypatch.setattr(bootstrap.subprocess, "Popen", FailProc)
    ok, last = bootstrap.pip_install(["nope"])
    assert ok is False
    assert "ERROR" in last
