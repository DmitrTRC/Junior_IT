# Zoom analysis Codex implementation plan

> **For agentic workers:** Use subagent-driven-development for implementation; review and verification stay in the main loop per project instructions. Execute continuously in the existing `codex/workflows-migration` checkout, preserving unrelated work.

**Goal:** Replace the hourly failing Claude invocation with isolated Codex analysis, durable bounded retries, and explicit recovery.

**Architecture:** An analysis adapter returns validated Markdown or a normalized error. State records attempts before calls and blocks ambiguous failures. The pipeline holds a process lock, supports local recovery and analysis-only commands, and publishes a draft only after validation.

**Tech Stack:** Python standard library, pytest, installed Codex CLI, launchd.

## 1. Durable state and recovery

Files: `tools/zoom_pipeline/state.py`, `tools/tests/test_zoom_state.py`.

Use a versioned envelope `{version: 2, entries: {...}, analysis_block: null}`;
legacy top-level meeting mappings are migrated in memory and saved atomically.
Every legacy transcribed entry starts blocked (`legacy_untracked`). Corrupt or
structurally invalid JSON raises a StateError. No reset to empty history.

Expose `analysis(uuid)`, `analysis_allowed(uuid, now)`, `begin_analysis(uuid, now)`,
`fail_analysis(uuid, code, now, retryable=False, global_block=False, retry_at=None)`,
`complete_analysis(uuid)`, `resume_analysis(uuid)`, `resume_engine()`,
`recover_interrupted()` and `locked()` context manager. Keep existing phase APIs.
Use timezone-aware UTC datetimes throughout and inject `now` into processing.
`begin_analysis` increments and saves before the subprocess. Delays are 1h/4h,
three calls total. Global blockage persists across ticks and meetings.
`locked()` uses nonblocking flock; no calls run concurrently.

First test persistence and boundaries with a fixed clock:

```python
now = datetime(2026, 10, 11, tzinfo=timezone.utc)
state.advance('u', 'transcribed')
state.begin_analysis('u', now)
state.fail_analysis('u', 'timeout', now, retryable=True)
state = State.load(path)
assert not state.analysis_allowed('u', now + timedelta(minutes=59))
assert state.analysis_allowed('u', now + timedelta(hours=1))
```

Run `tools/.venv/bin/python -m pytest tools/tests/test_zoom_state.py -q` before
and after implementing. Add corruption, migration, crash, lock, manual recovery,
global blockage and exhausted-cycle tests. Review state contract before integration.

## 2. Codex adapter and config

Files: `tools/zoom_pipeline/analysis.py`, `config.py`, new `test_zoom_analysis.py`,
existing `test_zoom_config.py`.

Configuration fields: `analysis_engine`, `analysis_command`, `analysis_model`,
`analysis_reasoning_effort`; TOML `[analysis]` keys `engine`, `command`, `model`,
`reasoning_effort`. Only codex supported; reject legacy claude_cmd and invalid types.
Use current local model identifier at deployment; never inherit arbitrary runtime
configuration. Default subprocess timeout 900s.

Define `AnalysisError(code, retryable=False, global_block=False, retry_at=None)`;
`analyze(cfg, prompt, runner)` returns a validated Markdown string. Separate
`validate_markdown(text)` and `classify_error(text, now)` for deterministic tests.
No raw subprocess diagnostics in exception messages. Known auth/account/model/
quota failures block engine, known transient network/service failures retry;
unknown/invalid output block one entry. Parse explicit retry deadlines conservatively.

Read installed CLI/schema to choose confirmed isolation flags. Use stdin,
`--ephemeral`, isolated cwd, disabled instructions/tools/hooks/MCP/skills,
`--output-last-message` with fresh temporary file. Treat inability to verify
isolation as deployment blocker. Capture events only in memory for validation;
never store input prompt or model diagnostics in logs.

First test output acceptance without network:

```python
valid = '\n\n'.join('## ' + title + '\nТекст.' for title in HEADINGS)
assert validate_markdown(valid) == valid
with pytest.raises(AnalysisError):
    validate_markdown(valid.replace('## Где буксовали', '## Ошибка'))
```

Test repeated/missing/reordered/empty headings, code fences, preambles, empty or
missing output file, nonzero exit, timeout and diagnostic sanitization.
Run `tools/.venv/bin/python -m pytest tools/tests/test_zoom_analysis.py tools/tests/test_zoom_config.py -q`.

## 3. Phase integration and CLI

Files: `phases.py`, `pipeline.py`, `analysis_prompt.md`, `test_zoom_pipeline.py`,
new `test_zoom_cli.py`.

Build prompt locally with anonymized topic/session/transcript. Replace recording
URL/passcode with literal markers, restoring only in the MAX section after
validation. Reserve/update state before model call. Write validated draft using
atomic replacement, then analyzed state, then best-effort notification.

Add mutually exclusive CLI modes `--resume-analysis UUID`, `--resume-engine`,
`--analyze-only UUID`; recovery modes require no Zoom credentials or network.
Analyze-only loads transcript/date/topic from state and local files, never calls
Zoom or retention. Preserve recording access locally at download time so future
analysis-only runs can restore markers. Legacy records without saved access
produce an explicit unavailable-link note, never fetch Zoom in analysis-only mode.

Lock all mutating CLI modes. Recover interrupted attempts only while locked.
State and config failures produce normalized stderr and nonzero exit status.
Tests use fake API/runner, fixed clocks and temporary paths; no live model.
Test pending attempts across ticks, global stop within one tick, notification
failure, invalid draft preserving existing file, retries, and CLI offline modes.
Run `tools/.venv/bin/python -m pytest tools/tests/test_zoom*.py -q`.

## 4. Documentation, validation and deployment

Files: `provisioning/zoom-pipeline/zoom-pipeline.toml.example`, `setup.md`,
`com.juniorit.zoom-pipeline.plist`, targeted `meta/maintenance.md` paragraphs.
Preserve existing user edits. Document precise recovery/deployment commands and
current state truthfully. Add Codex executable resolution to launchd PATH if needed.

Run `tools/.venv/bin/python -m pytest tools/tests -q` and `tools/build_site.sh`.
Inspect task diff and commit only task files. No push.

Synthetic CLI test must prove tools/instructions unavailable and six-heading
output accepted. Then back up private local state/config, write analysis config,
choose one blocked transcript explicitly, run analysis-only and verify artifact
and state. A repeat call must do no model work. Enable/bootstrap launchd only
on success; otherwise leave disabled with explicit blocker.

Find imported duplicate sessions read-only using exact pipeline prompt signature,
verify they contain only failed requests, archive by supported `codex archive`
command, verify persisted archive state and visible Recents. Never edit chat DB.

## Acceptance

No repeated unbounded requests after errors or restarts. No unvalidated draft is
published. No hidden tool execution in model analysis. Manual recovery is local,
explicit and auditable. Agent enabled only after successful end-to-end analysis.
