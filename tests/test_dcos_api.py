""" Verifies basic interface for the test harness employed in
DC/OS integration tests, see: packages/dcos-integration-tests/extra
"""
import pytest
import requests

from unittest.mock import MagicMock

from dcos_test_utils import dcos_api, helpers


class MockResponse:
    def __init__(self):
        self.cookies = {'dcos-acs-auth-cookie': 'foo'}

    def raise_for_status(self):
        pass

    def json(self):
        return {'token': 'bar'}


@pytest.fixture
def mock_dcos_client(monkeypatch):
    monkeypatch.setenv('DCOS_DNS_ADDRESS', 'http://mydcos.dcos')
    monkeypatch.setenv('MASTER_HOSTS', '127.0.0.1,0.0.0.0')
    monkeypatch.setenv('SLAVE_HOSTS', '127.0.0.1,123.123.123.123')
    monkeypatch.setenv('PUBLIC_SLAVE_HOSTS', '127.0.0.1,0.0.0.0')
    # covers any request made via the ApiClientSession
    monkeypatch.setattr(requests.Session, 'request', lambda *args, **kwargs: MockResponse())
    monkeypatch.setattr(dcos_api.DcosApiSession, 'wait_for_dcos', lambda self: True)
    args = dcos_api.DcosApiSession.get_args_from_env()
    args['auth_user'] = None
    return dcos_api.DcosApiSession(**args)


def test_make_user_session(mock_dcos_client):
    # make user session from no auth
    cluster_none = mock_dcos_client
    user_1 = dcos_api.DcosUser({'foo': 'bar'})
    user_2 = dcos_api.DcosUser({'baz': 'qux'})
    cluster_1 = cluster_none.get_user_session(user_1)
    assert cluster_1.session.auth.auth_token == 'bar'
    # Add a cookie to this session to make sure it gets cleared
    cluster_1.session.cookies.update({'dcos-acs-auth-cookie': 'foo'})
    # make user session from user
    cluster_2 = cluster_1.get_user_session(user_2)
    assert cluster_2.session.auth.auth_token == 'bar'
    # check cleared cookie
    assert cluster_2.session.cookies.get('dcos-acs-auth-cookie') is None
    # make no auth session from use session
    cluster_none = cluster_2.get_user_session(None)
    assert cluster_none.session.auth is None
    assert len(cluster_none.session.cookies.items()) == 0


def test_dcos_client_api(mock_dcos_client):
    """ Tests two critical aspects of the DcosApiSession
    1. node keyword arg is supported
    2. all HTTP verbs work
    """
    args = dcos_api.DcosApiSession.get_args_from_env()
    args['auth_user'] = None
    cluster = dcos_api.DcosApiSession(**args)
    # no assert necessary, just make sure that this function signatures works
    r = cluster.get('', node='123.123.123.123')
    r.raise_for_status()
    cluster.get('')
    cluster.post('')
    cluster.put('')
    cluster.delete('')
    cluster.head('')
    cluster.patch('')
    cluster.options('')


def test_api_client_session_path(monkeypatch):
    mock_request = MagicMock()
    monkeypatch.setattr(requests.Session, 'request', mock_request)
    access_url = 'http://leader.mesos'
    api = helpers.ApiClientSession(helpers.Url.from_string(access_url))
    api.get('')
    assert mock_request.call_args[0][0] == 'GET'
    assert mock_request.call_args[0][1] == access_url
    mock_request.reset()

    test_path = '/'
    api.get(test_path)
    assert mock_request.call_args[0][0] == 'GET'
    assert mock_request.call_args[0][1] == access_url + test_path
    mock_request.reset()

    test_path = '//'
    api.get(test_path)
    assert mock_request.call_args[0][0] == 'GET'
    assert mock_request.call_args[0][1] == access_url + test_path
