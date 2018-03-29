"""Utilities for integration testing package management (https://github.com/dcos/cosmos)
"""

import logging

from dcos_test_utils import helpers

log = logging.getLogger(__name__)


class Cosmos(helpers.RetryCommonHttpErrorsMixin, helpers.ApiClientSession):
    """ Specialized client for interacting with Cosmos (universe gateway) functionality

    :param default_url: URL of the jobs service to bind to
    :type default_url: helpers.Url
    :param session: option session to bootstrap this session with
    :type session: requests.Session
    """
    def __init__(self, default_url: helpers.Url, session=None):
        super().__init__(default_url)
        if session is not None:
            self.session = session

    def _update_headers(self, endpoint, request_version='1', response_version='1'):
        """Set the Content-type and Accept headers

        Args:
            request_version: str Version number of the cosmos API
            response_version: str Version number of the cosmos API
            endpoint: str cosmos API endpoint
        Returns:
            None
        """
        media_type = "application/vnd.dcos.package." + endpoint + \
            "-{action}+json;charset=utf-8;" + \
            "version=v{version}"
        self.session.headers.update({
            'Content-type': media_type.format(action="request", version=request_version),
            'Accept': media_type.format(action="response", version=response_version)
        })

    def _post(self, endpoint, data):
        response = self.post(endpoint, json=data)
        log.info('Response from cosmos: {0}'.format(repr(response.text)))
        response.raise_for_status()
        return response

    def install_package(self, package_name, package_version=None, options=None, app_id=None):
        """Install a package using the cosmos packaging API

        Args:
            package_name: str
            package_version: str
            options: JSON dict
            appId: str

        Returns:
            requests.response object

        Notes:
            Use Marathon.poll_marathon_for_app_deployment to check if the installed app deployed
            successfully (Need the appId from the response)
        """
        self._update_headers('install', response_version='2')
        package = {
            'packageName': package_name
        }
        if package_version is not None:
            package.update({'packageVersion': package_version})
        if options is not None:
            package.update({'options': options})
        if app_id is not None:
            package.update({'appId': app_id})
        return self._post('/install', package)

    def uninstall_package(self, package_name, app_id=None):
        """Uninstall a package using the cosmos packaging API

        Args:
            package_name: str
            app_id: str, should have leading slash

        Returns:
            requests.response object
        """
        self._update_headers('uninstall')
        package = {
            'packageName': package_name
        }
        if app_id is not None:
            package.update({'appId': app_id})
        return self._post('/uninstall', package)

    def list_packages(self):
        """List all packages using the cosmos packaging API

        Returns:
            requests.response object
        """
        self._update_headers('list')
        return self._post('/list', {})


class Repository(Cosmos):
    def __init__(self, default_url, session=None):
        super().__init__(default_url, session=session)

    def add(self, name: str, uri: str, index: int = None) -> dict:
        """Add a package repository. If `index` is 0 it will be added to
        the top of the repository list.

        :param name: Repository name
        :type name: str
        :param uri: Repository URI
        :type uri: str
        :param index: Position in repository list starting at 0
            (lower is higher priority)
        :type index: int
        :return: JSON response
        :rtype: dict
        """
        params = {
            'uri':  uri,
            'name': name,
        }
        if index is not None and type(index) == int:
            params['index'] = index

        self._update_headers('repository.add')
        r = self._post('/add', params)
        return r.json()

    def delete(self, name: str = None, uri: str = None) -> dict:
        """Delete the package repository with given name.

        :param name: Repository name
        :type name: str
        :param uri: Repository URI
        :type uri: str
        :return: JSON response
        :rtype: dict
        """
        params = {}
        if name:
            params['name'] = name
        if uri:
            params['uri'] = uri

        self._update_headers('repository.delete')
        r = self._post('/delete', params)
        return r.json()

    def list(self) -> dict:
        """Get list of package repositories.

        :return: JSON response
        :rtype: dict
        """
        self._update_headers('repository.list')
        r = self._post('/list', {})
        return r.json()


class Package(Cosmos):
    def __init__(self, default_url, session=None):
        super().__init__(default_url, session=session)
        self._versions = {
            'request_version':  '1',
            'response_version': '1',
        }

    def _make_request(self, resource: str, params: dict,
                      versions: dict = None) -> dict:
        """Every request to /packaging has the same couple of steps.
        This puts them in one place instead of duplicating efforts.

        :param versions: Request and Response versions
        :type versions: dict
        :param resource: Package resource (list, install, etc)
        :type resource: str
        :param params: POST parameters for the resource
        :type params: dict
        :return: JSON response
        :rtype: dict
        """
        kw = versions if versions else self._versions
        self._update_headers(resource, **kw)
        r = self._post("/{}".format(resource), params)
        return r.json()

    def list(self, name: str = None, app_id: str = None) -> dict:
        """List installed packages.

        :param app_id: App Id (optional)
        :type app_id: str
        :param name: Package name (optional)
        :type name: str
        :return: installed packages
        :rtype: dict
        """
        params = {}
        if app_id:
            params['appId'] = app_id
        if name:
            params['packageName'] = name
        return self._make_request('list', params)

    def install(self, name: str, version: str = None,
                options: dict = None, app_id: str = None) -> dict:
        """Install a Universe package.

        :param name: Package name
        :type name: str
        :param version: Package version string (optional)
        :type version: str
        :param options: Package installation options (optional)
        :type options: dict
        :param app_id: App ID (optional)
        :type app_id: str
        :return: JSON response
        :rtype: dict
        """
        params = {
            'packageName': name,
        }
        if version is not None:
            params['packageVersion'] = version
        if options and type(options) == dict:
            params['options'] = options
        if app_id:
            params['appId'] = app_id
        return self._make_request('install', params,
                                  {'response_version': '2', })

    def uninstall(self, name: str, app_id: str = None) -> dict:
        """Uninstall a Universe package

        :param name: Package name
        :type name: str
        :param app_id: App ID (optional)
        :type app_id: str
        :return: JSON response
        :rtype: dict
        """
        params = {
            'packageName': name,
        }
        if app_id:
            params['appId'] = app_id
        return self._make_request('uninstall', params)

    def describe(self, name: str, version: str = None) -> dict:
        """Show information about a package.

        :param name: Package name
        :type name: str
        :param version: Specific package version (optional)
        :type version: str
        :return: JSON response
        :rtype: dict
        """
        params = {
            'packageName': name,
        }
        if version:
            params['packageVersion'] = version
        return self._make_request('describe', params)

    def search(self, query: str = None) -> dict:
        """List all packages with a given partial (query).

        :param query: Partial package name
        :type query: str
        :return: JSON response
        :rtype: dict
        """
        params = {}
        if query:
            params['query'] = query
        return self._make_request('search', params)

    def list_versions(self, name: str,
                      include_versions: bool = False) -> dict:
        """List all available versions for a given package.

        :param name: Package name
        :type name: str
        :param include_versions: Include version details
        :type include_versions: bool
        :return: JSON response
        :rtype: dict
        """
        params = {
            'packageName':            name,
            'includePackageVersions': include_versions,
        }
        return self._make_request('list-versions', params)

    @property
    def repository(self):
        repo_path = '{}/repository'.format(self.default_url.path)
        return Repository(
                default_url=self.default_url.copy(path=repo_path),
                session=self.session)
