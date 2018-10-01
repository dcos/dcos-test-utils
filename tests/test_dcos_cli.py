import pytest
import subprocess

from dcos_test_utils import dcos_cli


def test_exec_command(caplog):
    cli = dcos_cli.DcosCli('')
    stdout, stderr, returncode = cli.exec_command(
        ['/bin/sh', '-c', 'echo "hello, world!"']
    )
    assert stdout == 'hello, world!\n'
    assert stderr == ''
    assert any(rec.message.startswith('CMD:') for rec in caplog.records)
    assert any(rec.message.startswith('STDOUT:') for rec in caplog.records)
    assert any(rec.message.startswith('STDERR:') for rec in caplog.records)
    assert returncode == 0


def test_exec_command_fail(caplog):
    cli = dcos_cli.DcosCli('')
    with pytest.raises(subprocess.CalledProcessError):
        _stdout, _stderr, returncode = cli.exec_command(['/bin/sh', '-c', 'does-not-exist'])
        assert returncode != 0

    assert any(rec.message.startswith('CMD:') for rec in caplog.records)
    assert any(rec.message.startswith('STDERR:') for rec in caplog.records)
