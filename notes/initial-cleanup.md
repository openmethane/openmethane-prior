# Notes
After a read through of the codebase, 
I've jotted down some thought about the steps to clean up this repository.
Broadly it is easy enough to follow where things live, 
but the goal is to improve the consistency of this repo (and other OM repos). 
This should make it easier to work as a team 
and produce extensible software in the long-run.

The goal would be to make no science changes as part of this refactor, 
i.e. the output data should not change.

This clean-up might not be the #1 priority, but should go on the roadmap. 
Once we agree on the steps involved, 
we can create a set of GH issues to track the process.

## Steps:
* Run ruff over the codebase. This will coalesce on a common variable/function naming conventions
* Move inputs,intermediates,outputs into a data folder
* Migrate to the CR copier template to define the repository structure and workflows. 
    * This will add linting, CI, versioning etc
    * There will be some changes in the development workflow so there might be some training needed
    * We should discuss what steps work for the rest of the team. There are part of the template that we can pick and choose
    * We've documented the technical decisions that we have made which we can share
* Run CI periodically to double-check that the processing is always ready

## Questions for Peter
* What do you do with the outputs? Are they uploaded to `https://prior.openmethane.org`?
* Do you envision the need for more layers or different sources in future? The level of flux here may change how much structure is needed.
* Will type hints be useful anywhere?
    * We typically use type hints to provide some additional context for future contributor and some additional guardrails. These type hints are then checked as part of the CI.
    * This can be hard to add into an existing project and get good coverage. 
    * There might be useful places to add type hints and progressively enhance the coverage over time.

## Future steps
* Are there additional validation steps to perform. There could be a couple of notebooks that visualise and compare the new prior against a previous priors
    * What can be automated?
    * What needs a human in the loop?
    * Are there any additional things to archive with a prior release
* Develop and document a release process for the prior
* Documentation of each step and the required outputs