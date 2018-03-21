import pytest
import requests
from requests import HTTPError

from dcos_test_utils.helpers import Url
from dcos_test_utils.jobs import Jobs


class MockJobResponse:
    def __init__(self, session, method, url, *args, json=None, **kwargs):
        self.cookies = {'dcos-acs-auth-cookie': 'foo'}
        self._session = session
        self._method = method
        self._url = url
        self._payload = json
        self._raise_status = kwargs['raise_status'] if 'raise_status' in kwargs else False
        assert url.startswith('https://localhost:443/service/metronome/v1/jobs')
    
    def raise_for_status(self):
        if self._raise_status:
            raise HTTPError('throwing error for test')
        pass
    
    def json(self):
        return self._payload


@pytest.fixture
def fake_url():
    return Url('https', 'localhost', 'service/metronome', '', '', port=443)


def test_jobs_create(monkeypatch, fake_url):
    monkeypatch.setattr(requests.Session, 'request',
                        lambda *args, **kwargs: MockJobResponse(*args, **kwargs))
    j = Jobs(default_url=fake_url)
    app_id = j.create({'id': 'app1'})
    assert app_id == 'app1'


def test_jobs_create_raise_error(monkeypatch, fake_url):
    monkeypatch.setattr(requests.Session, 'request',
                        lambda *args, **kwargs: MockJobResponse(*args, **kwargs, raise_status=True))
    j = Jobs(default_url=fake_url)
    with pytest.raises(HTTPError):
        j.create({'id': 'app1'})


def test_jobs_destroy(monkeypatch, fake_url):
    monkeypatch.setattr(requests.Session, 'request',
                        lambda *args, **kwargs: MockJobResponse(*args, **kwargs))
    j = Jobs(default_url=fake_url)
    j.destroy('myapp1')


def test_jobs_destroy_raise_error(monkeypatch, fake_url):
    monkeypatch.setattr(requests.Session, 'request',
                        lambda *args, **kwargs: MockJobResponse(*args, **kwargs, raise_status=True))
    j = Jobs(default_url=fake_url)
    with pytest.raises(HTTPError):
        j.destroy('myapp1')


def test_jobs_start(monkeypatch, fake_url):
    monkeypatch.setattr(requests.Session, 'request',
                        lambda *args, **kwargs: MockJobResponse(*args, **kwargs, json={'id': 'myrun1'}))
    j = Jobs(default_url=fake_url)
    r = j.start('myapp1')
    assert r == 'myrun1'


def test_jobs_start_raise_error(monkeypatch, fake_url):
    monkeypatch.setattr(requests.Session, 'request',
                        lambda *args, **kwargs: MockJobResponse(*args, **kwargs, raise_status=True))
    j = Jobs(default_url=fake_url)
    with pytest.raises(HTTPError):
        j.start('myapp1')
