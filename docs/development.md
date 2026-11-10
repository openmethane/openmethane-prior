
# Development

## Code review

Not every pull request benefits from a human review. The author of a pull
request decides whether it needs one, and says so on the first line of the
description, where it shows up in email notifications:

```markdown
**Review:** needed — changes science outputs: Safeguard data now follows the run's financial year
```

```markdown
**Review:** not needed — patch dependency updates, CI passing; merging Thursday unless someone objects
```

Always give a reason. The reason lets everyone else check the decision at a
glance, and shows over time whether these categories need adjusting.

### Review needed

- **Changes to science outputs.** Any change to the emissions the prior
  produces needs review, however small the fix that causes it.
- **Refactors that change structure or behaviour across more than one file.**
- **New concepts or features**, including new data sources, variables and
  methodology decisions.
- **Documentation changes.**
- **Changes that make a production run fail, or stop failing, where it didn't
  before.** Make sure whoever looks after production runs knows about these.

### Review not needed

- **Infrastructure changes** made by the person who looks after the
  infrastructure.
- **Mechanical changes**, such as small corrections and bug fixes whose
  correctness is established by tests, and tool-generated changes such as
  running a formatter. Being mechanical is what matters here, not size: a
  formatter run that touches every file is still mechanical.
- **Minor or patch dependency updates.** Major version updates need review.
- **Small changes to logging, warnings, types and project settings.**

### Science code isn't the same as science outputs

A change can touch science code without changing any outputs. For example,
it can fix a crash in a path that never produced results, or make the run
fail on bad input instead of producing NaNs. These changes don't need review,
but the reason has to give the evidence that the outputs don't change, not
just say so. If you can't write that sentence, choose "needed".

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
