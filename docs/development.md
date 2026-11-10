
# Development

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
