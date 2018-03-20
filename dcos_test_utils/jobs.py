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
    
    @staticmethod
    def _run_from_history(run_id: str, history: dict) -> dict or None:
        """Return a run item from a list of run items. This cas be
        used with results from embedded history.
        """
        r = [run for run in history if run['id'] == run_id]
        if r:
            return r[0]
        return None
    
    def details(self, job_id: str, history=False) -> dict:
        """Get the details of a specific Job."""
        params = {'embed': 'history'} if history else None
        r = self.get('{api}/jobs/{job_id}'
                     .format(api=self._api_version, job_id=job_id)
                     , params=params)
        r.raise_for_status()
        return r.json()
    
    def create(self, job_definition: dict) -> str:
        """Create a new job with given definition."""
        r = self.post('{api}/jobs'.format(api=self._api_version), json=job_definition)
        r.raise_for_status()
        return r.json()['id']
    
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
    
    def run(self, job_id: str, timeout=600) -> (bool, dict, dict):
        """Create a run, wait for it to finish, and return whether it was
        successful and the run itself.
        
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
            result = self.details(job_id, history=True)
            result_history = result['history']
            
            for res, field in ((True, 'successfulFinishedRuns'),
                               (False, 'failedFinishedRuns')):
                run = self._run_from_history(run_id,
                                             result_history[field])
                if run:
                    return res, run, result
            
            return False, None, result
        except retrying.RetryError as ex:
            raise Exception("Job run failed - operation was not "
                            "completed in {} seconds.".format(timeout)) from ex
