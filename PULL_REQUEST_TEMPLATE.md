## High-level description

What features does this change enable? What bugs does this change fix?


## Corresponding DC/OS tickets (obligatory)

These JIRA ticket(s) must be updated (ideally closed) in the moment this PR lands:

  - [DCOS-<number>](https://jira.mesosphere.com/browse/DCOS-<number>) Foo the Bar so it stops Bazzing.


## Related tickets (optional)

Other tickets related to this change:

  - [DCOS-<number>](https://jira.mesosphere.com/browse/DCOS-<number>) Foo the Bar so it stops Bazzing.


## Related `dcos-launch` and `dcos` PRs

Is this change going to be propagated up into another repo? Test the change by bumping the `dcos-test-utils` SHA to point to these changes to test it. Link the corresponding PRs here:


## Checklist for all PRs

  - [ ] Included a test which will fail if code is reverted but test is not. If there is no test please explain here:
  - [ ] Include a test in `dcos-integration-tests` in https://github.com/dcos/dcos or explain why this is not applicable:
  - [ ] Include a test in https://github.com/dcos/dcos-launch or explain why this is not applicable:

[Integration tests](https://teamcity.mesosphere.io/project.html?projectId=DcosIo_DcosTestUtils) were run and

  - [ ] Integration Test - Enterprise (link to job: )
  - [ ] Integration Test - Open (link to job: )


**PLEASE FILL IN THE TEMPLATE ABOVE** / **DO NOT REMOVE ANY SECTIONS ABOVE THIS LINE**


## Instructions and review process

**What is the review process and when will my changes land?**

All PRs require 2 approvals using GitHub's [pull request reviews](https://help.github.com/articles/about-pull-request-reviews/).

Reviewers should be:
* Developers who understand the code being modified.
* Developers responsible for code that interacts with or depends on the code being modified.

It is best to proactively ask for 2 reviews by @mentioning the candidate reviewers in the PR comments area. The responsibility is on the developer submitting the PR to follow-up with reviewers and make sure a PR is reviewed in a timely manner.