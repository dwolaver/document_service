# Security policy

[Back to README](README.md)

## Supported versions

The project is before 1.0, so only the latest release receives fixes. Earlier releases don't.

| Version | Supported |
| --- | --- |
| Latest release | Yes |
| Earlier releases | No |

## Reporting a vulnerability

Please report a vulnerability privately, not in a public issue or pull request. On the repository's
**Security** tab, choose **Report a vulnerability**. GitHub's private vulnerability reporting keeps
the report visible only to you and the repository owner until it's resolved.

Say what's affected, how to reproduce it, and what an attacker could do with it. This is a personal
project, so replies are best effort, with no promised response time. Once a fix is released, the
advisory can be published with credit to you, if you'd like.

## What to do about a leaked secret

The repository is public, so a secret that reaches a commit, or is pushed, has to be treated as
leaked. Rotate it with whoever issued it, as well as removing it from the code. Removing it alone
isn't enough, because the commit history still holds it.

The pre-commit hook and the `secrets` check in CI scan for secrets with gitleaks, as described in
[CONTRIBUTING.md](CONTRIBUTING.md#lint-format-type-and-secret-checks). That section also says how to
ignore a finding that has been reviewed and isn't a secret.
