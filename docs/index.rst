.. dcos-test-utils documentation master file, created by
   sphinx-quickstart on Thu Mar 22 17:59:32 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to dcos-test-utils's documentation!
===========================================
``dcos-test-utils`` is a package for comprehensive interaction with DC/OS including:

* API client for making calls to DC/OS APIs
* simple wrapper for managing and communicating with the binary dcos-cli
* SSH client for simple one-off host-level changes
* Advanced SSH client for parallelized asynchronous command chains

.. toctree::
   :maxdepth: 3
   :caption: Modules:

   dcos_test_utils

Getting Started
===============
To get started writing code that leverages the DC/OS API, not much is needed:

.. code-block:: python

   from dcos_test_utils import dcos_api

   dcos_api_session = dcos_api.DcosApiSession.create()
   dcos_api_session.marathon.deploy_app({
        "id": "/sample_app",
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

   r = dcos_api_session.get('/service/marathon/v2/apps')
   assert len(r.json()) >= 1, 'No apps were found!'

If using a Mesosphere Enterprise DC/OS cluster, a different but functionally similar client is used:

.. code-block:: python

   from dcos_test_utils import enterprise

   dcos_api_session = enterprise.EnterpriseApiSession.create()
   r = dcos_api_session.secrets.get('/store')
   assert r.json()['array'][0]['initialized']


To learn more about how to configure these sessions, see:

* OSS DC/OS cluster constructor :func:`~dcos_test_utils.dcos_api.DcosApiSession.get_args_from_env`
* Mesosphere Enterpise DC/OS constructor :func:`~dcos_test_utils.enterprise.EnterpriseApiSession.get_args_from_env`


Using ``dcos-test-utils`` in pytest
===================================
This module includes a pytest plugin, ``pytest-dcos``, which includes the boilerplate to create a session in tests via a fixture called ``dcos_api_session``.

In your conftest.py file, include the following:

.. code-block:: python

   pytest_plugins = ["pytest-dcos"]

Now, there is no need for boilerplate to declare the client

.. code-block:: python

   def test_dcos_apps(dcos_api_sessoion):
       dcos_api_session.get('/').raise_for_status()

Note: this fixture introduces an additional environment variable called **DCOS_ENTERPRISE** which can be set to true or false (default to false)

For more advanced configuration at test time, this fixture can be overridden like so:

.. code-block:: python

   @pytest.fixture(scope='session')
   def dcos_api_session(dcos_api_session_factory, user_config):
       """ Overrides the dcos_api_session fixture to use
       exhibitor settings currently used in the cluster
       """
       args = dcos_api_session_factory.get_args_from_env()

       exhibitor_admin_password = None
       if user_config['exhibitor_admin_password_enabled'] == 'true':
           exhibitor_admin_password = user_config['exhibitor_admin_password']

       api = dcos_api_session_factory(
           exhibitor_admin_password=exhibitor_admin_password,
           **args)
       api.wait_for_dcos()
       return api


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
