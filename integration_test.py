import os

import pytest


from dcos_test_utils import dcos_api, enterprise, helpers


@pytest.fixture
def dcos_api_session():
    is_enterprise = os.getenv('DCOS_ENTERPRISE', 'false').lower() == 'true'

    if is_enterprise:
        args = enterprise.EnterpriseApiSession.get_args_from_env()
        cluster_api = enterprise.EnterpriseApiSession(**args)
        if args['dcos_url'].startswith('https'):
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
    dcos_api_session.wait_for_up()
