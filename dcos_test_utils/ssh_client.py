""" Simple, robust SSH client(s) for basic I/O with remote hosts
"""
import asyncio
import logging
import os
import pty
import stat
import tempfile
from contextlib import contextmanager
from subprocess import check_call, check_output
from typing import Callable, Union

import retrying

from dcos_test_utils import helpers

log = logging.getLogger(__name__)


SHARED_SSH_OPTS = [
        '-oConnectTimeout=10',
        '-oStrictHostKeyChecking=no',
        '-oUserKnownHostsFile=/dev/null',
        '-oLogLevel=ERROR',
        '-oBatchMode=yes',
        '-oPasswordAuthentication=no']


class Tunnelled():
    def __init__(self, base_cmd: list, target: str):
        """
        Args:
            base_cmd: list of strings that will be evaluated by check_call
                to send commands through the tunnel
            target: string in the form user@host
        """
        self.base_cmd = base_cmd
        self.target = target

    def command(self, cmd: list, **kwargs) -> bytes:
        """ Run a command at the tunnel target
        Args:
            cmd: list of strings that will be sent as a command to the target
            **kwargs: any keywork args that can be passed into
                subprocess.check_output. For more information, see:
                https://docs.python.org/3/library/subprocess.html#subprocess.check_output
        """
        run_cmd = self.base_cmd + [self.target] + cmd
        log.debug('Running socket cmd: ' + ' '.join(run_cmd))
        if 'stdout' in kwargs:
            return check_call(run_cmd, **kwargs)
        else:
            return check_output(run_cmd, **kwargs)

    def copy_file(self, src: str, dst: str) -> None:
        """ Copy a file from localhost to target

        Args:
            src: local path representing source data
            dst: destination for path
        """
        cmd = self.base_cmd + ['-C', self.target, 'cat>' + dst]
        log.debug('Copying {} to {}:{}'.format(src, self.target, dst))
        with open(src, 'r') as fh:
            check_call(cmd, stdin=fh)


def temp_ssh_key(key: str) -> str:
    key_path = helpers.session_tempfile(key)
    os.chmod(str(key_path), stat.S_IREAD | stat.S_IWRITE)
    return key_path


@contextmanager
def open_tunnel(
        user: str,
        host: str,
        port: int,
        control_path: str,
        key_path: str) -> Tunnelled:
    """ Provides clean setup/tear down for an SSH tunnel
    Args:
        user: SSH user
        key_path: path to a private SSH key
        host: string containing target host
        port: target's SSH port
    """
    target = user + '@' + host
    base_cmd = ['/usr/bin/ssh'] + SHARED_SSH_OPTS
    base_cmd += [
        '-oControlPath=' + control_path,
        '-oControlMaster=auto',
        '-p', str(port)]

    start_tunnel = base_cmd + ['-fnN', '-i', key_path, target]
    log.debug('Starting SSH tunnel: ' + ' '.join(start_tunnel))
    check_call(start_tunnel)
    log.debug('SSH Tunnel established!')

    yield Tunnelled(base_cmd, target)

    close_tunnel = base_cmd + ['-O', 'exit', target]
    log.debug('Closing SSH Tunnel: ' + ' '.join(close_tunnel))
    check_call(close_tunnel)


class SshClient:
    """ class for binding SSH user and key to tunnel
    """
    def __init__(self, user: str, key: str):
        self.user = user
        self.key_path = temp_ssh_key(key)

    def tunnel(self, host: str, port: int=22):
        with tempfile.NamedTemporaryFile() as f:
            return open_tunnel(self.user, host, port, f.name, self.key_path)

    def command(self, host: str, cmd: list, port: int=22, **kwargs) -> bytes:
        with self.tunnel(host, port) as t:
            return t.command(cmd, **kwargs)

    def get_home_dir(self, host: str, port: int=22) -> str:
        """ Returns the SSH home dir
        """
        return self.command(host, ['pwd'], port=port).decode().strip()

    @retrying.retry(wait_fixed=1000)
    def wait_for_ssh_connection(self, host: str, port: int=22) -> None:
        """ Blocks until SSH connection can be established
        """
        self.get_home_dir(host, port)

    def add_ssh_user_to_docker_users(self, host: str, port: int=22):
        self.command(host, ['sudo', 'usermod', '-aG', 'docker', self.user], port=port)


@contextmanager
def make_slave_pty():
    master_pty, slave_pty = pty.openpty()
    yield slave_pty
    os.close(slave_pty)
    os.close(master_pty)


def parse_ip(ip: str) -> (str, int):
    """  takes an IP string and either a hostname and either the given port or
    the default ssh port of 22
    """
    tmp = ip.split(':')
    if len(tmp) == 2:
        return tmp[0], int(tmp[1])
    elif len(tmp) == 1:
        # no port, assume default SSH
        return ip, 22
    else:
        raise ValueError(
            "Expected a string of form <ip> or <ip>:<port> but found a string with more than one " +
            "colon in it. NOTE: IPv6 is not supported at this time. Got: {}".format(ip))


