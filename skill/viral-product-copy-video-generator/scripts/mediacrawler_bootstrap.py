#!/usr/bin/env python3
"""Run a pinned MediaCrawler checkout with ENHE's local-browser safety overrides."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class BootstrapOverrides:
    requested_max_contents: int
    requested_max_comments: int
    xhs_detail_query: str = ""
    xhs_detail_target: str = ""
    telemetry_path: Path | None = None


TELEMETRY_PHASES = {
    "sidecar_process_start",
    "bootstrap_start",
    "cdp_initialization",
    "upstream_http_api",
    "detail_content",
    "root_comments",
    "sub_comments",
    "normalization",
}


class PhaseTelemetry:
    def __init__(self, path: Path | None) -> None:
        self.path = path

    def begin(self, phase: str) -> None:
        if not self.path or phase not in TELEMETRY_PHASES:
            return
        try:
            source = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            source = {}
        phases = source.get("phases", []) if isinstance(source, dict) else []
        phases = [item for item in phases if isinstance(item, dict) and item.get("phase") in TELEMETRY_PHASES]
        now = utc_now()
        if phases and phases[-1].get("phase") == phase and phases[-1].get("status") == "started":
            return
        if phases and phases[-1].get("status") == "started":
            phases[-1].update({"durationSeconds": duration_seconds(str(phases[-1].get("startedAt") or now)), "status": "completed", "reason": "success"})
        phases.append({"phase": phase, "startedAt": now, "durationSeconds": None, "status": "started", "reason": ""})
        try:
            self.path.write_text(json.dumps({"schemaVersion": 1, "phases": phases}, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def duration_seconds(started_at: str) -> float:
    try:
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    return round(max(0.0, (datetime.now(timezone.utc) - started).total_seconds()), 3)


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


def patch_xiaohongshu_search_limit(client_class: type[Any], requested_max_contents: int) -> None:
    original = client_class.get_note_by_keyword

    async def limited_get_note_by_keyword(self: Any, *args: Any, **kwargs: Any) -> Any:
        response = await original(self, *args, **kwargs)
        if not isinstance(response, dict) or not isinstance(response.get("items"), list):
            return response
        result = dict(response)
        result["items"] = response["items"][:requested_max_contents]
        return result

    client_class.get_note_by_keyword = limited_get_note_by_keyword


def patch_douyin_search_limit(client_class: type[Any], requested_max_contents: int) -> None:
    original = client_class.search_info_by_keyword

    async def limited_search_info_by_keyword(self: Any, *args: Any, **kwargs: Any) -> Any:
        response = await original(self, *args, **kwargs)
        if not isinstance(response, dict) or not isinstance(response.get("data"), list):
            return response
        result = dict(response)
        result["data"] = response["data"][:requested_max_contents]
        return result

    client_class.search_info_by_keyword = limited_search_info_by_keyword


def patch_xiaohongshu_comment_limit(client_class: type[Any], requested_max_comments: int) -> None:
    original_sub_comments = client_class.get_note_sub_comments
    retained_by_root: dict[tuple[int, str], int] = {}

    if hasattr(client_class, "get_note_comments"):
        original_root_comments = client_class.get_note_comments

        async def limited_get_note_comments(self: Any, *args: Any, **kwargs: Any) -> Any:
            response = await original_root_comments(self, *args, **kwargs)
            if not isinstance(response, dict) or not isinstance(response.get("comments"), list):
                return response
            result = dict(response)
            limited_comments = []
            for comment in response["comments"]:
                if not isinstance(comment, dict):
                    limited_comments.append(comment)
                    continue
                limited_comment = dict(comment)
                inline_comments = comment.get("sub_comments")
                retained = 0
                if isinstance(inline_comments, list):
                    limited_comment["sub_comments"] = inline_comments[:requested_max_comments]
                    retained = len(limited_comment["sub_comments"])
                root_comment_id = str(comment.get("id") or "")
                if root_comment_id:
                    retained_by_root[(id(self), root_comment_id)] = retained
                if retained >= requested_max_comments:
                    limited_comment["sub_comment_has_more"] = False
                limited_comments.append(limited_comment)
            result["comments"] = limited_comments
            return result

        client_class.get_note_comments = limited_get_note_comments

    async def limited_get_note_sub_comments(self: Any, *args: Any, **kwargs: Any) -> Any:
        response = await original_sub_comments(self, *args, **kwargs)
        if not isinstance(response, dict):
            return response
        result = dict(response)
        root_comment_id = kwargs.get("root_comment_id")
        if root_comment_id is None and len(args) >= 2:
            root_comment_id = args[1]
        state_key = (id(self), str(root_comment_id or ""))
        retained = retained_by_root.get(state_key, 0)
        remaining = max(0, requested_max_comments - retained)
        if isinstance(response.get("comments"), list):
            result["comments"] = response["comments"][:remaining]
            retained_by_root[state_key] = retained + len(result["comments"])
        result["has_more"] = False
        return result

    client_class.get_note_sub_comments = limited_get_note_sub_comments


def patch_douyin_comment_limit(client_class: type[Any], requested_max_comments: int) -> None:
    original_sub_comments = client_class.get_sub_comments

    if hasattr(client_class, "get_aweme_comments"):
        original_root_comments = client_class.get_aweme_comments

        async def safe_get_aweme_comments(self: Any, *args: Any, **kwargs: Any) -> Any:
            response = await original_root_comments(self, *args, **kwargs)
            if not isinstance(response, dict) or response.get("comments"):
                return response
            result = dict(response)
            result["has_more"] = 0
            return result

        client_class.get_aweme_comments = safe_get_aweme_comments

    async def limited_get_sub_comments(self: Any, *args: Any, **kwargs: Any) -> Any:
        response = await original_sub_comments(self, *args, **kwargs)
        if not isinstance(response, dict):
            return response
        result = dict(response)
        if isinstance(response.get("comments"), list):
            result["comments"] = response["comments"][:requested_max_comments]
        result["has_more"] = 0
        return result

    client_class.get_sub_comments = limited_get_sub_comments


def patch_zhihu_comment_limit(client_class: type[Any], requested_max_comments: int) -> None:
    def make_limited_comment_method(original: Any) -> Any:
        async def limited_comment_method(self: Any, *args: Any, **kwargs: Any) -> Any:
            response = await original(self, *args, **kwargs)
            if not isinstance(response, dict):
                return response
            result = dict(response)
            if isinstance(response.get("data"), list):
                result["data"] = response["data"][:requested_max_comments]
            paging = dict(response.get("paging") or {})
            paging["is_end"] = True
            result["paging"] = paging
            return result

        return limited_comment_method

    client_class.get_root_comments = make_limited_comment_method(client_class.get_root_comments)
    client_class.get_child_comments = make_limited_comment_method(client_class.get_child_comments)


def patch_douyin_creator_limit(client_class: type[Any], requested_max_contents: int) -> None:
    limit = max(1, requested_max_contents)

    async def limited_get_all_user_aweme_posts(
        self: Any,
        sec_user_id: str,
        callback: Any = None,
    ) -> list[Any]:
        posts_has_more = 1
        max_cursor = ""
        result: list[Any] = []
        while posts_has_more == 1 and len(result) < limit:
            response = await self.get_user_aweme_posts(sec_user_id, max_cursor)
            posts_has_more = response.get("has_more", 0)
            max_cursor = response.get("max_cursor")
            rows = list(response.get("aweme_list") or [])[: limit - len(result)]
            if callback:
                await callback(rows)
            result.extend(rows)
            if not rows:
                break
        return result

    client_class.get_all_user_aweme_posts = limited_get_all_user_aweme_posts


def patch_zhihu_creator_limit(client_class: type[Any], requested_max_contents: int) -> None:
    limit = max(1, requested_max_contents)

    def make_limited_creator_method(original: Any) -> Any:
        async def limited_creator_method(self: Any, *args: Any, **kwargs: Any) -> Any:
            call_args = list(args)
            call_kwargs = dict(kwargs)
            effective_limit = limit
            if "limit" in call_kwargs:
                effective_limit = min(call_kwargs["limit"], limit)
                call_kwargs["limit"] = effective_limit
            elif len(call_args) >= 3:
                effective_limit = min(call_args[2], limit)
                call_args[2] = effective_limit
            else:
                call_kwargs["limit"] = limit

            response = await original(self, *call_args, **call_kwargs)
            if not isinstance(response, dict):
                return response
            result = dict(response)
            rows = result.get("data")
            if isinstance(rows, list):
                result["data"] = rows[:effective_limit]
            paging = dict(result.get("paging") or {})
            paging["is_end"] = True
            result["paging"] = paging
            return result

        return limited_creator_method

    for method_name in ("get_creator_content_list_async", "get_creator_answers"):
        if hasattr(client_class, method_name):
            setattr(client_class, method_name, make_limited_creator_method(getattr(client_class, method_name)))


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


def patch_zhihu_phase_telemetry(
    client_class: type[Any],
    crawler_class: type[Any],
    manager_class: type[Any],
    telemetry: PhaseTelemetry,
) -> None:
    original_launch = manager_class.launch_and_connect

    async def tracked_launch(self: Any, *args: Any, **kwargs: Any) -> Any:
        telemetry.begin("cdp_initialization")
        return await original_launch(self, *args, **kwargs)

    manager_class.launch_and_connect = tracked_launch

    def track_method(name: str, phase: str) -> None:
        original = getattr(client_class, name)

        async def tracked(self: Any, *args: Any, **kwargs: Any) -> Any:
            telemetry.begin(phase)
            return await original(self, *args, **kwargs)

        setattr(client_class, name, tracked)

    for method_name in ("get_note_by_keyword", "get_creator_info", "get_creator_answers", "get_creator_articles", "get_creator_videos"):
        if hasattr(client_class, method_name):
            track_method(method_name, "upstream_http_api")
    track_method("get_root_comments", "root_comments")
    track_method("get_child_comments", "sub_comments")
    original_detail = crawler_class.get_note_detail

    async def tracked_detail(self: Any, *args: Any, **kwargs: Any) -> Any:
        telemetry.begin("detail_content")
        return await original_detail(self, *args, **kwargs)

    crawler_class.get_note_detail = tracked_detail


def parse_bootstrap_args(argv: Sequence[str]) -> tuple[Path, list[str], BootstrapOverrides]:
    values = list(argv)
    if "--" not in values:
        raise SystemExit("MediaCrawler bootstrap requires `--` before upstream arguments.")
    separator = values.index("--")
    parser = argparse.ArgumentParser(description="Run a pinned MediaCrawler checkout safely.")
    parser.add_argument("--checkout", required=True)
    parser.add_argument("--requested-max-contents", type=int, default=20)
    parser.add_argument("--requested-max-comments", type=int, default=30)
    parser.add_argument("--xhs-detail-query", default="")
    parser.add_argument("--xhs-detail-target", default="")
    parser.add_argument("--telemetry-path", default="")
    args = parser.parse_args(values[:separator])
    checkout = Path(args.checkout).resolve()
    if not (checkout / "main.py").is_file():
        raise SystemExit(f"Pinned MediaCrawler main.py is missing: {checkout}")
    if not 1 <= args.requested_max_contents <= 20:
        raise SystemExit("requested max contents must be between 1 and 20")
    if not 0 <= args.requested_max_comments <= 30:
        raise SystemExit("requested max comments must be between 0 and 30")
    overrides = BootstrapOverrides(
        requested_max_contents=args.requested_max_contents,
        requested_max_comments=args.requested_max_comments,
        xhs_detail_query=args.xhs_detail_query.strip(),
        xhs_detail_target=args.xhs_detail_target.strip(),
        telemetry_path=Path(args.telemetry_path).resolve() if args.telemetry_path.strip() else None,
    )
    return checkout, values[separator + 1 :], overrides


def main(argv: Sequence[str] | None = None) -> None:
    checkout, upstream_args, overrides = parse_bootstrap_args(list(argv) if argv is not None else sys.argv[1:])
    telemetry = PhaseTelemetry(overrides.telemetry_path)
    telemetry.begin("bootstrap_start")
    sys.path.insert(0, str(checkout))

    import cmd_arg  # type: ignore[import-not-found]
    import config  # type: ignore[import-not-found]
    from media_platform.douyin.client import DouYinClient  # type: ignore[import-not-found]
    from media_platform.xhs.client import XiaoHongShuClient  # type: ignore[import-not-found]
    from media_platform.zhihu.client import ZhiHuClient  # type: ignore[import-not-found]
    from media_platform.zhihu.core import ZhihuCrawler  # type: ignore[import-not-found]
    from tools.cdp_browser import CDPBrowserManager  # type: ignore[import-not-found]

    apply_cdp_port_override(config, os.environ.get("ENHE_MEDIACRAWLER_CDP_PORT"))
    patch_safe_cdp_cleanup(config, CDPBrowserManager)
    if upstream_platform(upstream_args) == "zhihu":
        patch_zhihu_phase_telemetry(ZhiHuClient, ZhihuCrawler, CDPBrowserManager, telemetry)
    patch_douyin_creator_limit(DouYinClient, overrides.requested_max_contents)
    patch_zhihu_creator_limit(ZhiHuClient, overrides.requested_max_contents)
    patch_zhihu_search_limit(ZhiHuClient, overrides.requested_max_contents)
    if overrides.xhs_detail_query and overrides.xhs_detail_target:
        patch_xiaohongshu_detail_search(XiaoHongShuClient, overrides.xhs_detail_target)
    patch_xiaohongshu_search_limit(XiaoHongShuClient, overrides.requested_max_contents)
    patch_douyin_search_limit(DouYinClient, overrides.requested_max_contents)
    patch_xiaohongshu_comment_limit(XiaoHongShuClient, overrides.requested_max_comments)
    patch_douyin_comment_limit(DouYinClient, overrides.requested_max_comments)
    patch_zhihu_comment_limit(ZhiHuClient, overrides.requested_max_comments)
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


def upstream_platform(upstream_args: Sequence[str]) -> str:
    try:
        return str(upstream_args[upstream_args.index("--platform") + 1])
    except (ValueError, IndexError):
        return ""


if __name__ == "__main__":
    main()
