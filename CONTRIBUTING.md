# Contributing to MediaClinic

Thanks for your interest. This is a personal project built with AI assistance (Claude) and improved in small, versioned steps, so contributions are welcome but reviewed carefully.

## Ways to help

- Report a bug or a confusing behaviour using the issue templates
- Suggest an improvement (scanner, settings subsystem, table)
- Send a pull request for a small, focused change

## Before you start

1. Open an issue first for anything bigger than a small fix, so we agree on the approach.
2. Python 3.9 or newer, Windows is the tested platform.
3. Run the checks locally:

```
pip install pytest
python -m pytest tests
```

## Pull request checklist

- [ ] The change is small and does one thing
- [ ] `python -m pytest tests` passes
- [ ] No secrets, personal paths, corpus files, transcripts or media are included
- [ ] The README or docs are updated if behaviour changed

## Working with an AI assistant

If you use an AI tool to prepare a change, please say so in the pull request and test the result on real data yourself. The project values small, reviewable diffs, logging that explains what happened, and root-cause fixes over patches.

## Code of conduct

Be respectful and constructive. Assume good intent.
