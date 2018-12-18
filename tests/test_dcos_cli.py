import subprocess

import deprecation
import pytest
from dcos_test_utils import dcos_cli


@deprecation.deprecated(details="Deprecated in favor of the `exec` function. DCOS-44823")
def test_exec_command(caplog):
    cli = dcos_cli.DcosCli('')
    stdout, stderr = cli.exec_command(
        ['/bin/sh', '-c', 'echo "hello, world!"']
    )
    assert stdout == 'hello, world!\n'
    assert stderr == ''
    assert any(rec.message.startswith('CMD:') for rec in caplog.records)
    assert any(rec.message.startswith('STDOUT:') for rec in caplog.records)
    assert any(rec.message.startswith('STDERR:') for rec in caplog.records)


@deprecation.deprecated(details="Deprecated in favor of the `exec` function. DCOS-44823")
def test_exec_command_fail(caplog):
    cli = dcos_cli.DcosCli('')
    with pytest.raises(subprocess.CalledProcessError):
        cli.exec_command(['/bin/sh', '-c', 'does-not-exist'])
    assert any(rec.message.startswith('CMD:') for rec in caplog.records)
    assert any(rec.message.startswith('STDERR:') for rec in caplog.records)


def test_exec(caplog):
    cli = dcos_cli.DcosCli('')
    process = cli.exec(
        ['/bin/sh', '-c', 'echo "hello, world!"']
    )
    assert process.stdout == b'hello, world!\n'
    assert process.stderr == b''
    assert process.returncode == 0
    assert any(rec.message.startswith('CMD:') for rec in caplog.records)
    assert any(rec.message.startswith('STDOUT:') for rec in caplog.records)
    assert any(rec.message.startswith('STDERR:') for rec in caplog.records)


def test_exec_fail(caplog):
    cli = dcos_cli.DcosCli('')
    with pytest.raises(subprocess.CalledProcessError):
        cli.exec(['/bin/sh', '-c', 'does-not-exist'])
    assert any(rec.message.startswith('CMD:') for rec in caplog.records)
    assert any(rec.message.startswith('STDERR:') for rec in caplog.records)
    assert any(rec.message.startswith('STDOUT:') for rec in caplog.records)


def test_exec_fail_without_check(caplog):
    cli = dcos_cli.DcosCli('')
    process = cli.exec(
        ['/bin/sh', '-c', 'does-not-exist'],
        check=False
    )
    assert process.stdout == b''
    assert b'does-not-exist' in process.stderr
    assert process.returncode == 127
    assert any(rec.message.startswith('CMD:') for rec in caplog.records)
    assert any(rec.message.startswith('STDOUT:') for rec in caplog.records)
    assert any(rec.message.startswith('STDERR:') for rec in caplog.records)
