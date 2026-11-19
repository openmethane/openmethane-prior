
# Development

## Code review

Review isn't only for catching bugs. It keeps the team aware of how the
project is changing and builds agreement on decisions. Not every pull request
benefits from that. The author of a pull request decides whether it needs a
human review, and says so on the first line of the description, where it
shows up in email notifications:

```markdown
**Review:** needed — changes science outputs: Safeguard data now follows the run's financial year
```

```markdown
**Review:** not needed — patch dependency updates, CI passing; merging Thursday unless someone objects
```

Always give a reason. The reason lets everyone else check the decision at a
glance, and shows over time whether these categories need adjusting.

The lists below are a guide, not rules, and some judgement is still needed.
When a change doesn't clearly fit, ask: would the rest of the team want to
know about this, or have a say in it? If so, it needs review.

### Review needed

- **Changes to science outputs.** Any change to the emissions the prior
  produces needs review, however small the fix that causes it.
- **Refactors that change structure or behaviour across more than one file.**
- **New concepts or features**, including new data sources, variables and
  methodology decisions.
- **Documentation changes.** If something is worth documenting, it's worth
  the rest of the team knowing about it and agreeing with it. This doesn't
  include fixes to typos, grammar or formatting, which are mechanical changes.
- **Changes that make a production run fail, or stop failing, where it didn't
  before.** Make sure whoever looks after production runs knows about these.

### Review not needed

- **Infrastructure changes** made by the person who looks after the
  infrastructure.
- **Mechanical changes**, such as small corrections and bug fixes whose
  correctness is established by tests, tool-generated changes such as
  running a formatter, and fixes to typos, grammar or formatting in
  documentation. Being mechanical is what matters here, not size: a
  formatter run that touches every file is still mechanical.
- **Minor or patch dependency updates.** Major version updates need review.
- **Small changes to logging, warnings, types and project settings.**

### Science code isn't the same as science outputs

A change can touch science code without changing any outputs. For example,
it can fix a crash in a path that never produced results, or make the run
fail on bad input instead of producing NaNs. These changes don't need review,
but the reason has to give the evidence that the outputs don't change, not
just say so. If you can't write that sentence, choose "needed".

### Agent review before a pull request

If you use an agent such as Claude Code to prepare a change, `CLAUDE.md`
asks it to review anything that isn't mechanical with a fresh reviewer
(`.claude/agents/reviewer.md`) before it opens the pull request. The agent
fixes clear problems itself and brings anything else to you. For riskier
changes it offers a second, independent review. Each review costs tokens, so
you can tell the agent to skip it. This is part of preparing the change, not a
substitute for human review: it doesn't change whether a pull request needs
review.

### Not needed doesn't mean merged immediately

For a "not needed" pull request, say when you'll merge it. This gives
everyone a chance to ask for a review before then. Anyone can switch a pull
request to "needed", and then it waits for a review as usual.

### Examples

| Pull request | First line |
|---|---|
| [#232](https://github.com/openmethane/openmethane-prior/pull/232) | **Review:** not needed — bug fix with a regression test; non-square domains used to crash, and square-domain outputs are unchanged |
| [#233](https://github.com/openmethane/openmethane-prior/pull/233) | **Review:** not needed — automated `ruff format` and safe autofixes across 122 files, plus a CI check; no behaviour change |
| [#245](https://github.com/openmethane/openmethane-prior/pull/245) | **Review:** not needed — silences warnings that carry no information; test and project settings only |
| [#246](https://github.com/openmethane/openmethane-prior/pull/246) | **Review:** not needed — bug fix with tests; the run now fails on missing weights instead of producing NaN; no current outputs change |
| [#227](https://github.com/openmethane/openmethane-prior/pull/227) | **Review:** needed — new feature: an inventory jurisdiction mask on the domain, plus a methodology decision and docs |
| [#240](https://github.com/openmethane/openmethane-prior/pull/240) | **Review:** needed — changes science outputs: Safeguard data now follows the run's financial year |

#246 is "not needed" because no current outputs change. Because production
runs can now fail where they didn't before, the person who looks after
production runs should still hear about it.

## Docker images

A docker image will be built and made available through the GitHub Container
Registry for every push to `main` branch, as well as each PR that changes
more than documentation.

See https://github.com/orgs/openmethane/packages for a list of available
packages.

## Continuous integration

The `CI` and `Build docker image` workflows skip their tests, package build and
image build when a pull request (or push to `main`) touches only documentation,
agent instructions or other markdown, including changelog fragments. The jobs
are skipped rather than the workflow, so the required `tests` and `check-build`
checks still report success. `.github/ci-paths.yml` lists the paths that need
checks. Tags and manual runs always run everything.

### Input data cache

To keep runs fast, the `tests` job restores downloaded inputs from a shared
cache, `test-data-cache`, instead of fetching them every time. The cache is
only refreshed when a pull request labelled `input-updates` is merged.

Add the `input-updates` label to a pull request that changes inputs or how
they're fetched, such as:

- adding a data source, or changing a source's URL or version
- changing how an input is downloaded or parsed
- editing a Google Sheet the prior reads, when the pull request depends on the
  edit

On a labelled pull request, CI skips the cache and fetches every input, so the
tests run against the live data, even if the pull request only changes
markdown. Adding the label re-runs CI, but removing it doesn't. When the pull
request is merged with the label still on, the CI run on `main` deletes the
cache, fetches every input and saves a fresh cache.

Without the label, CI keeps testing against the inputs as they were when the
cache was saved, so a change to input fetching may never run in CI, and a
change to the data itself can go unnoticed.

## Preparing a release

When changes have been merged into `main` which should be used in prod or
released to the public, we follow a simple release process.

Visit the openmethane-prior [Actions](https://github.com/openmethane/openmethane-prior/actions)
page and select the
"[Create release](https://github.com/openmethane/openmethane-prior/actions/workflows/release.yaml)"
action. Click the "Run workflow" button, leaving `main` as the selected branch.

Based on the content of the `changelog` folder in `main`, determine whether
this is a patch, minor or major release. Select that value in the workflow
dialogue, and click "Run workflow".

This workflow will:
- update the project version to the next semver version
- tag the repo with a `vX.Y.Z` tag
- update `docs/changelog.md` with the contents of the changelog items
- prepare a GitHub Release with the changelog content
- build and push a container image with the same version tag
