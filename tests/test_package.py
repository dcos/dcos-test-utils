import pytest
import requests

from dcos_test_utils.helpers import Url
from dcos_test_utils.package import Package
from helpers import MockEmitter, MockResponse


@pytest.fixture
def replay_session(monkeypatch):
    """A mocked session that sends back the configured responses in
    order.
    """
    mock_session = MockEmitter(list())

    monkeypatch.setattr(requests, 'Session',
                        lambda *args, **kwargs: mock_session)

    try:
        yield mock_session
    finally:
        print('Actual session requests:')
        print(mock_session.debug_cache)


@pytest.fixture
def mock_url():
    """A URL that is accepted by DcosApiSession."""
    return Url('https', 'localhost', 'package', '', '', port=443)


def test_repo_list(mock_url, replay_session):
    exp_url = 'https://localhost:443/package/repository/list'
    replay_session.queue((MockResponse({}, 200), ))
    r = Package(default_url=mock_url).repository.list()
    assert r == {}
    assert replay_session.debug_cache[0] == (
        (('POST', exp_url), {'json': {}}))


def test_repo_add_typeerror(mock_url, replay_session):
    replay_session.queue((
        MockResponse({}, 201),
        MockResponse({}, 201)
    ))
    with pytest.raises(TypeError):
        Package(default_url=mock_url).repository.add(
                'http://example.com/repo', 'my_repo', 'a')


def test_repo_add(mock_url, replay_session):
    exp_url = 'https://localhost:443/package/repository/add'
    replay_session.queue((
        MockResponse({}, 201),
        MockResponse({}, 201)
    ))
    r = Package(default_url=mock_url).repository.add(
            'http://example.com/repo', 'my_repo', 0)
    assert r == {}
    assert replay_session.debug_cache[0] == (
        (('POST', exp_url),
         {'json': {'index': 0, 'name': 'http://example.com/repo',
                   'uri':   'my_repo'}})
    )
    r = Package(default_url=mock_url).repository.add(
            'http://example.com/repo', 'my_repo')
    assert r == {}
    assert replay_session.debug_cache[1] == (
        (('POST', exp_url),
         {'json': {'name': 'http://example.com/repo',
                   'uri':  'my_repo'}})
    )


def test_repo_delete(mock_url, replay_session):
    exp_url = 'https://localhost:443/package/repository/delete'
    kwargs = {'name': 'my_repo', 'uri': 'http://example.com/repo'}
    replay_session.queue([MockResponse({}, 201)])
    r = Package(default_url=mock_url).repository.delete(**kwargs)
    assert r == {}
    assert replay_session.debug_cache[0] == (
        (('POST', exp_url), {'json': kwargs})
    )


def test_package_list(mock_url, replay_session):
    exp_url = 'https://localhost:443/package/list'
    replay_session.queue((
        MockResponse({}, 200), MockResponse({}, 200),
        MockResponse({}, 200), MockResponse({}, 200),
    ))
    p = Package(default_url=mock_url).list()
    assert p == {}
    assert replay_session.debug_cache[0] == (
        (('POST', exp_url), {'json': {}}))

    p = Package(default_url=mock_url).list(name='a')
    assert p == {}
    assert replay_session.debug_cache[1] == (
        (('POST', exp_url), {'json': {'packageName': 'a'}}))

    p = Package(default_url=mock_url).list(app_id='b')
    assert p == {}
    assert replay_session.debug_cache[2] == (
        (('POST', exp_url), {'json': {'appId': 'b'}}))


