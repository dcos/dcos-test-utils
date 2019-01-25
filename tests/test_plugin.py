import json
import pytest


def test_dcos_api_session_factory_fixture_imported(dcos_api_session_factory):
    pass


@pytest.mark.xfailflake(
    jira='DCOS-1337',
    reason='A reason',
    since='2019-01-25'
)
def test_xfailflake():
    # Test always fails, but the test suite should still pass.
    assert False


def test_xfailflake_report():
    # This should be written out by the collect process.
    report = json.load(open('xfailflake.json'))
    assert report == [
        {
            'module': 'test_plugin',
            'name': 'test_xfailflake',
            'path': __file__,
            'xfailflake': {
                'jira': 'DCOS-1337',
                'reason': 'A reason',
                'since': '2019-01-25'
            }
        }
    ]
