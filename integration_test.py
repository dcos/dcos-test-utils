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
    r = dcos_api_session.health.get('units')
    r.raise_for_status()
    log.info('Got system health: ' + str(r.json()))
