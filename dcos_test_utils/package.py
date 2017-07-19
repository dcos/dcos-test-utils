"""Utilities for integration testing package management (https://github.com/dcos/cosmos)
"""

import logging



from dcos_test_utils.helpers import (ApiClientSession,
                                    RetryCommonHttpErrorsMixin)

log = logging.getLogger(__name__)


class Cosmos(RetryCommonHttpErrorsMixin, ApiClientSession):
    def __init__(self, default_url, default_os_user='root', session=None):
        super().__init__(default_url)
        if session is not None:
            self.session = session
        self.default_os_user = default_os_user

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
        response = self.post(endpoiont, json=data)
        log.info('Response from cosmos: {0}'.format(repr(response.json())))
        response.raise_for_status()
        return response

    def add_package(self, package_name, package_version):
        """Install a package using the cosmos packaging API
        
        Args:
            package_name: str
            package_version: str

        Returns:
            requests.response object

        Notes:
            Use Marathon.poll_marathon_for_app_deployment to check if the installed app deployed
            successfully (Need the appId from the response)
        """
        self._update_headers('install', response_version='2')
        package = {
            'packageName': package_name,
            'packageVersion': package_version
        }
        return self._post('install', package)

    def remove_package(self, package_name, app_id):
        """Uninstall a package using the cosmos packaging API

        Args:
            package_name: str
            app_id: str, should have leading slash

        Returns:
            requests.response object
        """
        self._update_headers('uninstall')
        package = {
            'packageName': package_name,
            'appId': app_id
        }
        return self._post('uninstall', package)

    def list_packages(self):
        """List all packages using the cosmos packaging API

        Returns:
            requests.response object
        """
        self._update_headers('list')
        return self._post('list', {})