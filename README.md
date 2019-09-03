# dcos-test-utils1

This module is the backend for the `dcos_api_session` object used as a test harness in the [DC/OS integration tests](http://github.com/dcos/dcos/tree/master/packages/dcos-integration-test/extra). More specifically, this module provides utilities that allow:
* Storing common URL elements repeated between requests to the same service
* Providing a DC/OS-authenticated API Client that can be wrapped and composed with API Mixins
* Helper methods for managing Marathon and other DC/OS services

To read more about how to use this library, [Read the Docs](https://dcos-test-utils.readthedocs.io/en/latest/)

## System Requirements
* python 3.5
* local SSH client at /usr/bin/ssh

### Using the library interactively
```
python3.5 -m venv env
. env/bin/activate
pip3 install -r requirements.txt
python setup.py develop
```

## Running Unit Tests with tox
Simply run `tox` and the following will be executed:
* flake8 for style errors
* pytest for unit tests

Note: these can be triggered individually by supplying the `-e` option to `tox`


## Running Integration Tests with Tox
Integration tests are not run by default as they require a real DC/OS cluster which is externally provided.

To launch a cluster, check out [dcos-launch](https://github.com/dcos/dcos-launch), which can be used like so (on a GNU/Linux system):
```
#!/bin/bash
wget https://downloads.dcos.io/dcos-launch/bin/linux/dcos-launch
chmod +x dcos-launch
cat <<EOF > config.yaml
---
launch_config_version: 1
deployment_name: YOUR-DEPLOYMENT-NAME-HERE
template_url: https://s3.amazonaws.com/downloads.dcos.io/dcos/testing/master/cloudformation/single-master.cloudformation.json
provider: aws
aws_region: us-west-2
key_helper: true
template_parameters:
    AdminLocation: 0.0.0.0/0
    PublicSlaveInstanceCount: 1
    SlaveInstanceCount: 1
ssh_user: core
EOF

dcos-launch create

dcos-launch wait

export DCOS_DNS_ADDRESS=http://`dcos-launch describe | jq -r .masters[0].public_ip`

# if WAIT_FOR_HOSTS is set to `true`, then MASTER_LIST, SLAVE_LIST, and PUBLIC_SLAVE list
# must be set before starting the test
export WAIT_FOR_HOSTS=false

tox -e py35-integration-tests

dcos-launch-delete
```
