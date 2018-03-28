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

    yield mock_session

    print('Actual session requests:')
    print(mock_session.debug_cache)


@pytest.fixture
def mock_url():
    """A URL that is accepted by DcosApiSession."""
    return Url('https', 'localhost', 'package', '', '', port=443)


def test_repo_list(mock_url, replay_session):
    exp_url = 'https://localhost:443/package/repository/list'
    replay_session.queue([MockResponse({}, 200)])
    r = Package(default_url=mock_url).repository.list()
    assert r == {}
    assert replay_session.debug_cache[0] == (
        (('POST', exp_url), {'json': {}}))


def test_repo_add(mock_url, replay_session):
    exp_url = 'https://localhost:443/package/repository/add'
    replay_session.queue((
        MockResponse({}, 201),
        MockResponse({}, 201)
    ))
    r = Package(default_url=mock_url).repository.add(
            'http://example.com/repo',
            'my_repo', 0)
    assert r == {}
    assert replay_session.debug_cache[0] == (
        (('POST', exp_url),
         {'json': {'index': 0, 'name': 'http://example.com/repo',
                   'uri':   'my_repo'}})
    )
    r = Package(default_url=mock_url).repository.add(
            'http://example.com/repo',
            'my_repo')
    assert r == {}
    assert replay_session.debug_cache[1] == (
        (('POST', exp_url),
         {'json': {'name': 'http://example.com/repo', 'uri': 'my_repo'}})
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
