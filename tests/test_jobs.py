import pytest
import requests
from requests import HTTPError

from dcos_test_utils.helpers import Url
from dcos_test_utils.jobs import Jobs
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
    return Url('https',
               'localhost',
               'service/metronome',
               '', '',
               port=443)


def test_jobs_create(mock_url, replay_session):
    """Create should return JSON of the created Job."""
    job_payload = {'id': 'app1'}
    resp_json = {'id': 'response'}
    exp_method = 'POST'
    exp_url = 'https://localhost:443/service/metronome/v1/jobs'
    replay_session.queue([MockResponse(resp_json, 201)])

    j = Jobs(default_url=mock_url)

    assert j.create(job_payload) == resp_json
    assert len(replay_session.debug_cache) == 1
    assert replay_session.debug_cache[0] == (
        (exp_method, exp_url), {'json': job_payload})


def test_jobs_create_raise_error(mock_url, replay_session):
    replay_session.queue([MockResponse({}, 500)])

    j = Jobs(default_url=mock_url)
    with pytest.raises(HTTPError):
        j.create({'id': 'app1'})


def test_jobs_destroy(mock_url, replay_session):
    """Destroy sends a DELETE and does not return anything."""
    exp_method = 'DELETE'
    exp_url = 'https://localhost:443/service/metronome/v1/jobs/myapp1'
    replay_session.queue([MockResponse({}, 200)])

    j = Jobs(default_url=mock_url)
    j.destroy('myapp1')

    assert replay_session.debug_cache[0] == (
        (exp_method, exp_url),
        {'params': {'stopCurrentJobRuns': 'true'}})


def test_jobs_destroy_raise_error(mock_url, replay_session):
    replay_session.queue([MockResponse({}, 500)])

    j = Jobs(default_url=mock_url)
    with pytest.raises(HTTPError):
        j.destroy('myapp1')


def test_jobs_start(mock_url, replay_session):
    """Test the `start` method and verify the returned JSON."""
    job_payload = {'id': 'myrun1'}
    exp_method = 'POST'
    exp_url = 'https://localhost:443/service/metronome/v1/jobs/myapp1/runs'
    replay_session.queue([MockResponse(job_payload, 201)])

    j = Jobs(default_url=mock_url)

    assert job_payload == j.start('myapp1')
    # verify HTTP method and URL
    assert replay_session.debug_cache[0] == (
        (exp_method, exp_url), {})


def test_jobs_start_raise_error(mock_url, replay_session):
    replay_session.queue([MockResponse({}, 500)])

    j = Jobs(default_url=mock_url)
    with pytest.raises(HTTPError):
        j.start('myapp1')


def test_jobs_run(mock_url, replay_session):
    """Test the `run` method, which is a mixture of `start`
    and waiting (looping) on the run to complete.
    """
    run_payload = {'id': 'myrun1'}
    job_payload = {'id':      'myjob',
                   'history': {'successfulFinishedRuns': [run_payload],
                               'failedFinishedRuns':     []}}
    # 2 200's to test timeout=1
    mock_replay = list((
        MockResponse(run_payload, 201),
        MockResponse({}, 200),
        MockResponse({}, 404),  # break the wait loop (run over)
        MockResponse(job_payload, 200),
        MockResponse(job_payload, 200),
    ))
    replay_session.queue(mock_replay)

    j = Jobs(default_url=mock_url)
    success, run, job = j.run('myapp1')

    assert success is True
    assert run == run_payload
    assert job == job_payload
    assert len(replay_session.debug_cache) == 5


