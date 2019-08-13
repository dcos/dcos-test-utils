import os
import tempfile
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID

import pytest
import requests
import responses
from requests import HTTPError

from dcos_test_utils import dcos_api
from dcos_test_utils.diagnostics import Diagnostics
from dcos_test_utils.helpers import check_json


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


@responses.activate
@patch('uuid.uuid1', return_value=UUID('f053c58c-b9ce-11e9-8c5b-38d54714bf36'))
def test_start_diagnostics_job(mock_uuid):
    responses.add(responses.PUT,
                  'http://leader.mesos/system/health/v1/diagnostics/f053c58c-b9ce-11e9-8c5b-38d54714bf36',
                  json={
                      'id': 'f053c58c-b9ce-11e9-8c5b-38d54714bf36',
                      'status': 'Started',
                      'started_at': '2019-08-05T11:31:53.238640571Z',
                  })

    args = dcos_api.DcosApiSession.get_args_from_env()
    dcos_api_session = dcos_api.DcosApiSession(**args)

    health_url = dcos_api_session.default_url.copy(
        path='system/health/v1',
    )

    diagnostics = Diagnostics(
        default_url=health_url,
        masters=[],
        all_slaves=[],
        session=dcos_api_session.copy().session,
    )

    response = diagnostics.start_diagnostics_job()

    assert check_json(response) == {
        'id': 'f053c58c-b9ce-11e9-8c5b-38d54714bf36',
        'status': 'Started',
        'started_at': '2019-08-05T11:31:53.238640571Z',
    }


@responses.activate
@patch('uuid.uuid1', return_value=UUID('f053c58c-b9ce-11e9-8c5b-38d54714bf36'))
def test_start_diagnostics_job_error(mock_uuid):
    responses.add(responses.PUT,
                  'http://leader.mesos/system/health/v1/diagnostics/f053c58c-b9ce-11e9-8c5b-38d54714bf36',
                  json={
                      'code': 507,
                      'error': 'could not create bundle f053c58c-b9ce-11e9-8c5b-38d54714bf36 workdir',
                  }, status=507)

    args = dcos_api.DcosApiSession.get_args_from_env()
    dcos_api_session = dcos_api.DcosApiSession(**args)

    health_url = dcos_api_session.default_url.copy(
        path='system/health/v1',
    )

    diagnostics = Diagnostics(
        default_url=health_url,
        masters=[],
        all_slaves=[],
        session=dcos_api_session.copy().session,
    )

    with TestCase.assertRaises(TestCase(), HTTPError):
        response = diagnostics.start_diagnostics_job()
        check_json(response)


@responses.activate
def test_wait_for_diagnostics_job():
    responses.add(responses.GET,
                  'http://leader.mesos/system/health/v1/diagnostics',
                  json=[{'id': '123e4567-e89b-12d3-a456-426655440000', 'status': 'Done'},
                        {'id': 'f053c58c-b9ce-11e9-8c5b-38d54714bf36', 'status': 'Started'},
                        ])
    responses.add(responses.GET,
                  'http://leader.mesos/system/health/v1/diagnostics',
                  json=[{'id': '123e4567-e89b-12d3-a456-426655440000', 'status': 'Done'},
                        {'id': 'f053c58c-b9ce-11e9-8c5b-38d54714bf36', 'status': 'InProgress'}])
    responses.add(responses.GET,
                  'http://leader.mesos/system/health/v1/diagnostics',
                  json=[{'id': '123e4567-e89b-12d3-a456-426655440000', 'status': 'Done'},
                        {'id': 'f053c58c-b9ce-11e9-8c5b-38d54714bf36', 'status': 'Done'}])

    args = dcos_api.DcosApiSession.get_args_from_env()
    dcos_api_session = dcos_api.DcosApiSession(**args)

    health_url = dcos_api_session.default_url.copy(
        path='system/health/v1',
    )

    diagnostics = Diagnostics(
        default_url=health_url,
        masters=[],
        all_slaves=[],
        session=dcos_api_session.copy().session,
    )

    assert diagnostics.wait_for_diagnostics_job({})


@responses.activate
def test_get_reports():
    responses.add(responses.GET,
                  'http://leader.mesos/system/health/v1/diagnostics',
                  json=[{'id': '123e4567-e89b-12d3-a456-426655440000', 'status': 'Started'},
                        {'id': '123e4567-e89b-12d3-a456-426655440000', 'status': 'Deleted'},
                        {'id': 'f053c58c-b9ce-11e9-8c5b-38d54714bf36', 'status': 'Done'}])

    args = dcos_api.DcosApiSession.get_args_from_env()
    dcos_api_session = dcos_api.DcosApiSession(**args)

    health_url = dcos_api_session.default_url.copy(
        path='system/health/v1',
    )

    diagnostics = Diagnostics(
        default_url=health_url,
        masters=[],
        all_slaves=[],
        session=dcos_api_session.copy().session,
    )

    assert diagnostics.get_diagnostics_reports() == ['123e4567-e89b-12d3-a456-426655440000',
                                                     'f053c58c-b9ce-11e9-8c5b-38d54714bf36']


@responses.activate
def test_download_reports():
    responses.add(responses.GET,
                  'http://leader.mesos/system/health/v1/diagnostics/f053c58c-b9ce-11e9-8c5b-38d54714bf36/file',
                  content_type='application/zip', body='OK')

    args = dcos_api.DcosApiSession.get_args_from_env()
    dcos_api_session = dcos_api.DcosApiSession(**args)

    health_url = dcos_api_session.default_url.copy(
        path='system/health/v1',
    )

    diagnostics = Diagnostics(
        default_url=health_url,
        masters=['leader.mesos'],
        all_slaves=[],
        session=dcos_api_session.copy().session,
    )

    with tempfile.TemporaryDirectory() as tmpdirname:
        diagnostics.download_diagnostics_reports(['f053c58c-b9ce-11e9-8c5b-38d54714bf36'], tmpdirname)
        with open(os.path.join(tmpdirname, 'f053c58c-b9ce-11e9-8c5b-38d54714bf36'), 'r') as f:
            assert f.read() == 'OK'
