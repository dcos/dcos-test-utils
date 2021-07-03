from requests import HTTPError


class MockResponse:
    def __init__(self, json: dict, status_code: int):
        self._json = json
        self._status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        """Throw an HTTPErrer based on status code."""
        if self._status_code >= 400:
            raise HTTPError('Throwing test error', response=self)

    @property
    def status_code(self):
        return self._status_code

    @property
    def text(self):
        return str(self._json)


class MockEmitter:
    """Emulates a Session and responds with a queued response for each
    request made. If no responses are queued, the request will raise
    an error.

    A history of requests are held in a request cache and can be
    reviewed.
    """

    def __init__(self, mock_responses: list):
        self._mock_responses = mock_responses
        self._request_cache = list()

    def request(self, *args, **kwargs):
        self._request_cache.append((args, kwargs))
        return self._mock_responses.pop(0)

    def queue(self, response: list):
        """Add responses to the response queue.

        :param response: A list of responses
        :type response: list
        """
        self._mock_responses.extend(response)

    @property
    def headers(self):
        return dict()

    @property
    def cookies(self):
        return dict()

    @property
    def debug_cache(self):
        """Return the list of requests made during this session.

        Items in the cache are formatted:
            ((Method, URL), params)

        :return: a list of requests made to this session
        :rtype: list
        """
        return self._request_cache
