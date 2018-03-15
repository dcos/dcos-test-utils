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
        self._api_version = 'v1'
    
    def create(self, job_definition):
        """Create a new job with given definition."""
        r = self.post('{api}/jobs'.format(api=self._api_version), json=job_definition)
        r.raise_for_status()
    
    def destroy(self, job_id: str):
        """Delete an existing job and all data."""
        r = self.delete('{api}/jobs/{job_id}'.format(
                api=self._api_version, job_id=job_id),
                params={'stopCurrentJobRuns': 'true'})
        r.raise_for_status()
    
    def start(self, job_id: str) -> str:
        """Create a run and return the Run ID."""
        r = self.post('{api}/jobs/{job_id}/runs'.format(
                api=self._api_version,
                job_id=job_id))
        r.raise_for_status()
        r_json = r.json()
        
        # a run is given an ID
        run_id = r_json['id']
        log.info("Started job {}, run id {}".format(job_id, run_id))
        return run_id
    
    def run(self, job_id: str, timeout=600) -> bool:
        """Create a run and wait for it to finish.
        
        This will run the job immediately and block until
        the run is complete.
        """
        run_id = self.start(job_id)
        
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
                return True
            elif rc.status_code == 200:
                return False
            
            rc.raise_for_status()
            raise HTTPError('Unexpected status code: {}'.format(rc.status_code))
        
        try:
            return _wait_for_run_completion(job_id, run_id)
        except retrying.RetryError as ex:
            raise Exception("Job run failed - operation was not "
                            "completed in {} seconds.".format(timeout)) from ex
