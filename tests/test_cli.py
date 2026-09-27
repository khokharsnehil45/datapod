import pytest
from pathlib import Path
from datapod.cli import main, parse_metadata_arg


def test_parse_metadata_arg():
    # Pipe syntax: "file_name | holder name"
    holder, meta = parse_metadata_arg("report.pdf | finance_team")
    assert holder == "finance_team"
    assert meta["label"] == "report.pdf"

    # Key=value syntax
    holder, meta = parse_metadata_arg("holder=alice,env=staging,tier=gold")
    assert holder == "alice"
    assert meta["env"] == "staging"
    assert meta["tier"] == "gold"


def test_cli_add_and_pull(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    test_file = tmp_path / "sample.log"
    test_file.write_text("Server boot 200 OK")

    # Add via flag format: datapod -add sample.log -meta "sample.log | dev_ops"
    res = main(["-add", str(test_file), "-meta", "sample.log | dev_ops"])
    assert res == 0
    captured = capsys.readouterr()
    assert "POD STORED SUCCESSFULLY" in captured.out
    assert "dev_ops" in captured.out

    # Extract ID from output
    import re
    match = re.search(r"datapod -pull ([a-f0-9]{8})", captured.out)
    assert match is not None
    pod_id = match.group(1)

    # Info
    res = main(["-info", pod_id])
    assert res == 0
    captured = capsys.readouterr()
    assert pod_id in captured.out
    assert "dev_ops" in captured.out

    # List
    res = main(["-list"])
    assert res == 0
    captured = capsys.readouterr()
    assert pod_id in captured.out

    # Pull
    pull_target = tmp_path / "extracted.log"
    res = main(["-pull", pod_id, "-out", str(pull_target)])
    assert res == 0
    assert pull_target.exists()
    assert pull_target.read_text() == "Server boot 200 OK"
