from unittest import mock

import pytest
import requests
from requests import HTTPError, models

from dcos_test_utils.helpers import Url
from dcos_test_utils.jobs import Jobs


class MockResponse:
    def __init__(self, json: dict, status_code: int):
        self._json = json
        self._status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self._status_code >= 400:
            raise HTTPError('Throwing test error')

    @property
    def status_code(self):
        return self._status_code


class MockEmitter:
    def __init__(self, mock_responses: list):
        self._mock_responses = mock_responses
        self._request_cache = list()

    def request(self, *args, **kwargs):
        self._request_cache.append((args, kwargs))
        return self._mock_responses.pop(0)

    @property
    def headers(self):
        return dict()

    @property
    def cookies(self):
        return dict()

    @property
    def debug_cache(self):
        return self._request_cache


@pytest.fixture
def replay_session(monkeypatch):
    """A mocked session that sends back the configured responses in
    order.
    """
    run_payload = {'id': 'myrun1'}
    job_payload = {'id':      'myjob',
                   'history': {'successfulFinishedRuns': [run_payload],
                               'failedFinishedRuns':     []}}

    # 2 200's to test timeout=1
    mock_replay = list((
        MockResponse(run_payload, 201),
        MockResponse({}, 200),
        MockResponse({}, 200),
        MockResponse({}, 404),
        MockResponse(job_payload, 200),
    ))

    mock_session = MockEmitter(mock_replay)

    monkeypatch.setattr(requests, 'Session',
                        lambda *args, **kwargs: mock_session)

    yield run_payload, job_payload, mock_session

    print('Actual session requests:')
    print(mock_session.debug_cache)


@pytest.fixture
def mock_url():
    """A URL that is accepted by DcosApiSession."""
    return Url('https',
               'localhost',
               'service/metronome',
               '', '',
               port=443)


@pytest.fixture
def mock_error():
    """A mock that will throw an error on raise_for_status()."""
    resp = mock.MagicMock(spec=models.Response)
    resp.return_value.raise_for_status.side_effect = HTTPError
    return resp


def test_jobs_create(monkeypatch, mock_url):
    """Create should return JSON of the created Job."""
    job_payload = {'id': 'app1'}
    resp_json = {'id': 'response'}
    exp_method = 'POST'
    exp_url = 'https://localhost:443/service/metronome/v1/jobs'

    resp = mock.MagicMock(spec=models.Response, name='create_mock')
    resp.return_value.json.side_effect = lambda: resp_json
    monkeypatch.setattr(requests.Session, 'request', resp)

    j = Jobs(default_url=mock_url)
    assert resp_json == j.create(job_payload)
    resp.return_value.raise_for_status.assert_called_once_with()

    # verify HTTP method and URL
    args, kwargs = resp.call_args
    assert (exp_method, exp_url) == args
    assert {'json': job_payload} == kwargs


def test_jobs_create_raise_error(monkeypatch, mock_url, mock_error):
    monkeypatch.setattr(requests.Session, 'request', mock_error)

    j = Jobs(default_url=mock_url)
    with pytest.raises(HTTPError):
        j.create({'id': 'app1'})
    mock_error.return_value.raise_for_status.assert_called_once_with()
    mock_error.json.assert_not_called()


def test_jobs_destroy(monkeypatch, mock_url):
    """Destroy sends a DELETE and does not return anything."""
    exp_method = 'DELETE'
    exp_url = 'https://localhost:443/service/metronome/v1/jobs/myapp1'

    resp = mock.MagicMock(spec=models.Response, name='destroy_mock')
    monkeypatch.setattr(requests.Session, 'request', resp)

    j = Jobs(default_url=mock_url)
    j.destroy('myapp1')
    resp.return_value.raise_for_status.assert_called_once_with()

    # verify HTTP method and URL
    args, kwargs = resp.call_args
    assert (exp_method, exp_url) == args


def test_jobs_destroy_raise_error(monkeypatch, mock_url, mock_error):
    monkeypatch.setattr(requests.Session, 'request', mock_error)

    j = Jobs(default_url=mock_url)
    with pytest.raises(HTTPError):
        j.destroy('myapp1')

    mock_error.return_value.raise_for_status.assert_called_once_with()
    mock_error.json.assert_not_called()


def test_jobs_start(monkeypatch, mock_url):
    job_payload = {'id': 'myrun1'}
    exp_method = 'POST'
    exp_url = 'https://localhost:443/service/metronome/v1/jobs/myapp1/runs'

    resp = mock.MagicMock(spec=models.Response)
    resp.return_value.json.side_effect = lambda: job_payload
    monkeypatch.setattr(requests.Session, 'request', resp)

    j = Jobs(default_url=mock_url)
    assert job_payload == j.start('myapp1')
    resp.return_value.raise_for_status.assert_called_once_with()

    # verify HTTP method and URL
    args, kwargs = resp.call_args
    assert (exp_method, exp_url) == args


def test_jobs_start_raise_error(monkeypatch, mock_url, mock_error):
    monkeypatch.setattr(requests.Session, 'request', mock_error)

    j = Jobs(default_url=mock_url)
    with pytest.raises(HTTPError):
        j.start('myapp1')
    mock_error.return_value.raise_for_status.assert_called_once_with()
    mock_error.json.assert_not_called()


def test_jobs_run(mock_url, replay_session):
    j = Jobs(default_url=mock_url)
    success, run, job = j.run('myapp1')
    assert success is True
    assert run == replay_session[0]
    assert job == replay_session[1]
    assert len(replay_session[2].debug_cache) == 5


def test_jobs_run_timeout(mock_url, replay_session):
    j = Jobs(default_url=mock_url)
    with pytest.raises(Exception):
        j.run('myapp1', timeout=1)
    assert len(replay_session[2].debug_cache) == 3
