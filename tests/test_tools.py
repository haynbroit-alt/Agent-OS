import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config
config.ALLOWED_COMMANDS = {"ls", "echo", "cat"}

from modules.tools import Tools


def test_think():
    t = Tools()
    out, ok, cost = t.execute("think:just reasoning")
    assert ok and out == "just reasoning" and cost == 1


def test_shell_allowed():
    t = Tools()
    out, ok, cost = t.execute("shell:echo hello")
    assert ok and "hello" in out


def test_shell_blocked():
    t = Tools()
    out, ok, cost = t.execute("shell:rm -rf /")
    assert not ok and "blocked" in out


def test_read_missing():
    t = Tools()
    out, ok, cost = t.execute("read:/nonexistent/file.txt")
    assert not ok


def test_would_block():
    t = Tools()
    assert not t.would_block("shell:ls -la")
    assert t.would_block("shell:rm -rf /")
    assert not t.would_block("think:plan")
    assert not t.would_block("read:config.py")


def test_invalid_action():
    t = Tools()
    out, ok, _ = t.execute("no_colon_here")
    assert not ok


if __name__ == "__main__":
    test_think()
    test_shell_allowed()
    test_shell_blocked()
    test_read_missing()
    test_would_block()
    test_invalid_action()
    print("All tool tests passed.")
