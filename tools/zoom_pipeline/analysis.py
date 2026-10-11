"""Text-only lesson analysis and its output contract."""
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

HEADINGS = (
    'Фактические тайминги', 'Где буксовали', 'Cutting plan',
    'Рекомендации к следующему занятию', 'Черновик постмортема',
    'Сообщение в MAX',
)


class AnalysisError(Exception):
    def __init__(self, code, *, retryable=False, global_block=False, retry_at=None):
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.global_block = global_block
        self.retry_at = retry_at


def validate_markdown(text):
    text = text.strip()
    if not text.startswith('## ' + HEADINGS[0] + '\n'):
        raise AnalysisError('invalid_output')
    sections = []
    fence = None
    for line in text.splitlines():
        marker = re.match(r'^\s{0,3}(`{3,}|~{3,})(.*)$', line)
        if marker:
            run, tail = marker.groups()
            if fence is None:
                fence = run
            elif run[0] == fence[0] and len(run) >= len(fence) and not tail.strip():
                fence = None
            if sections:
                sections[-1][1].append(line)
            continue
        heading = re.match(r'^##\s+(.+?)\s*$', line) if fence is None else None
        if heading:
            sections.append((heading[1], []))
        elif sections:
            sections[-1][1].append(line)
    if (fence is not None or tuple(title for title, _ in sections) != HEADINGS
            or any(not '\n'.join(body).strip() for _, body in sections)):
        raise AnalysisError('invalid_output')
    return text


def _retry_deadline(text, now):
    match = re.search(r'retry[-_ ]after["\s]*[:=]\s*["\s]*([^\n"}]+)', text, re.I)
    if match:
        value = match[1].strip()
        if value.isdigit():
            try:
                return now + timedelta(seconds=int(value))
            except OverflowError:
                return None
        try:
            result = parsedate_to_datetime(value)
            return result.astimezone(timezone.utc) if result.tzinfo else None
        except (ValueError, TypeError, OverflowError):
            pass
    match = re.search(r'(?:retry_at|resets_at)["\s]*[:=]\s*["\s]*([0-9TZ:+.\-]+)', text)
    if match:
        try:
            result = datetime.fromisoformat(match[1].replace('Z', '+00:00'))
            return result.astimezone(timezone.utc) if result.tzinfo else None
        except ValueError:
            pass
    return None


def classify_error(text, now):
    lower = text.lower()
    if re.search(r'(account|organization)[^\n]{0,80}(suspended|blocked|deactivated|disabled|banned|on hold)', lower):
        return AnalysisError('account_blocked', global_block=True)
    if any(word in lower for word in ('unauthorized', 'authentication', 'invalid_api_key',
                                      'please log in', 'not logged in', 'token expired',
                                      '401', '403')):
        return AnalysisError('authentication', global_block=True)
    if (re.search(r'model[^\n]{0,100}(not found|not supported|does not exist|not available|unavailable)', lower)
            or 'model_not_found' in lower):
        return AnalysisError('model_unavailable', global_block=True)
    deadline = _retry_deadline(text, now)
    if any(word in lower for word in ('insufficient_quota', 'usage limit',
                                      'quota exceeded', 'credit balance', 'billing')):
        if deadline is not None:
            return AnalysisError('quota', retryable=True, retry_at=deadline)
        return AnalysisError('quota', global_block=True)
    if any(word in lower for word in ('429', 'rate limit', 'rate_limit')):
        return AnalysisError('rate_limit', retryable=True, retry_at=deadline)
    if any(word in lower for word in ('502', '503', '504', 'service unavailable',
                                      'server_error', 'overloaded')):
        return AnalysisError('service_unavailable', retryable=True, retry_at=deadline)
    if any(word in lower for word in ('connection reset', 'connection refused',
                                      'dns', 'network', 'timed out', 'timeout',
                                      'error sending request', 'stream disconnected')):
        return AnalysisError('network', retryable=True, retry_at=deadline)
    return AnalysisError('unknown')


