#!/usr/bin/env python3
"""
DeerFlow Provider Configuration Tool

Reads provider configurations from ~/.config/myllmproviders/my_claude_provider.json
and updates DeerFlow's config.yaml model settings.

Also manages proxy configuration for web tools (web_search, web_fetch, image_search).
"""

import json
import sys
import os
import re
from pathlib import Path

CONFIG_FILE = Path.home() / ".config/myllmproviders/my_claude_provider.json"
DEERFLOW_CONFIG = "config.yaml"

# Provider-specific settings for DeerFlow
# Maps provider_id to DeerFlow model configuration template
PROVIDER_CONFIGS = {
    "aliyun-coding-plan": {
        "use": "langchain_anthropic:ChatAnthropic",
        "url_key": "anthropic_api_url",
        "url": "https://coding.dashscope.aliyuncs.com/apps/anthropic",
        "supports_thinking": True,
        "supports_vision": True,
    },
    "volc-engine-coding-plan": {
        "use": "deerflow.models.patched_deepseek:PatchedChatDeepSeek",
        "url_key": "api_base",
        "url": "https://ark.cn-beijing.volces.com/api/coding/v3",
        "supports_thinking": True,
        "supports_vision": True,
        "extra_config": {
            "when_thinking_enabled": {
                "extra_body": {
                    "thinking": {
                        "type": "enabled"
                    }
                }
            }
        }
    },
    "minimax": {
        "use": "langchain_anthropic:ChatAnthropic",
        "url_key": "anthropic_api_url",
        "url": "https://api.minimaxi.com/anthropic",
        "supports_thinking": True,
        "supports_vision": True,
    },
    "zhipuai-coding-plan": {
        "use": "langchain_anthropic:ChatAnthropic",
        "url_key": "anthropic_api_url",
        "url": "https://open.bigmodel.cn/api/anthropic",
        "supports_thinking": True,
        "supports_vision": True,
    },
    "ollama": {
        "use": "langchain_ollama:ChatOllama",
        "url_key": "base_url",
        "url": "{base_url}",  # Will be replaced
        "supports_thinking": False,
        "supports_vision": True,
    }
}

# Colors for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


def print_color(color: str, message: str) -> None:
    """Print a message with color."""
    print(f"{color}{message}{Colors.NC}")


def load_providers() -> dict:
    """Load providers from config file."""
    if not CONFIG_FILE.exists():
        print_color(Colors.RED, f"Config file not found at {CONFIG_FILE}")
        print_color(Colors.YELLOW, "Please create the config file or run 'claude-provider-config list' first.")
        sys.exit(1)

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print_color(Colors.RED, f"Error parsing config file: {e}")
        sys.exit(1)
    except Exception as e:
        print_color(Colors.RED, f"Error reading config: {e}")
        sys.exit(1)


def get_provider_info(provider_id: str, provider_data: dict) -> dict:
    """Extract provider information."""
    options = provider_data.get('options', {})
    models = provider_data.get('models', {})

    model_list = [(key, m.get('name', key)) for key, m in models.items()]
    model_list.sort(key=lambda x: x[1])

    return {
        'name': provider_data.get('name', provider_id),
        'api_key': options.get('apiKey', ''),
        'base_url': options.get('baseURL', ''),
        'models': model_list
    }


def find_deerflow_config() -> Path:
    """Find DeerFlow config.yaml file."""
    cwd = Path.cwd()

    # Check current directory
    config_path = cwd / DEERFLOW_CONFIG
    if config_path.exists():
        return config_path

    # Check parent directory (common when in backend/ subdir)
    config_path = cwd.parent / DEERFLOW_CONFIG
    if config_path.exists():
        return config_path

    # Check DEER_FLOW_CONFIG_PATH env var
    env_path = os.environ.get('DEER_FLOW_CONFIG_PATH')
    if env_path:
        config_path = Path(env_path)
        if config_path.exists():
            return config_path

    print_color(Colors.RED, f"Error: {DEERFLOW_CONFIG} not found")
    print_color(Colors.YELLOW, f"Searched in:")
    print_color(Colors.YELLOW, f"  - {cwd / DEERFLOW_CONFIG}")
    print_color(Colors.YELLOW, f"  - {cwd.parent / DEERFLOW_CONFIG}")
    sys.exit(1)


