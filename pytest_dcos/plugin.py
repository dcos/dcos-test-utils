import os

import pytest

from dcos_test_utils import dcos_api, enterprise, logger

logger.setup(os.getenv('LOG_LEVEL', 'DEBUG'))

log = logging.getLogger(__name__)

USER_HOME_DIR = os.path.join(os.path.expanduser('~'))


def order_fixtures(metafunc):
    """Pytest currently does not have a built-in way to ensure fixtures are called in a particular order
    https://github.com/pytest-dev/pytest/issues/1216#issuecomment-366496568
    """
    metafunc.fixturenames[:] = []
    orders = {name: getattr(definition[0].func, "order", None)
              for name, definition in metafunc._arg2fixturedefs.items()}
    ordered = {name: getattr(order, "args")[0] for name, order in orders.items() if order}
    unordered = [name for name, order in orders.items() if not order]
    first = {name: order for name, order in ordered.items() if order and order < 0}
    last = {name: order for name, order in ordered.items() if order and order > 0}
    merged = sorted(first, key=first.get) + unordered + sorted(last, key=last.get)
    metafunc.fixturenames.extend(merged)


def pytest_generate_tests(metafunc):
    order_fixtures(metafunc)


@pytest.fixture(scope='session')
def dcos_api_session_factory():
    is_enterprise = os.getenv('DCOS_ENTERPRISE', 'false').lower() == 'true'

    if is_enterprise:
        return enterprise.EnterpriseApiSession
    else:
        return dcos_api.DcosApiSession


@pytest.fixture(scope='session')
def dcos_api_session(dcos_api_session_factory):
    api = dcos_api_session_factory.create()
    api.wait_for_dcos()
    return api


def pytest_addoption(parser):
    parser.addoption(
        "--diagnostics",
        nargs='?',
        const=USER_HOME_DIR,
        default=None,
        help="Download a diagnostics bundle .zip file from the cluster at the end of the test run." +
             "Value is directory to put the file in. If no value is set, then it defaults to home directory.")


def _isdir(maybe_dir):
    """os.path.isdir except it won't raise an Exception on non str, int, byte input"""
    try:
        valid_dir = os.path.isdir(maybe_dir)
    except TypeError as e:
        valid_dir = False
    
    return valid_dir


@pytest.mark.order(-1)
@pytest.fixture(scope='session', autouse=True)
def make_diagnostics_report(dcos_api_session):
    """This fixture should be called first so that the diagnostics report code gets run last."""
    yield
    diagnostics_dir = config.getoption('--diagnostics')

    if diagnostics_dir is None:
        log.info('\nNot downloading diagnostics bundle for this session.')
    else:
        warning = '{} is not a directory. Writing diagnostics report to home directory {} instead.'.format(
            diagnostics_dir, USER_HOME_DIR)
        if not _isdir(diagnostics_dir):
            log.warn(warning)
            diagnostics_dir = USER_HOME_DIR

    log.info('Create diagnostics report for all nodes')
    dcos_api_session.health.start_diagnostics_job()

    last_datapoint = {
        'time': None,
        'value': 0
    }

    log.info('\nWait for diagnostics job to complete')
    dcos_api_session.health.wait_for_diagnostics_job(last_datapoint)

    log.info('\nWait for diagnostics report to become available')
    dcos_api_session.health.wait_for_diagnostics_reports()

    log.info('\nDownload zipped diagnostics reports')
    bundles = dcos_api_session.health.get_diagnostics_reports()
    dcos_api_session.health.download_diagnostics_reports(bundles, download_directory=diagnostics_dir)