def _isolated_command(cfg, root, model):
    import json
    model = dict(model)
    model.update(apply_patch_tool_type=None, experimental_supported_tools=[],
                 tool_mode='standard', node_repl_disabled=True,
                 multi_agent_version=None, multi_agent_reasoning_effort=None,
                 model_messages=None,
                 base_instructions='Analyze only the supplied text. Return only the requested Markdown.')
    catalog = root / 'catalog.json'
    catalog.write_text(json.dumps({'models': [model]}), encoding='utf-8')
    cmd = [cfg.analysis_command, 'exec', '--ignore-user-config', '--ignore-rules',
           '--ephemeral', '--skip-git-repo-check', '--sandbox', 'read-only',
           '-C', str(root), '-m', cfg.analysis_model, '--json',
           '-o', str(root / 'answer.md')]
    settings = {
        'model_catalog_json': str(catalog),
        'model_reasoning_effort': cfg.analysis_reasoning_effort,
        'project_doc_max_bytes': 0, 'include_permissions_instructions': False,
        'include_apps_instructions': False, 'include_collaboration_mode_instructions': False,
        'include_environment_context': False, 'web_search': 'disabled',
        'tools.update_plan.enabled': False,
        'tools.experimental_request_user_input.enabled': False,
        'skills.include_instructions': False, 'features.skip_host_skill_discovery': True,
        'mcp_servers': {},
        'model_provider': 'zoom-analysis',
        'model_providers.zoom-analysis.name': 'Zoom analysis',
        'model_providers.zoom-analysis.wire_api': 'responses',
        'model_providers.zoom-analysis.requires_openai_auth': True,
        'model_providers.zoom-analysis.request_max_retries': 0,
        'model_providers.zoom-analysis.stream_max_retries': 0,
    }
    for flag in ('shell_tool', 'unified_exec', 'apps', 'plugins', 'hooks', 'memories',
                 'multi_agent', 'multi_agent_v2', 'browser_use', 'browser_use_external',
                 'computer_use', 'image_generation', 'view_image', 'sleep_tool', 'goals',
                 'skill_search', 'skill_mcp_dependency_install', 'code_mode_host',
                 'code_mode', 'code_mode_only', 'enable_request_compression',
                 'remote_plugin', 'in_app_browser', 'tool_suggest', 'chronicle',
                 'unbounded_connection_retries'):
        settings['features.' + flag] = False
    for key, value in settings.items():
        cmd.extend(['-c', key + '=' + json.dumps(value, separators=(',', ':'))])
    return cmd + ['-']


def analyze(cfg, prompt, runner):
    import json
    import os
    from pathlib import Path
    import subprocess
    import tempfile
    from zoom_pipeline.config import ANALYSIS_TIMEOUT

    if cfg.analysis_engine != 'codex':
        raise AnalysisError('configuration', global_block=True)
    try:
        # Bundled catalog is local and does not contact the model service.
        bundled = runner([cfg.analysis_command, 'debug', 'models', '--bundled'], timeout=10)
        if bundled.returncode:
            raise AnalysisError('configuration', global_block=True)
        models = json.loads(bundled.stdout)['models']
        model = next((item for item in models if item['slug'] == cfg.analysis_model), None)
        if model is None:
            raise AnalysisError('model_unavailable', global_block=True)
        auth = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'auth.json'
        if not auth.is_file():
            raise AnalysisError('authentication', global_block=True)
        with tempfile.TemporaryDirectory(prefix='juniorit-analysis-') as directory:
            root = Path(directory)
            home = root / 'home'
            home.mkdir(mode=0o700)
            # Reuse login without copying tokens or global instructions/configuration.
            (home / 'auth.json').symlink_to(auth.resolve())
            env = {key: value for key, value in os.environ.items()
                   if key in {'PATH', 'HOME', 'USER', 'LOGNAME', 'TMPDIR', 'LANG', 'LC_ALL',
                              'SSL_CERT_FILE', 'SSL_CERT_DIR'}}
            env['CODEX_HOME'] = str(home)
            cmd = _isolated_command(cfg, root, model)
            result = runner(cmd, timeout=ANALYSIS_TIMEOUT, stdin_text=prompt, env=env)
            if result.returncode:
                raise classify_error((result.stderr or '') + '\n' + (result.stdout or ''),
                                     datetime.now(timezone.utc))
            # Refuse any observed tool execution even if a future CLI changes defaults.
            for line in (result.stdout or '').splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    raise AnalysisError('invalid_events', global_block=True) from None
                item = event.get('item', {})
                if item.get('type') in {'command_execution', 'mcp_tool_call', 'web_search',
                                        'file_change', 'collab_tool_call'}:
                    raise AnalysisError('isolation_violation', global_block=True)
            answer = root / 'answer.md'
            if not answer.is_file():
                raise AnalysisError('missing_output')
            return validate_markdown(answer.read_text(encoding='utf-8'))
    except subprocess.TimeoutExpired:
        raise AnalysisError('timeout', retryable=True) from None
    except (FileNotFoundError, PermissionError):
        raise AnalysisError('configuration', global_block=True) from None
    except (KeyError, TypeError, ValueError):
        raise AnalysisError('configuration', global_block=True) from None
