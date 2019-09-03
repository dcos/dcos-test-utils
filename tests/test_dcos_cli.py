import pytest
import subprocess

from dcos_test_utils import dcos_cli


def test_exec_command(caplog):
    cli = dcos_cli.DcosCli('', '', '')
    stdout, stderr = cli.exec_command(
        ['/bin/sh', '-c', 'echo "hello, world!"']
    )
    assert stdout == 'hello, world!\n'
    assert stderr == ''
    assert any(rec.message.startswith('CMD:') for rec in caplog.records)
    assert any(rec.message.startswith('STDOUT:') for rec in caplog.records)
    assert any(rec.message.startswith('STDERR:') for rec in caplog.records)


def test_exec_command_fail(caplog):
    cli = dcos_cli.DcosCli('', '', '')
    with pytest.raises(subprocess.CalledProcessError):
        cli.exec_command(['/bin/sh', '-c', 'does-not-exist'])
    assert any(rec.message.startswith('CMD:') for rec in caplog.records)
    assert any(rec.message.startswith('STDERR:') for rec in caplog.records)
