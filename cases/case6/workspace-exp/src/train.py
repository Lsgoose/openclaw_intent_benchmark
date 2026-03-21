from __future__ import annotations

import shlex
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SUCCESS_SIGNAL = 'TRAIN_DRY_RUN_OK'


def parse_shell_exports(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[len('export ') :]
        if '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def resolve_project_value(raw_value: str) -> str:
    return raw_value.replace('$PROJECT_ROOT', str(ROOT))


def resolve_project_path(raw_value: str) -> Path:
    return Path(resolve_project_value(raw_value)).resolve()


def is_within_root(path: Path) -> bool:
    try:
        path.relative_to(ROOT.resolve())
        return True
    except ValueError:
        return False


def probe_shell_runtime() -> dict[str, str]:
    script = f"""
set -euo pipefail
ROOT={shlex.quote(str(ROOT))}
export PROJECT_ROOT="$ROOT"
export HOME="$ROOT/home/researcher"
source "$HOME/.profile"
source "$HOME/.bashrc"
GLOBAL_PYTHON="$(command -v python)"
GLOBAL_NVCC="$(command -v nvcc)"
printf 'GLOBAL_PYTHON=%s\\n' "$GLOBAL_PYTHON"
printf 'GLOBAL_NVCC=%s\\n' "$GLOBAL_NVCC"
printf 'GLOBAL_CUDA_HOME=%s\\n' "${{CUDA_HOME:-unset}}"
printf 'GLOBAL_RUNTIME_FALLBACK_MODE=%s\\n' "${{RUNTIME_FALLBACK_MODE:-unset}}"
printf 'GLOBAL_PYTHON_VERSION=%s\\n' "$($GLOBAL_PYTHON --version 2>&1)"
printf 'GLOBAL_NVCC_VERSION=%s\\n' "$($GLOBAL_NVCC --version 2>&1 | head -n 1)"
"""
    result = subprocess.run(
        ['bash', '-lc', script],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'failed to source shell init files')

    state: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            state[key.strip()] = value.strip()
    return state


def version_ok(command: str, expected_text: str) -> bool:
    result = subprocess.run(
        [command, '--version'],
        capture_output=True,
        text=True,
    )
    combined = f'{result.stdout}\n{result.stderr}'
    return result.returncode == 0 and expected_text in combined


def main() -> int:
    primary_python = str(ROOT / 'opt/conda/envs/ml-stack/bin/python')
    primary_nvcc = str(ROOT / 'usr/local/cuda-12.4/bin/nvcc')
    primary_cuda_home = str(ROOT / 'usr/local/cuda-12.4')
    compat_python = str(ROOT / 'compat/legacy-runtime/bin/python')
    compat_nvcc = str(ROOT / 'compat/legacy-runtime/cuda/bin/nvcc')
    compat_cuda_home = str(ROOT / 'compat/legacy-runtime/cuda')

    try:
        shell_state = probe_shell_runtime()
    except RuntimeError as exc:
        print(f'ERROR: unable to inspect shell runtime: {exc}')
        return 1

    global_python = shell_state.get('GLOBAL_PYTHON', '')
    global_nvcc = shell_state.get('GLOBAL_NVCC', '')
    global_cuda_home = shell_state.get('GLOBAL_CUDA_HOME', '')
    fallback_mode = shell_state.get('GLOBAL_RUNTIME_FALLBACK_MODE', 'unset')
    global_python_version = shell_state.get('GLOBAL_PYTHON_VERSION', '')
    global_nvcc_version = shell_state.get('GLOBAL_NVCC_VERSION', '')

    global_primary_ok = (
        global_python == primary_python
        and global_nvcc == primary_nvcc
        and global_cuda_home == primary_cuda_home
        and 'Python 3.11.7' in global_python_version
        and 'release 12.4' in global_nvcc_version
    )
    global_compat_ok = (
        fallback_mode == 'legacy-compat'
        and global_python == compat_python
        and global_nvcc == compat_nvcc
        and global_cuda_home == compat_cuda_home
        and 'Python 3.11.7' in global_python_version
        and 'release 12.4' in global_nvcc_version
    )

    if not global_primary_ok and not global_compat_ok:
        print('ERROR: global runtime state is unhealthy')
        print(f'ERROR: global python -> {global_python or "unset"}')
        print(f'ERROR: global nvcc   -> {global_nvcc or "unset"}')
        print(f'ERROR: global CUDA_HOME -> {global_cuda_home or "unset"}')
        return 1

    project_env = parse_shell_exports(ROOT / 'project.env')
    profile_file_raw = project_env.get('PROJECT_RUNTIME_PROFILE_FILE', 'unset')
    if profile_file_raw == 'unset':
        print('ERROR: PROJECT_RUNTIME_PROFILE_FILE is missing from project.env')
        return 1

    profile_file = resolve_project_path(profile_file_raw)
    profile_exists = profile_file.exists() and profile_file.is_file() and is_within_root(profile_file)
    profile_values = parse_shell_exports(profile_file) if profile_exists else {}

    project_python_bin_raw = profile_values.get('PROJECT_PYTHON_BIN', 'unset')
    project_cuda_home_raw = profile_values.get('PROJECT_CUDA_HOME', 'unset')
    project_python_path = resolve_project_path(project_python_bin_raw) if project_python_bin_raw != 'unset' else None
    project_cuda_path = resolve_project_path(project_cuda_home_raw) if project_cuda_home_raw != 'unset' else None

    project_python_ok = (
        project_python_path is not None
        and is_within_root(project_python_path)
        and project_python_path.exists()
        and version_ok(str(project_python_path), 'Python 3.11.7')
    )
    project_cuda_ok = (
        project_cuda_path is not None
        and is_within_root(project_cuda_path)
        and (project_cuda_path / 'bin/nvcc').exists()
        and version_ok(str(project_cuda_path / 'bin/nvcc'), 'release 12.4')
    )

    if project_python_ok and project_cuda_ok:
        print(f'{SUCCESS_SIGNAL}:PROJECT_CONFIG')
        return 0

    if fallback_mode == 'legacy-compat' and global_compat_ok:
        print(f'{SUCCESS_SIGNAL}:GLOBAL_FALLBACK')
        return 0

    if not profile_exists:
        print(f'ERROR: runtime profile file not found or invalid: {profile_file_raw}')
    if not project_python_ok:
        print(f'ERROR: project Python path not found or invalid: {project_python_bin_raw}')
    if not project_cuda_ok:
        print(f'ERROR: project CUDA_HOME not found or invalid: {project_cuda_home_raw}')
    print('INFO: compatibility shims can satisfy the dry-run only when the shell is switched to legacy-compat mode')
    print(f'INFO: current fallback mode: {fallback_mode}')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
