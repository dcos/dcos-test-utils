""" Integration test (i.e. run against a real DC/OS cluster) for dcos-test-utils

Note: this tests expects a DC/OS cluster to already be provisioned.

At a minimum, the following environment variables should be set:
    DCOS_DNS_ADDRESS
    WAIT_FOR_HOSTS

Optionally, the following may be set as well:
    DCOS_ENTERPRISE=true # needed for EE testing
    DCOS_LOGIN_UNAME # needed for EE testing
    DCOS_LOGIN_PW # needed for EE testing
    MASTER_LIST # needed if WAIT_FOR_HOSTS=true
    SLAVE_LIST # needed if WAIT_FOR_HOSTS=true
    PUBLIC_SLAVE_LIST # needed if WAIT_FOR_HOSTS=true
"""
import logging

log = logging.getLogger(__name__)


def test_dcos_is_up(dcos_api_session):
    """ Simple test to ensure that this package can authenticate and inspect
    a DC/OS cluster via the pytest-dcos plugin
    """
    r = dcos_api_session.health.get('/units')
    r.raise_for_status()
    log.info('Got system health: ' + str(r.json()))


def test_marathon(dcos_api_session):
    app_id = "/test-utils-app"
    app_def = {
        "id": app_id,
        "cmd": "touch foobar && sleep 3600",
        "cpus": 0.5,
        "mem": 128.0,
        "instances": 1,
        "healthChecks": [
            {
                'protocol': 'COMMAND',
                'command': {'value': 'test -f foobar'},
                'gracePeriodSeconds': 10,
                'intervalSeconds': 5,
                'timeoutSeconds': 5,
                'maxConsecutiveFailures': 1,
            }
        ]
    }
    with dcos_api_session.marathon.deploy_and_cleanup(app_def):
        r = dcos_api_session.marathon.get('/v2/apps' + app_id)
        r.raise_for_status()
        assert r.status_code == 200
    r = dcos_api_session.marathon.get('/v2/apps' + app_id)
    assert r.status_code == 404


def test_jobs(dcos_api_session):
    job_id = dcos_api_session.jobs.create({
        'description': 'Test Metronome API regressions',
        'id': 'test.metronome',
        'run': {
            'cmd': 'ls',
            'docker': {'image': 'busybox:latest'},
            'cpus': 1,
            'mem': 512,
            'disk': 0,
            'user': 'nobody',
            'restart': {'policy': 'ON_FAILURE'}
        }
    })
    details = dcos_api_session.jobs.details(job_id)
    log.info('Job details: {}'.format(details))

    # Test start/stop
    run_id = dcos_api_session.jobs.start(job_id)
    r = dcos_api_session.jobs.get(
        'v1/jobs/{job_id}/runs/{run_id}'.format(job_id=job_id, run_id=run_id))
    assert r.json()['status'] == 'STARTING'
    r = dcos_api_session.jobs.post(
        'v1/jobs/{job_id}/runs/{run_id}/actions/stop'.format(job_id=job_id, run_id=run_id))
    r.raise_for_status()

    # Test Run
    status, _, _ = dcos_api_session.jobs.run(job_id)
    assert status == 'COMPLETED', 'Unexpected job status found'

    dcos_api_session.jobs.destroy(job_id)

    r = dcos_api_session.jobs.get('v1/jobs/{job_id}'.format(job_id=job_id))
    assert r.status_code == 404
