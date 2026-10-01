# Security policy

## Scope

MediaClinic is a local desktop tool. It does not run a server (unless a LAN status page is explicitly enabled in the app) and it does not send your files anywhere by default. The sensitive items are:

- API keys (TMDb, OMDb) stored in the local settings file.
- Files you convert, transcribe or process, which stay on your machine.

## Handling of secrets

- Secrets are never part of this repository. `.gitignore` excludes configuration, settings, `.env`, key files, data and media.
- Some files in `archive/versions/` contain placeholder strings such as `sk-ant-...` in comments or tests. They are not real keys.
- The automated tests fail if a string that looks like a real Anthropic key is committed.

## Reporting a vulnerability

Please do not open a public issue for a security problem. Email **junqueira.ch@gmail.com** with the subject "Security: mediaclinic" and include the version, what you observed and how to reproduce it. I aim to answer within 7 days.

If you find a real API key anywhere in this repository or its history, tell me right away so I can revoke it.

## Supported versions

Only the latest release on the `main` branch is supported. Older versions in `archive/versions/` are kept for history and are not maintained.
