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

from requests import HTTPError

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
    create_resp = dcos_api_session.jobs.create({
        'description': 'Test Metronome API regressions',
        'id':          'test.metronome',
        'run':         {
            'cmd':     'ls',
            'docker':  {'image': 'busybox:latest'},
            'cpus':    1,
            'mem':     512,
            'disk':    0,
            'user':    'nobody',
            'restart': {'policy': 'ON_FAILURE'}
        }
    })
    job_id = create_resp['id']
    details = dcos_api_session.jobs.details(job_id)
    log.info('Job details: {}'.format(details))

    # Test start/stop
    run_id = dcos_api_session.jobs.start(job_id)['id']
    r = dcos_api_session.jobs.run_details(job_id=job_id, run_id=run_id)
    assert r['status'] in ('INITIAL', 'STARTING')
    dcos_api_session.jobs.run_stop(job_id, run_id)

    # Test Run
    success, _, _ = dcos_api_session.jobs.run(job_id)
    assert success is True, 'Job failed!'

    dcos_api_session.jobs.destroy(job_id)

    # check to make sure the job is really destroyed
    try:
        dcos_api_session.jobs.details(job_id=job_id)
        assert False
    except HTTPError as http_e:
        assert http_e.response.status_code == 404


def test_packages(dcos_api_session):
    pack_api = dcos_api_session.package
    install_resp = pack_api.install('hello-world',
                                    version='2.1.0-0.31.2')
    installed_id = install_resp['appId']
    dcos_api_session.marathon.wait_for_app_deployment(
            installed_id, 1, True, False, 300)
    packs = pack_api.list()
    found = [p for p in packs['packages']
             if p['appId'] == installed_id]
    assert found
    pack_api.uninstall('hello-world', app_id=installed_id)

    pack_api.describe('hello-world')
    pack_api.search('hello*')
    pack_api.list_versions('hello-world')


def test_repository(dcos_api_session):
    listing = dcos_api_session.package.repository.list()
    assert 'repositories' in listing
    assert len(listing['repositories']) > 0
