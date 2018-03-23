""" Utilities for integration testing metronome in a deployed DC/OS cluster
"""
import logging

import retrying
from requests import HTTPError

from dcos_test_utils.helpers import (ApiClientSession,
                                     RetryCommonHttpErrorsMixin)

REQUIRED_HEADERS = {'Accept': 'application/json, text/plain, */*'}
log = logging.getLogger(__name__)


class Jobs(RetryCommonHttpErrorsMixin, ApiClientSession):
    def __init__(self, default_url, session=None):
        super().__init__(default_url)
        if session is not None:
            self.session = session
        self.session.headers.update(REQUIRED_HEADERS)
        self._api_version = '/v1'

    def wait_for_run(self, job_id: str, run_id: str, timeout=600):
        """Wait for a given run to complete or timeout seconds to
        elapse.

        :param job_id: Job ID
        :type job_id: str
        :param run_id: Run ID
        :type run_id: str
        :param timeout: Time in seconds to wait before giving up
        :type timeout: int
        :return: None

        """

        @retrying.retry(wait_fixed=1000, stop_max_delay=timeout * 1000,
                        retry_on_result=lambda ret: ret is False,
                        retry_on_exception=lambda x: False)
        def _wait_for_run_completion(j_id: str, r_id: str) -> bool:
            rc = self.get('{api}/jobs/{jid}/runs/{rid}'.format(
                    api=self._api_version,
                    jid=j_id,
                    rid=r_id))
            # 404 means the run is complete and this is done
            # 200 means the run is still in progress
            # anything else is a problem and should not happen
            if rc.status_code == 404:
                log.info('Job run {} finished.'.format(r_id))
                return True
            elif rc.status_code == 200:
                log.info('Waiting on job run {} to finish.'.format(r_id))
                return False

            rc.raise_for_status()
            raise HTTPError('Unexpected status code for job run {}:'
                            ' {}'.format(r_id, rc.status_code))

        try:
            # wait for the run to complete and then return the
            # run's result
            _wait_for_run_completion(job_id, run_id)
        except retrying.RetryError as ex:
            raise Exception("Job run failed - operation was not "
                            "completed in {} seconds.".format(timeout)) from ex

    def details(self, job_id: str, history=False) -> dict:
        """Get the details of a specific Job.

        :param job_id: Job ID
        :type job_id: str
        :param history: Include embedded history in details
        :type history: bool
        :return: Job details as JSON
        :rtype: dict

        """
        params = {'embed': 'history'} if history else None
        r = self.get(
                '{api}/jobs/{job_id}'.format(api=self._api_version,
                                             job_id=job_id),
                params=params)
        r.raise_for_status()
        return r.json()

    def create(self, job_definition: dict) -> dict:
        """Create a new job with given definition.

        :param job_definition: Job definition
        :type job_definition: dict
        :return: Response from Jobs service as JSON
        :rtype: dict

        """
        r = self.post('{api}/jobs'.format(api=self._api_version),
                      json=job_definition)
        r.raise_for_status()
        return r.json()

    def destroy(self, job_id: str):
        """Delete an existing job and all data.

        :param job_id: Job ID
        :type job_id: str

        """
        r = self.delete('{api}/jobs/{job_id}'.format(
                api=self._api_version, job_id=job_id),
                params={'stopCurrentJobRuns': 'true'})
        r.raise_for_status()

    def start(self, job_id: str) -> dict:
        """Create a run and return the Run.

        :param job_id: Job ID
        :type job_id: str
        :return: Run creation response from Jobs service
        :rtype: dict

        """
        r = self.post('{api}/jobs/{job_id}/runs'.format(
                api=self._api_version,
                job_id=job_id))
        r.raise_for_status()
        r_json = r.json()

        log.info("Started job {}, run id {}".format(job_id, r_json['id']))
        return r_json

    def run(self, job_id: str, timeout=600) -> (bool, dict, dict):
        """Create a run, wait for it to finish, and return whether it was
        successful and the run itself.

        This will run the job immediately and block until
        the run is complete.
        """
        run_json = self.start(job_id)
        run_id = run_json['id']
        self.wait_for_run(job_id, run_id, timeout)

        result = self.details(job_id, history=True)
        history = result['history']

        for res, field in ((True, 'successfulFinishedRuns'),
                           (False, 'failedFinishedRuns')):
            run = [r for r in history[field] if r['id'] == run_id]
            if run:
                return res, run[0], result

        return False, None, result