class CommandChain():
    '''
    Add command to execute on a remote host.

    :param cmd: String, command to execute
    :param stage: String (optional)
    :return:
    '''
    execute_flag = 'execute'
    copy_flag = 'copy'

    def __init__(self):
        self.commands_stack = []

    def add_execute(self, cmd: Union[list, Callable], stage=None):
        self.commands_stack.append((self.execute_flag, cmd, stage))

    def add_copy(self, local_path, remote_path, recursive=False, stage=None):
        self.commands_stack.append((self.copy_flag, local_path, remote_path, recursive, stage))


class MultiRunner(SshClient):
    def __init__(
            self,
            user: str,
            key: str,
            targets: list,
            process_timeout=120,
            parallelism=10):
        super().__init__(user, key)
        self.process_timeout = process_timeout
        self.__targets = targets
        self.__parallelism = parallelism

    @asyncio.coroutine
    def run_cmd_return_dict_async(
            self,
            cmd: list,
            stage: str):
        """
        Runs cmd with a pTTY and times out if necessary
        Returns a dict of data about the process
        """
        with make_slave_pty() as slave_pty:
            process = yield from asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=slave_pty,
                env={'TERM': 'linux'})
            stdout = b''
            stderr = b''
            try:
                stdout, stderr = yield from asyncio.wait_for(process.communicate(), self.process_timeout)
            except asyncio.TimeoutError:
                try:
                    process.terminate()
                except ProcessLookupError:
                    log.info('process with pid {} not found'.format(process.pid))
                log.error('timeout of {} sec reached. PID {} killed'.format(self.process_timeout, process.pid))

        # For each possible line in stderr, match from the beginning of the line for the
        # the confusing warning: "Warning: Permanently added ...". If the warning exists,
        # remove it from the string.
        err_arry = stderr.decode().split('\r')
        stderr = bytes('\n'.join([line for line in err_arry if not line.startswith(
            'Warning: Permanently added')]), 'utf-8')

        return {
            "cmd": cmd,
            "stdout": stdout.decode().split('\n'),
            "stderr": stderr.decode().split('\n'),
            "returncode": process.returncode,
            "pid": process.pid,
            "stage": stage
        }

    @asyncio.coroutine
    def run_async(self, host, command, stage):
        # command consists of (command_flag, command, stage)
        # we will ignore all but command for now
        _, cmd, _ = command
        hostname, port = parse_ip(host)

        with self.tunnel(hostname, port) as t:
            full_cmd = t.base_cmd + [t.target] + cmd
            log.debug('executing command {}'.format(full_cmd))
            result = yield from self.run_cmd_return_dict_async(full_cmd, stage)
        return result

    @asyncio.coroutine
    def copy_async(self, host, command, stage):
        # command[0] is command_flag, command[-1] is stage
        # we will ignore them here.
        _, local_path, remote_path, recursive, _ = command
        hostname, port = parse_ip(host)
        copy_command = []
        if recursive:
            copy_command.append('-r')
        remote_full_path = '{}@{}:{}'.format(self.user, hostname, remote_path)
        copy_command += [local_path, remote_full_path]
        full_cmd = ['/usr/bin/scp'] + SHARED_SSH_OPTS + ['-P', str(port), '-i', self.key_path] + copy_command
        log.debug('copy with command {}'.format(full_cmd))
        result = yield from self.run_cmd_return_dict_async(full_cmd, stage)
        return result

    def _run_chain_command(self, chain: CommandChain, host):
        # do start chain logging

        host_status = 'success'

        command_map = {
            CommandChain.execute_flag: self.run_async,
            CommandChain.copy_flag: self.copy_async
        }

        process_exit_code_map = {
            None: 'terminated',
            0: 'success'
        }
        result_list = list()
        for command in chain.commands_stack:
            cmd_flag = command[0]
            stage = command[-1]

            result = yield from command_map[cmd_flag](host, command, stage)
            host_status = process_exit_code_map.get(result['returncode'], 'failed')

            result_list.append(result)
            if host_status != 'success':
                break
        # do chain finish logging
        return result_list

    @asyncio.coroutine
    def dispatch_chain(self, host, chain, sem) -> None:
        """ controls the parallelism of jobs by blocking on a semaphor
        """
        log.debug('Started dispatch_chain for host {}'.format(host))
        with (yield from sem):
            result_list = yield from self._run_chain_command(chain, host)
        return result_list

    @asyncio.coroutine
    def run_command_chain_async(self, cmd_chain) -> list:
        """
        - instantiates a semaphor to control parallelism
        - starts the commands in cmd_chain against all hosts
        - will block if parallelism will be exceeded
        - after all tasks have been started, this will block until finishes
        """
        sem = asyncio.Semaphore(self.__parallelism)
        log.debug('Waiting for run_command_chain_async to execute')
        tasks = []
        for host in self.__targets:
            tasks.append(asyncio.async(self.dispatch_chain(host, cmd_chain, sem)))
        yield from asyncio.wait(tasks)
        return [task.result() for task in tasks]

    def run_command_chain(self, cmd_chain):
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.run_command_chain_async(cmd_chain))
        finally:
            loop.close()
        return result
