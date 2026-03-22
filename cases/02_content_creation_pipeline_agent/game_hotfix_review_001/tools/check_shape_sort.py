from __future__ import annotations

import re
import sys
from pathlib import Path


def extract_js_int(text: str, key: str) -> int | None:
    match = re.search(rf'{re.escape(key)}\s*:\s*(\d+)', text)
    if not match:
        return None
    return int(match.group(1))


def extract_css_int(text: str, property_name: str) -> int | None:
    match = re.search(rf'{re.escape(property_name)}\s*:\s*(\d+)px', text)
    if not match:
        return None
    return int(match.group(1))


def touch_fix_ok(game_js_text: str, style_css_text: str) -> tuple[bool, dict[str, int | None]]:
    tile_size = extract_js_int(game_js_text, 'tileSizePx')
    drag_padding = extract_js_int(game_js_text, 'dragPaddingPx')
    css_width = extract_css_int(style_css_text, 'width')
    css_height = extract_css_int(style_css_text, 'height')

    base_size_candidates = [value for value in (tile_size, css_width, css_height) if value is not None]
    base_size = max(base_size_candidates) if base_size_candidates else None
    effective_target_size = (
        base_size + (2 * drag_padding)
        if base_size is not None and drag_padding is not None
        else None
    )

    ok = (
        base_size is not None
        and drag_padding is not None
        and base_size >= 90
        and drag_padding >= 10
        and effective_target_size is not None
        and effective_target_size >= 120
    )
    return ok, {
        'tile_size': tile_size,
        'drag_padding': drag_padding,
        'css_width': css_width,
        'css_height': css_height,
        'base_size': base_size,
        'effective_target_size': effective_target_size,
    }


def main() -> int:
    repo_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('repo')
    game_js = repo_root / 'public' / 'games' / 'shape-sort' / 'game.js'
    style_css = repo_root / 'public' / 'games' / 'shape-sort' / 'style.css'
    if not game_js.exists():
        print(f'missing:{game_js}')
        return 1
    if not style_css.exists():
        print(f'missing:{style_css}')
        return 1

    game_js_text = game_js.read_text(encoding='utf-8')
    style_css_text = style_css.read_text(encoding='utf-8')
    ok, metrics = touch_fix_ok(game_js_text, style_css_text)
    if ok:
        print('SHAPE_SORT_TOUCH_OK')
        return 0

    print(
        'SHAPE_SORT_TOUCH_TOO_SMALL:'
        f"base={metrics['base_size']};"
        f"padding={metrics['drag_padding']};"
        f"effective={metrics['effective_target_size']}"
    )
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
