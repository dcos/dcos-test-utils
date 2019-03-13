import json
import os


xfailflake_test = """
    import pytest

    @pytest.mark.xfailflake(
        jira='DCOS-1337',
        reason='A reason',
        since='2019-01-25'
    )
    def test_xfailflake():
        # Test always fails, but the test suite should still pass.
        assert False
"""


def test_dcos_api_session_factory_fixture_imported(dcos_api_session_factory):
    pass


def test_xfailflake_no_report(testdir):
    testdir.makepyfile(xfailflake_test)

    result = testdir.runpytest()
    result.assert_outcomes(xfailed=1)

    assert not os.path.exists('xfailflake.json')


def test_xfailflake_write_report(testdir):
    testdir.makepyfile(xfailflake_test)

    result = testdir.runpytest("--xfailflake-report")
    result.assert_outcomes(xfailed=1)

    assert os.path.exists('xfailflake.json')

    report = json.load(open('xfailflake.json'))
    assert report == [
        {
            'module': 'test_xfailflake_write_report',
            'name': 'test_xfailflake',
            'path': os.path.join(os.getcwd(), 'test_xfailflake_write_report.py'),
            'xfailflake': {
                'jira': 'DCOS-1337',
                'reason': 'A reason',
                'since': '2019-01-25'
            }
        }
    ]