def test_jobs_run_failed_run(mock_url, replay_session):
    """Test the `run` method, which is a mixture of `start`
    and waiting (looping) on the run to complete.

    This test expects the Run to appear in the failed run list.
    """
    run_payload = {'id': 'myrun1'}
    job_payload = {'id':      'myjob',
                   'history': {'successfulFinishedRuns': [],
                               'failedFinishedRuns':     [run_payload]}}
    # 2 200's to test timeout=1
    mock_replay = list((
        MockResponse(run_payload, 201),
        MockResponse({}, 404),
        MockResponse(job_payload, 200),
        MockResponse(job_payload, 200),
    ))
    replay_session.queue(mock_replay)

    j = Jobs(default_url=mock_url)
    success, run, job = j.run('myapp1')

    assert success is False
    assert run == run_payload
    assert job == job_payload
    assert len(replay_session.debug_cache) == 4


def test_jobs_run_timeout(mock_url, replay_session):
    run_payload = {'id': 'myrun1'}
    job_payload = {'id':      'myjob',
                   'history': {'successfulFinishedRuns': [run_payload],
                               'failedFinishedRuns':     []}}
    # lots of responses, but only a few will trigger before timeout
    mock_replay = list((
        MockResponse(run_payload, 201),
        MockResponse({}, 200),
        MockResponse({}, 200),
        MockResponse({}, 200),  # should timeout here
        MockResponse({}, 200),
        MockResponse({}, 200),
        MockResponse({}, 404),
        MockResponse(job_payload, 200),
    ))
    replay_session.queue(mock_replay)

    j = Jobs(default_url=mock_url)
    with pytest.raises(Exception):
        j.run('myapp1', timeout=2)

    assert len(replay_session.debug_cache) == 4


def test_jobs_run_history_not_available(mock_url, replay_session):
    run_payload = {'id': 'myrun1'}
    job_payload = {'id':      'myjob',
                   'history': {'successfulFinishedRuns': [],
                               'failedFinishedRuns':     []}}
    exp_err_msg = 'Job run failed - operation was not completed in 2 seconds.'

    # lots of responses, but only a few will trigger before timeout
    mock_replay = list((
        MockResponse(run_payload, 201),
        MockResponse({}, 404),
        MockResponse(job_payload, 200),
        MockResponse({}, 404),
        MockResponse(job_payload, 200),
        MockResponse({}, 404),
        MockResponse(job_payload, 200),
        MockResponse({}, 404),
        MockResponse(job_payload, 200)
    ))
    replay_session.queue(mock_replay)

    j = Jobs(default_url=mock_url)
    with pytest.raises(Exception) as error:
        j.run('myapp1', timeout=2)

    assert str(error.value) == exp_err_msg


def test_jobs_run_unknown_error(mock_url, replay_session):
    run_payload = {'id': 'myrun1'}
    exp_err_msg = 'Waiting for job run myrun1 to be finished, but getting HTTP status code 500'
    mock_replay = list((
        MockResponse(run_payload, 201),
        MockResponse({}, 500),
    ))
    replay_session.queue(mock_replay)

    j = Jobs(default_url=mock_url)
    with pytest.raises(HTTPError) as http_error:
        j.run('myapp1')
    assert str(http_error.value) == exp_err_msg
    assert len(replay_session.debug_cache) == 2


def test_jobs_run_details(mock_url, replay_session):
    run_payload = {'id': 'myrun1', 'foo': 'bar'}
    exp_method = 'GET'
    exp_url = 'https://localhost:443/service/metronome/v1/jobs/myjob' \
              '/runs/myrun1'
    replay_session.queue([MockResponse(run_payload, 200)])

    j = Jobs(default_url=mock_url)
    r = j.run_details('myjob', 'myrun1')
    assert r == run_payload
    assert replay_session.debug_cache[0] == (
        (exp_method, exp_url), {})


def test_jobs_run_stop(mock_url, replay_session):
    exp_method = 'POST'
    exp_url = 'https://localhost:443/service/metronome/v1/jobs/myjob' \
              '/runs/myrun1/actions/stop'
    replay_session.queue([MockResponse({}, 200)])

    j = Jobs(default_url=mock_url)
    j.run_stop('myjob', 'myrun1')
    assert replay_session.debug_cache[0] == (
        (exp_method, exp_url), {})
