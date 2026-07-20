#!/usr/bin/env python3
"""Run a pinned MediaCrawler checkout with ENHE's local-browser safety overrides."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class BootstrapOverrides:
    requested_max_contents: int
    xhs_detail_query: str = ""
    xhs_detail_target: str = ""


def apply_cdp_port_override(config: Any, raw_port: str | None) -> None:
    if not raw_port or not raw_port.strip():
        return
    port = int(raw_port)
    if not 1 <= port <= 65535:
        raise ValueError("ENHE_MEDIACRAWLER_CDP_PORT must be between 1 and 65535")
    config.CDP_DEBUG_PORT = port


def apply_creator_override(config: Any, parsed: Any) -> None:
    if getattr(parsed, "platform", "") != "zhihu" or getattr(parsed, "type", "") != "creator":
        return
    creator_ids = [item.strip() for item in str(getattr(parsed, "creator_id", "") or "").split(",") if item.strip()]
    if creator_ids:
        config.ZHIHU_CREATOR_URL_LIST = creator_ids


def patch_zhihu_search_limit(client_class: type[Any], requested_max_contents: int) -> None:
    original = client_class.get_note_by_keyword
    limit = max(1, requested_max_contents)

    async def limited_get_note_by_keyword(self: Any, *args: Any, **kwargs: Any) -> list[Any]:
        rows = await original(self, *args, **kwargs)
        return list(rows or [])[:limit]

    client_class.get_note_by_keyword = limited_get_note_by_keyword


def apply_xiaohongshu_detail_context(config: Any, parsed: Any, query: str, target_id: str) -> None:
    if (
        getattr(parsed, "platform", "") not in {"xhs", "xiaohongshu"}
        or getattr(parsed, "type", "") != "detail"
        or not query.strip()
        or not target_id.strip()
    ):
        return
    config.CRAWLER_TYPE = "search"
    config.KEYWORDS = query.strip()
    parsed.type = "search"


def patch_xiaohongshu_detail_search(client_class: type[Any], target_id: str) -> None:
    original = client_class.get_note_by_keyword
    expected = target_id.strip()

    async def filtered_get_note_by_keyword(self: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        response = await original(self, *args, **kwargs)
        if not isinstance(response, dict):
            return response
        items = response.get("items")
        if not isinstance(items, list):
            return response
        filtered = [
            item
            for item in items
            if isinstance(item, dict) and str(item.get("id") or item.get("note_id") or "").strip() == expected
        ]
        result = dict(response)
        result["items"] = filtered
        result["has_more"] = bool(filtered)
        return result

    client_class.get_note_by_keyword = filtered_get_note_by_keyword


def patch_safe_cdp_cleanup(config: Any, manager_class: type[Any]) -> None:
    original_cleanup = manager_class.cleanup

    async def safe_cleanup(self: Any, force: bool = False) -> None:
        if getattr(config, "CDP_CONNECT_EXISTING", False):
            self.browser_context = None
            self.browser = None
            return
        await original_cleanup(self, force=force)

    manager_class.cleanup = safe_cleanup


def parse_bootstrap_args(argv: Sequence[str]) -> tuple[Path, list[str], BootstrapOverrides]:
    values = list(argv)
    if "--" not in values:
        raise SystemExit("MediaCrawler bootstrap requires `--` before upstream arguments.")
    separator = values.index("--")
    parser = argparse.ArgumentParser(description="Run a pinned MediaCrawler checkout safely.")
    parser.add_argument("--checkout", required=True)
    parser.add_argument("--requested-max-contents", type=int, default=20)
    parser.add_argument("--xhs-detail-query", default="")
    parser.add_argument("--xhs-detail-target", default="")
    args = parser.parse_args(values[:separator])
    checkout = Path(args.checkout).resolve()
    if not (checkout / "main.py").is_file():
        raise SystemExit(f"Pinned MediaCrawler main.py is missing: {checkout}")
    if not 1 <= args.requested_max_contents <= 20:
        raise SystemExit("requested max contents must be between 1 and 20")
    overrides = BootstrapOverrides(
        requested_max_contents=args.requested_max_contents,
        xhs_detail_query=args.xhs_detail_query.strip(),
        xhs_detail_target=args.xhs_detail_target.strip(),
    )
    return checkout, values[separator + 1 :], overrides


def main(argv: Sequence[str] | None = None) -> None:
    checkout, upstream_args, overrides = parse_bootstrap_args(list(argv) if argv is not None else sys.argv[1:])
    sys.path.insert(0, str(checkout))

    import cmd_arg  # type: ignore[import-not-found]
    import config  # type: ignore[import-not-found]
    from media_platform.xhs.client import XiaoHongShuClient  # type: ignore[import-not-found]
    from media_platform.zhihu.client import ZhiHuClient  # type: ignore[import-not-found]
    from tools.cdp_browser import CDPBrowserManager  # type: ignore[import-not-found]

    apply_cdp_port_override(config, os.environ.get("ENHE_MEDIACRAWLER_CDP_PORT"))
    patch_safe_cdp_cleanup(config, CDPBrowserManager)
    patch_zhihu_search_limit(ZhiHuClient, overrides.requested_max_contents)
    if overrides.xhs_detail_query and overrides.xhs_detail_target:
        patch_xiaohongshu_detail_search(XiaoHongShuClient, overrides.xhs_detail_target)
    original_parse_cmd = cmd_arg.parse_cmd

    async def parse_cmd_with_overrides(parsed_argv: Sequence[str] | None = None) -> Any:
        parsed = await original_parse_cmd(upstream_args if parsed_argv is None else parsed_argv)
        apply_creator_override(config, parsed)
        apply_xiaohongshu_detail_context(
            config,
            parsed,
            overrides.xhs_detail_query,
            overrides.xhs_detail_target,
        )
        return parsed

    cmd_arg.parse_cmd = parse_cmd_with_overrides

    import main as upstream_main  # type: ignore[import-not-found]

    async def run() -> None:
        try:
            await upstream_main.main()
        finally:
            await upstream_main.async_cleanup()

    asyncio.run(run())


if __name__ == "__main__":
    main()
