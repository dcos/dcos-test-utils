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
import os

import pytest


from dcos_test_utils import dcos_api, enterprise, helpers, logger


logger.setup(os.getenv('LOG_LEVEL', 'DEBUG'))


@pytest.fixture
def dcos_api_session():
    is_enterprise = os.getenv('DCOS_ENTERPRISE', 'false').lower() == 'true'

    if is_enterprise:
        args = enterprise.EnterpriseApiSession.get_args_from_env()
        cluster_api = enterprise.EnterpriseApiSession(**args)
        cluster_api.set_ca_cert()
    else:
        args = dcos_api.DcosApiSession.get_args_from_env()
        cluster_api = dcos_api.DcosApiSession(
            auth_user=dcos_api.DcosUser(helpers.CI_CREDENTIALS),
            **args)
    return cluster_api


def test_dcos_is_up(dcos_api_session):
    """ Simple test to ensure that this package can authenticate and inspect
    a DC/OS cluster
    """
    dcos_api_session.wait_for_dcos()