def update_yaml_model(yaml_content: str, model_config: dict) -> str:
    """Update the first model entry in YAML content."""
    lines = yaml_content.split('\n')
    result_lines = []
    in_models_section = False
    in_first_model = False
    model_indent = 0
    skip_until_next_top_level = False

    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect models section
        if line.strip().startswith('models:'):
            in_models_section = True
            result_lines.append(line)
            i += 1
            continue

        if in_models_section:
            # Detect first model entry (starts with '- name:')
            if line.strip().startswith('- name:'):
                if not in_first_model:
                    in_first_model = True
                    model_indent = len(line) - len(line.lstrip())

                    # Insert new model config
                    result_lines.append(f"{' ' * model_indent}- name: {model_config['name']}")
                    result_lines.append(f"{' ' * (model_indent + 2)}display_name: {model_config['display_name']}")
                    result_lines.append(f"{' ' * (model_indent + 2)}use: {model_config['use']}")
                    result_lines.append(f"{' ' * (model_indent + 2)}model: {model_config['model']}")

                    if model_config.get('url_key') and model_config.get('url'):
                        result_lines.append(f"{' ' * (model_indent + 2)}{model_config['url_key']}: {model_config['url']}")

                    result_lines.append(f"{' ' * (model_indent + 2)}api_key: {model_config['api_key']}")

                    if 'supports_thinking' in model_config:
                        result_lines.append(f"{' ' * (model_indent + 2)}supports_thinking: {str(model_config['supports_thinking']).lower()}")

                    if 'supports_vision' in model_config:
                        result_lines.append(f"{' ' * (model_indent + 2)}supports_vision: {str(model_config['supports_vision']).lower()}")

                    if 'extra_config' in model_config:
                        for key, value in model_config['extra_config'].items():
                            result_lines.append(f"{' ' * (model_indent + 2)}{key}:")
                            _add_yaml_dict(result_lines, value, model_indent + 4)

                    # Skip original model lines until next top-level key or next model
                    skip_until_next_top_level = True
                    i += 1
                    continue

            # If skipping, check for end of current model
            if skip_until_next_top_level:
                stripped = line.strip()

                # Check if we've reached the next model or a top-level key
                if stripped.startswith('- name:') or (line and not line[0].isspace() and ':' in line and not stripped.startswith('#')):
                    if stripped.startswith('- name:'):
                        # We've reached the second model, keep it
                        skip_until_next_top_level = False
                        in_first_model = False
                        in_models_section = False  # Exit models section handling
                        result_lines.append(line)
                    else:
                        # Top-level key, stop skipping
                        skip_until_next_top_level = False
                        in_first_model = False
                        in_models_section = False
                        result_lines.append(line)
                    i += 1
                    continue

                # Skip this line (it's part of the old first model)
                i += 1
                continue

        result_lines.append(line)
        i += 1

    return '\n'.join(result_lines)


def _add_yaml_dict(lines: list, d: dict, indent: int) -> None:
    """Recursively add dictionary to YAML lines."""
    for key, value in d.items():
        if isinstance(value, dict):
            lines.append(f"{' ' * indent}{key}:")
            _add_yaml_dict(lines, value, indent + 2)
        else:
            lines.append(f"{' ' * indent}{key}: {value}")


def action_list() -> list:
    """List available providers and return provider list."""
    providers = load_providers()

    print_color(Colors.BLUE, "Available model providers:")
    print_color(Colors.BLUE, "--------------------------")
    print()

    provider_list = []

    for provider_id, provider_data in providers.items():
        info = get_provider_info(provider_id, provider_data)
        provider_list.append({
            'id': provider_id,
            **info
        })

        print_color(Colors.GREEN, f"{provider_id}")
        print(f"   URL: {info['base_url']}")
        if info['models']:
            for model_key, model_name in info['models']:
                print(f"   Model: {model_name}")
        print()

    return provider_list


