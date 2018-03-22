from unittest import mock
from unittest.mock import PropertyMock

import pytest
import requests
from requests import HTTPError, models

from dcos_test_utils.helpers import Url
from dcos_test_utils.jobs import Jobs


@pytest.fixture
def mock_url():
    """A URL that is accepted by DcosApiSession."""
    return Url('https', 'localhost', 'service/metronome', '', '', port=443)


@pytest.fixture
def mock_error():
    """A mock that will throw an error on raise_for_status()."""
    resp = mock.MagicMock(spec=models.Response)
    resp.return_value.raise_for_status.side_effect = HTTPError
    return resp


def test_jobs_create(monkeypatch, mock_url):
    """Create should return the "id" of the returned JSON."""
    job_payload = {'id': 'app1'}
    exp_method = 'POST'
    exp_url = 'https://localhost:443/service/metronome/v1/jobs'

    resp = mock.MagicMock(spec=models.Response, name='create_mock')
    resp.return_value.json.side_effect = lambda: {'id': 'app1'}
    monkeypatch.setattr(requests.Session, 'request', resp)

    j = Jobs(default_url=mock_url)
    assert 'app1' == j.create(job_payload)
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
    assert 'myrun1' == j.start('myapp1')
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


def test_jobs_run(monkeypatch, mock_url):
    run_payload = {'id': 'myrun1'}
    job_payload = {'id':      'myjob',
                   'history': {'successfulFinishedRuns': [run_payload],
                               'failedFinishedRuns':     []}}

    resp = mock.MagicMock(spec=models.Response, name='run_mock')
    resp.return_value.json.side_effect = [run_payload, job_payload]
    resp.return_value.raise_for_status.side_effect = (True, True)
    # 404 is "run complete" and only the _wait_for loop is checking
    # this.
    type(resp.return_value).status_code = PropertyMock(return_value=404)
    monkeypatch.setattr(requests.Session, 'request', resp)

    j = Jobs(default_url=mock_url)
    success, run, job = j.run('myapp1')
    assert True is success
    assert run_payload == run
    assert job_payload == job
