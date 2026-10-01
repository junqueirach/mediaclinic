# MediaClinic

**A library health tool for Kodi: scan your movie folders, find broken or incomplete metadata and artwork, and fix them.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) ![Python](https://img.shields.io/badge/Python-3.9%2B-blue) ![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

## What it does

MediaClinic reads a media library and shows one table with the state of every title:

- **NFO and XML validation** with clear error reporting and an "open file" shortcut
- **Artwork checks**: poster, folder, fanart and backdrop count against size and proportion rules you set
- **Genre tools**: normalise genres, split merged tags such as `Family/Fantasy`, sort and filter
- **Ratings sync** from TMDb and OMDb (you supply your own API keys)
- **Technical checks** with FFprobe and FFmpeg: quality, language, subtitles
- **Improvements report** that lists what to fix, per title
- **Safe edits**: automatic silent backup of every NFO/XML before writing, with backup folder maintenance
- Keyboard shortcuts, jump-to-letter, sortable columns, dark theme, rotating logs

## Quick start

```
python mediaclinic.py
```

Run it from the folder that contains the `settings_*.py` files. Settings are saved locally and are not part of this repository. See [docs/help](docs/help) for the in-app help pages.

## Engineering notes

This project is the clearest example of working with an AI under a written contract:

- [`docs/CLAUDE_RULES.md`](docs/CLAUDE_RULES.md) defines module boundaries, the save chain, naming rules and a safety checklist that every AI-edited change must respect
- `settings_schema.json` plus `tests/settings_test_harness.py` check the settings subsystem after every change
- The settings code is split into model, controller, context and dialog modules so the AI can edit one part without breaking another
- About 11,700 lines of Python; 30 tracked versions in `archive/versions/`, starting from a 12 KB folder scanner

---

## How this was built

Built with **Claude (Anthropic)** as the coding partner. I wrote the requirements and the revision prompts, tested every build on real data, and decided what to fix next. The `archive/versions/` folder keeps every earlier release so the iteration history is visible.

**Security note:** the app stores any API keys you enter in a local settings file outside this repository. `.gitignore` excludes config and settings files so keys are never committed.

## Licence

MIT. See [LICENSE](LICENSE).

## Author

Luiz Junqueira - [junqueira.ch](https://www.junqueira.ch) - [LinkedIn](https://www.linkedin.com/in/luizjunqueira/)