def action_generate() -> None:
    """Generate DeerFlow config.yaml model settings."""
    providers = load_providers()

    if not providers:
        print_color(Colors.RED, "Error: No providers found.")
        sys.exit(1)

    # Build flat list of all models
    all_models = []
    for p in providers:
        info = get_provider_info(p, providers[p])
        if info['models']:
            for model_key, model_name in info['models']:
                display_name = f"{p}/{model_name}"
                all_models.append({
                    'provider_id': p,
                    'model_key': model_key,
                    'model_name': model_name,
                    'display_name': display_name,
                    'api_key': info['api_key'],
                    'base_url': info['base_url']
                })
        else:
            all_models.append({
                'provider_id': p,
                'model_key': p,
                'model_name': p,
                'display_name': p,
                'api_key': info['api_key'],
                'base_url': info['base_url']
            })

    print_color(Colors.BLUE, "Available models:")
    print()

    for i, m in enumerate(all_models, 1):
        print_color(Colors.GREEN, f"{i}. {m['display_name']}")

    print()

    # Prompt for selection
    try:
        selection = input(f"Enter model number (1-{len(all_models)}): ").strip()
        selection_idx = int(selection) - 1

        if selection_idx < 0 or selection_idx >= len(all_models):
            print_color(Colors.RED, "Error: Invalid selection.")
            sys.exit(1)

        selected = all_models[selection_idx]

    except (ValueError, KeyboardInterrupt):
        print_color(Colors.RED, "Error: Invalid selection.")
        sys.exit(1)

    print_color(Colors.GREEN, f"Selected: {selected['display_name']}")
    print()

    # Get provider-specific config
    provider_id = selected['provider_id']
    provider_config = PROVIDER_CONFIGS.get(provider_id, {
        "use": "langchain_anthropic:ChatAnthropic",
        "url_key": "anthropic_api_url",
        "url": selected['base_url'],
        "supports_thinking": True,
        "supports_vision": True,
    })

    # Build model config
    model_config = {
        'name': selected['model_key'],
        'display_name': selected['display_name'].replace('/', ' '),
        'use': provider_config['use'],
        'model': selected['model_name'],
        'api_key': selected['api_key'],
    }

    if provider_config.get('url_key') and provider_config.get('url'):
        url = provider_config['url']
        if '{base_url}' in url:
            url = url.replace('{base_url}', selected['base_url'])
        model_config['url_key'] = provider_config['url_key']
        model_config['url'] = url

    if 'supports_thinking' in provider_config:
        model_config['supports_thinking'] = provider_config['supports_thinking']

    if 'supports_vision' in provider_config:
        model_config['supports_vision'] = provider_config['supports_vision']

    if 'extra_config' in provider_config:
        model_config['extra_config'] = provider_config['extra_config']

    # Find and update config.yaml
    config_path = find_deerflow_config()
    print_color(Colors.BLUE, f"Updating: {config_path}")

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            yaml_content = f.read()
    except Exception as e:
        print_color(Colors.RED, f"Error reading config.yaml: {e}")
        sys.exit(1)

    updated_yaml = update_yaml_model(yaml_content, model_config)

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(updated_yaml)
        print_color(Colors.GREEN, f"Model configuration updated!")
        print()
        print_color(Colors.YELLOW, "Restart DeerFlow to apply changes:")
        print("  make stop && make dev")
    except Exception as e:
        print_color(Colors.RED, f"Error writing config.yaml: {e}")
        sys.exit(1)


def action_current() -> None:
    """Show current model configuration."""
    config_path = find_deerflow_config()

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print_color(Colors.RED, f"Error reading config.yaml: {e}")
        sys.exit(1)

    # Parse first model from YAML
    print_color(Colors.BLUE, "Current DeerFlow model configuration:")
    print_color(Colors.BLUE, "------------------------------------")
    print()

    in_models = False
    in_first_model = False
    model_lines = []

    for line in content.split('\n'):
        if line.strip().startswith('models:'):
            in_models = True
            continue

        if in_models and line.strip().startswith('- name:'):
            if not in_first_model:
                in_first_model = True
                model_lines.append(line)
            else:
                break
            continue

        if in_first_model:
            # Check if we've reached next top-level key
            if line and not line[0].isspace() and ':' in line and not line.strip().startswith('#'):
                break
            model_lines.append(line)

    for line in model_lines:
        print(line)