def test_package_install(mock_url, replay_session):
    exp_url = 'https://localhost:443/package/install'
    replay_session.queue((
        MockResponse({}, 200), MockResponse({}, 200),
        MockResponse({}, 200), MockResponse({}, 200),
    ))
    p = Package(default_url=mock_url).install('hello-world')
    assert p == {}
    assert replay_session.debug_cache[0] == (
        (('POST', exp_url), {'json': {'packageName': 'hello-world'}}))
    p = Package(default_url=mock_url).install('hello-world', '23')
    assert p == {}
    assert replay_session.debug_cache[1] == (
        (('POST', exp_url),
         {'json': {'packageName':    'hello-world',
                   'packageVersion': '23'}}))
    p = Package(default_url=mock_url).install('hello-world', '23', {'a': 'b'})
    assert p == {}
    assert replay_session.debug_cache[2] == (
        (('POST', exp_url),
         {'json': {'packageName':    'hello-world',
                   'packageVersion': '23',
                   'options':        {'a': 'b'}}}))
    p = Package(default_url=mock_url).install('hello-world', '23',
                                              {'a': 'b'}, 'myapp1')
    assert p == {}
    assert replay_session.debug_cache[3] == (
        (('POST', exp_url),
         {'json': {'packageName':    'hello-world',
                   'packageVersion': '23',
                   'options':        {'a': 'b'},
                   'appId':          'myapp1'}}))


def test_package_install_typeerror(mock_url, replay_session):
    replay_session.queue((
        MockResponse({}, 200), MockResponse({}, 200),
    ))
    with pytest.raises(TypeError):
        Package(default_url=mock_url).install('hello-world',
                                              options='a')


def test_package_uninstall(mock_url, replay_session):
    exp_url = 'https://localhost:443/package/uninstall'
    replay_session.queue((
        MockResponse({}, 200), MockResponse({}, 200),
    ))
    p = Package(default_url=mock_url).uninstall('hello-world')
    assert p == {}
    assert replay_session.debug_cache[0] == (
        (('POST', exp_url), {'json': {'packageName': 'hello-world'}}))
    p = Package(default_url=mock_url).uninstall('hello-world', 'myapp1')
    assert p == {}
    assert replay_session.debug_cache[1] == (
        (('POST', exp_url),
         {'json': {'packageName': 'hello-world',
                   'appId':       'myapp1'}}))


def test_package_list_versions(mock_url, replay_session):
    exp_url = 'https://localhost:443/package/list-versions'
    replay_session.queue((
        MockResponse({}, 200), MockResponse({}, 200),
    ))
    p = Package(default_url=mock_url).list_versions('hello-world')
    assert p == {}
    assert replay_session.debug_cache[0] == (
        (('POST', exp_url),
         {'json': {'packageName':            'hello-world',
                   'includePackageVersions': False}})
    )
    p = Package(default_url=mock_url).list_versions('hello-world', True)
    assert p == {}
    assert replay_session.debug_cache[1] == (
        (('POST', exp_url),
         {'json': {'packageName':            'hello-world',
                   'includePackageVersions': True}})
    )


def test_package_describe(mock_url, replay_session):
    exp_url = 'https://localhost:443/package/describe'
    replay_session.queue((
        MockResponse({}, 200), MockResponse({}, 200),
    ))
    p = Package(default_url=mock_url).describe('hello-world')
    assert p == {}
    assert replay_session.debug_cache[0] == (
        (('POST', exp_url),
         {'json': {'packageName': 'hello-world'}}))
    p = Package(default_url=mock_url).describe('hello-world', 'v3')
    assert p == {}
    assert replay_session.debug_cache[1] == (
        (('POST', exp_url),
         {'json': {'packageName':    'hello-world',
                   'packageVersion': 'v3'}}))


def test_package_search(mock_url, replay_session):
    exp_url = 'https://localhost:443/package/search'
    replay_session.queue((
        MockResponse({}, 200), MockResponse({}, 200),
    ))
    p = Package(default_url=mock_url).search('hello-world')
    assert p == {}
    assert replay_session.debug_cache[0] == (
        (('POST', exp_url),
         {'json': {'query': 'hello-world'}}))
    p = Package(default_url=mock_url).search()
    assert p == {}
    assert replay_session.debug_cache[1] == (
        (('POST', exp_url), {'json': {}}))