def action_proxy_add(proxy_url: str) -> None:
    """Add proxy configuration to config.yaml.

    Args:
        proxy_url: Proxy URL in format host:port or http://host:port
    """
    config_path = find_deerflow_config()

    # Normalize proxy URL
    if not proxy_url.startswith('http://') and not proxy_url.startswith('https://'):
        proxy_url = f'http://{proxy_url}'

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print_color(Colors.RED, f"Error reading config.yaml: {e}")
        sys.exit(1)

    # Check if there's an uncommented proxy section
    has_uncommented_proxy = False
    for line in content.split('\n'):
        stripped = line.strip()
        if stripped == 'proxy:':
            has_uncommented_proxy = True
            break

    if has_uncommented_proxy:
        # Update existing proxy section
        updated = update_proxy_section(content, proxy_url)
    else:
        # Add new proxy section (replace commented section if exists)
        updated = add_proxy_section(content, proxy_url)

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(updated)
        print_color(Colors.GREEN, f"Proxy configuration added: {proxy_url}")
        print()
        print_color(Colors.YELLOW, "Restart DeerFlow to apply changes:")
        print("  make stop && make dev")
    except Exception as e:
        print_color(Colors.RED, f"Error writing config.yaml: {e}")
        sys.exit(1)


def action_proxy_remove() -> None:
    """Remove proxy configuration from config.yaml."""
    config_path = find_deerflow_config()

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print_color(Colors.RED, f"Error reading config.yaml: {e}")
        sys.exit(1)

    updated = remove_proxy_section(content)

    if updated == content:
        print_color(Colors.YELLOW, "No proxy configuration found to remove.")
        return

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(updated)
        print_color(Colors.GREEN, "Proxy configuration removed.")
        print()
        print_color(Colors.YELLOW, "Restart DeerFlow to apply changes:")
        print("  make stop && make dev")
    except Exception as e:
        print_color(Colors.RED, f"Error writing config.yaml: {e}")
        sys.exit(1)


def action_proxy_show() -> None:
    """Show current proxy configuration."""
    config_path = find_deerflow_config()

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print_color(Colors.RED, f"Error reading config.yaml: {e}")
        sys.exit(1)

    proxy_config = parse_proxy_config(content)

    print_color(Colors.BLUE, "Current Proxy Configuration:")
    print_color(Colors.BLUE, "---------------------------")
    print()

    if proxy_config:
        for key, value in proxy_config.items():
            print(f"  {key}: {value}")
    else:
        print_color(Colors.YELLOW, "  No proxy configured.")


def update_proxy_section(content: str, proxy_url: str) -> str:
    """Update existing proxy section in YAML content."""
    lines = content.split('\n')
    result = []
    in_proxy_section = False
    proxy_indent = 0
    updated_keys = {'http': False, 'https': False}

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Detect proxy section start
        if stripped == 'proxy:':
            in_proxy_section = True
            proxy_indent = len(line) - len(line.lstrip())
            result.append(line)
            continue

        if in_proxy_section:
            current_indent = len(line) - len(line.lstrip()) if line.strip() else proxy_indent + 2

            # Check if we've exited the proxy section
            if stripped and not stripped.startswith('#') and current_indent <= proxy_indent:
                in_proxy_section = False
                # Add any keys that weren't updated
                if not updated_keys['http']:
                    result.append(' ' * (proxy_indent + 2) + f'http: {proxy_url}')
                if not updated_keys['https']:
                    result.append(' ' * (proxy_indent + 2) + f'https: {proxy_url}')
                result.append(line)
                continue

            # Update http/https lines
            if stripped.startswith('http:'):
                result.append(' ' * (proxy_indent + 2) + f'http: {proxy_url}')
                updated_keys['http'] = True
                continue
            elif stripped.startswith('https:'):
                result.append(' ' * (proxy_indent + 2) + f'https: {proxy_url}')
                updated_keys['https'] = True
                continue

        result.append(line)

    # If we were in proxy section at end of file, add missing keys
    if in_proxy_section:
        if not updated_keys['http']:
            result.append(' ' * (proxy_indent + 2) + f'http: {proxy_url}')
        if not updated_keys['https']:
            result.append(' ' * (proxy_indent + 2) + f'https: {proxy_url}')

    return '\n'.join(result)


def add_proxy_section(content: str, proxy_url: str) -> str:
    """Add new proxy section to YAML content.

    If there's a commented proxy section, replace it with an uncommented one.
    Otherwise, insert after token_usage section.
    """
    lines = content.split('\n')
    result = []

    # First, check if there's already an uncommented proxy section
    has_uncommented_proxy = False
    uncommented_proxy_start = -1
    uncommented_proxy_end = -1

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == 'proxy:' and not has_uncommented_proxy:
            has_uncommented_proxy = True
            uncommented_proxy_start = i
            proxy_indent = len(line) - len(line.lstrip())
            # Find end of proxy section
            for j in range(i + 1, len(lines)):
                next_line = lines[j]
                next_stripped = next_line.strip()
                if not next_stripped:
                    continue
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent <= proxy_indent and not next_stripped.startswith('#'):
                    uncommented_proxy_end = j
                    break
            break

    if has_uncommented_proxy:
        # Update existing proxy section
        for i, line in enumerate(lines):
            if i == uncommented_proxy_start:
                result.append('proxy:')
                result.append(f'  http: {proxy_url}')
                result.append(f'  https: {proxy_url}')
            elif i > uncommented_proxy_start and (uncommented_proxy_end < 0 or i < uncommented_proxy_end):
                # Skip old proxy content
                continue
            else:
                result.append(line)
        return '\n'.join(result)

    # Check if there's a commented proxy section to replace
    comment_proxy_start = -1
    comment_proxy_end = -1

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Look for the header comment line (starts with # ===) before "Proxy Configuration"
        if stripped.startswith('# ===') and i + 1 < len(lines):
            next_stripped = lines[i + 1].strip()
            if 'Proxy Configuration' in next_stripped:
                comment_proxy_start = i
                # Find the end - look for the next section header or uncommented key
                for j in range(i, len(lines)):
                    next_line = lines[j]
                    next_stripped = next_line.strip()
                    # Check for next section (uncommented key at start of line)
                    if next_stripped and not next_stripped.startswith('#') and next_line[0] not in ' \t':
                        comment_proxy_end = j
                        break
                break

    if comment_proxy_start >= 0:
        # Replace commented proxy section
        for i, line in enumerate(lines):
            if i == comment_proxy_start:
                # Insert uncommented proxy section
                result.append('# =============================================================================')
                result.append('# Proxy Configuration')
                result.append('# =============================================================================')
                result.append('# Configure HTTP proxy for web tools (web_search, web_fetch, image_search)')
                result.append('proxy:')
                result.append(f'  http: {proxy_url}')
                result.append(f'  https: {proxy_url}')
                result.append('')
            elif i >= comment_proxy_start and (comment_proxy_end < 0 or i < comment_proxy_end):
                # Skip the old commented section
                continue
            else:
                result.append(line)
        return '\n'.join(result)

    # No commented section, insert after token_usage
    inserted = False
    for i, line in enumerate(lines):
        result.append(line)

        if not inserted and line.strip().startswith('token_usage:'):
            # Find the end of token_usage section
            j = i + 1
            token_indent = len(line) - len(line.lstrip())

            while j < len(lines):
                next_line = lines[j]
                next_stripped = next_line.strip()

                # Skip empty lines and comments
                if not next_stripped or next_stripped.startswith('#'):
                    result.append(next_line)
                    j += 1
                    continue

                next_indent = len(next_line) - len(next_line.lstrip())

                # If we're back at the same or lower indent level, we've exited token_usage
                if next_indent <= token_indent:
                    break

                result.append(next_line)
                j += 1

            # Insert proxy section
            result.append('')
            result.append('# =============================================================================')
            result.append('# Proxy Configuration')
            result.append('# =============================================================================')
            result.append('# Configure HTTP proxy for web tools (web_search, web_fetch, image_search)')
            result.append('proxy:')
            result.append(f'  http: {proxy_url}')
            result.append(f'  https: {proxy_url}')
            result.append('')
            inserted = True

            # Continue processing from j
            for k in range(j, len(lines)):
                result.append(lines[k])
            break

    # If token_usage not found, add at the beginning after header comments
    if not inserted:
        # Find first non-comment, non-empty line
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.strip() and not line.strip().startswith('#'):
                insert_pos = i
                break

        result = lines[:insert_pos]
        result.append('# =============================================================================')
        result.append('# Proxy Configuration')
        result.append('# =============================================================================')
        result.append('# Configure HTTP proxy for web tools (web_search, web_fetch, image_search)')
        result.append('proxy:')
        result.append(f'  http: {proxy_url}')
        result.append(f'  https: {proxy_url}')
        result.append('')
        result.extend(lines[insert_pos:])

    return '\n'.join(result)


def remove_proxy_section(content: str) -> str:
    """Remove proxy section from YAML content and replace with commented template."""
    lines = content.split('\n')

    # Find the uncommented proxy section
    proxy_start = -1
    proxy_end = -1
    proxy_indent = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == 'proxy:':
            proxy_start = i
            proxy_indent = len(line) - len(line.lstrip())
            # Find end of proxy section
            for j in range(i + 1, len(lines)):
                next_line = lines[j]
                next_stripped = next_line.strip()
                if not next_stripped:
                    continue
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent <= proxy_indent and not next_stripped.startswith('#'):
                    proxy_end = j
                    break
            break

    if proxy_start < 0:
        # No uncommented proxy section found, return original
        return content

    # Check if there's already a header comment above the proxy section
    header_start = proxy_start
    for i in range(proxy_start - 1, -1, -1):
        stripped = lines[i].strip()
        if not stripped or stripped.startswith('#'):
            header_start = i
        else:
            break

    # Build result
    result = []

    # Add everything before the header/proxy section
    result.extend(lines[:header_start])

    # Add commented proxy template
    result.append('# =============================================================================')
    result.append('# Proxy Configuration')
    result.append('# =============================================================================')
    result.append('# Configure HTTP proxy for web tools (web_search, web_fetch, image_search)')
    result.append('#')
    result.append('# proxy:')
    result.append('#   # HTTP proxy URL')
    result.append('#   http: http://proxy.example.com:8080')
    result.append('#   # HTTPS proxy URL (often the same as http proxy)')
    result.append('#   https: http://proxy.example.com:8080')
    result.append('#   # Optional: Proxy authentication')
    result.append('#   # username: your_username')
    result.append('#   # password: your_password')
    result.append('#   # Or use environment variables:')
    result.append('#   # username: $PROXY_USERNAME')
    result.append('#   # password: $PROXY_PASSWORD')
    result.append('')

    # Add everything after the proxy section
    if proxy_end >= 0:
        result.extend(lines[proxy_end:])
    else:
        # proxy_end not found, add remaining lines
        result.extend(lines[proxy_start + 1:])

    return '\n'.join(result)


def parse_proxy_config(content: str) -> dict:
    """Parse proxy configuration from YAML content."""
    proxy_config = {}
    in_proxy_section = False
    proxy_indent = 0

    for line in content.split('\n'):
        stripped = line.strip()

        if stripped == 'proxy:':
            in_proxy_section = True
            proxy_indent = len(line) - len(line.lstrip())
            continue

        if in_proxy_section:
            current_indent = len(line) - len(line.lstrip()) if stripped else proxy_indent + 2

            if stripped and not stripped.startswith('#') and current_indent <= proxy_indent:
                break

            if ':' in stripped and not stripped.startswith('#'):
                key, _, value = stripped.partition(':')
                key = key.strip()
                value = value.strip()
                if value:  # Only add if there's a value on the same line
                    proxy_config[key] = value

    return proxy_config


def print_help() -> None:
    """Print help message."""
    print("Usage: deerflow-provider-config [command]")
    print()
    print("Commands:")
    print("  list, ls              List available model providers")
    print("  generate, gen         Update DeerFlow config.yaml with selected model")
    print("  current               Show current model configuration")
    print()
    print("Proxy Commands:")
    print("  proxy add <host:port> Add proxy configuration (e.g., 127.0.0.1:7890)")
    print("  proxy remove          Remove proxy configuration")
    print("  proxy show            Show current proxy configuration")
    print()
    print("  -h, --help            Show this help message")
    print()
    print("If no command is given, runs in interactive mode.")


def interactive_mode() -> None:
    """Run in interactive menu mode."""
    while True:
        print_color(Colors.BLUE, "DeerFlow Provider Configuration")
        print_color(Colors.BLUE, "===============================")
        print()
        print("1. List available model providers")
        print("2. Update model configuration")
        print("3. Show current model configuration")
        print("4. Configure proxy settings")
        print("5. Exit")
        print()

        try:
            choice = input("Select an option: ").strip()
            print()

            if choice == '1':
                action_list()
            elif choice == '2':
                action_generate()
            elif choice == '3':
                action_current()
            elif choice == '4':
                proxy_interactive_mode()
            elif choice == '5':
                print_color(Colors.GREEN, "Goodbye!")
                sys.exit(0)
            else:
                print_color(Colors.RED, "Error: Invalid option. Please select 1-5.")

        except KeyboardInterrupt:
            print()
            print_color(Colors.GREEN, "Goodbye!")
            sys.exit(0)
        except EOFError:
            sys.exit(0)

        print()


def proxy_interactive_mode() -> None:
    """Interactive mode for proxy configuration."""
    print_color(Colors.BLUE, "Proxy Configuration")
    print_color(Colors.BLUE, "===================")
    print()

    # Show current proxy
    action_proxy_show()
    print()

    print("1. Add/Update proxy")
    print("2. Remove proxy")
    print("3. Back to main menu")
    print()

    try:
        choice = input("Select an option: ").strip()
        print()

        if choice == '1':
            proxy_url = input("Enter proxy address (e.g., 127.0.0.1:7890): ").strip()
            if proxy_url:
                action_proxy_add(proxy_url)
            else:
                print_color(Colors.RED, "Error: Proxy address cannot be empty.")
        elif choice == '2':
            action_proxy_remove()
        elif choice == '3':
            return
        else:
            print_color(Colors.RED, "Error: Invalid option.")

    except KeyboardInterrupt:
        print()
        return
    except EOFError:
        sys.exit(0)


def main() -> None:
    """Main entry point."""
    if len(sys.argv) == 1:
        interactive_mode()
    else:
        command = sys.argv[1].lower()

        if command in ('list', 'ls'):
            action_list()
        elif command in ('generate', 'gen'):
            action_generate()
        elif command == 'current':
            action_current()
        elif command == 'proxy':
            # Handle proxy subcommands
            if len(sys.argv) < 3:
                print_color(Colors.RED, "Error: Missing proxy subcommand.")
                print("Usage: deerflow-provider-config proxy [add|remove|show] [host:port]")
                sys.exit(1)

            subcommand = sys.argv[2].lower()

            if subcommand == 'add':
                if len(sys.argv) < 4:
                    print_color(Colors.RED, "Error: Missing proxy address.")
                    print("Usage: deerflow-provider-config proxy add <host:port>")
                    print("Example: deerflow-provider-config proxy add 127.0.0.1:7890")
                    sys.exit(1)
                action_proxy_add(sys.argv[3])
            elif subcommand == 'remove':
                action_proxy_remove()
            elif subcommand == 'show':
                action_proxy_show()
            else:
                print_color(Colors.RED, f"Error: Unknown proxy subcommand '{subcommand}'")
                print("Available proxy commands: add, remove, show")
                sys.exit(1)
        elif command in ('-h', '--help', 'help'):
            print_help()
        else:
            print_color(Colors.RED, f"Error: Unknown command '{command}'")
            print("Run 'deerflow-provider-config --help' for usage information.")
            sys.exit(1)


if __name__ == "__main__":
    main()