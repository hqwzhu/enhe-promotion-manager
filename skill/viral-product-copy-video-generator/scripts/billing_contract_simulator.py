#!/usr/bin/env python3
"""Local reference simulator for the browser extension billing contract.

This is not a production payment backend. It is a deterministic local harness
that proves the extension contract can support license validation, usage
reservation, hosted run acceptance, usage commit, and subscription webhook
state changes without storing payment secrets or plaintext license keys.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "browser-extension" / "billing-contract.json"
REPORT_SUBDIR = Path("reports/promotion-manager/billing-simulator")
STATE_FILENAME = "billing-simulator-state.json"
REPORT_FILENAME = "billing-simulator.json"
MARKDOWN_FILENAME = "billing-simulator.md"
LICENSE_HASH_PREFIX = "enhe-promotion-manager-license:"
ACTIVE_STATUSES = {"active", "trialing"}


def main() -> None:
    args = parse_args()
    response = run_command(args)
    print(json.dumps(response, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulate ENHE Product Promo Maker billing contract behavior locally.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--contract", default=str(DEFAULT_CONTRACT), help="Path to browser-extension/billing-contract.json.")
    parent.add_argument("--out-dir", default="./promotion-output", help="Output directory for reports.")
    parent.add_argument("--state-file", default="", help="Optional explicit simulator state file.")

    subparsers.add_parser("validate-contract", parents=[parent], help="Validate required billing contract fields.")

    demo = subparsers.add_parser("demo", parents=[parent], help="Run a complete local license, usage, and webhook flow.")
    demo.add_argument("--license-key", default="", help="Optional demo license key. The key is hashed before storage.")
    demo.add_argument("--plan", default="starter", choices=["free", "starter", "growth", "scale"])
    demo.add_argument("--workflow-type", default="research_run")
    demo.add_argument("--idempotency-key", default="demo-idempotency-key")
    demo.add_argument("--input-tokens", type=int, default=180000)
    demo.add_argument("--output-tokens", type=int, default=65000)
    demo.add_argument("--reset-state", action="store_true", help="Start the demo with an empty local state file.")

    hosted_demo = subparsers.add_parser("demo-hosted-run", parents=[parent], help="Run license, usage reservation, hosted run acceptance, usage commit, and webhook flow.")
    hosted_demo.add_argument("--license-key", default="", help="Optional demo license key. The key is hashed before storage.")
    hosted_demo.add_argument("--plan", default="growth", choices=["free", "starter", "growth", "scale"])
    hosted_demo.add_argument("--workflow-type", default="standard_run")
    hosted_demo.add_argument("--command-type", default="skill_entry")
    hosted_demo.add_argument("--product-url", default="https://example.com/product")
    hosted_demo.add_argument("--platforms", default="youtube,zhihu,xiaohongshu,douyin,github")
    hosted_demo.add_argument("--workflow-depth", default="full", choices=["full", "research", "playbook"])
    hosted_demo.add_argument("--local-command", default="")
    hosted_demo.add_argument("--idempotency-key", default="demo-hosted-run-idempotency-key")
    hosted_demo.add_argument("--input-tokens", type=int, default=220000)
    hosted_demo.add_argument("--output-tokens", type=int, default=80000)
    hosted_demo.add_argument("--video-seconds-rendered", type=int, default=0)
    hosted_demo.add_argument("--reset-state", action="store_true", help="Start the demo with an empty local state file.")

    issue = subparsers.add_parser("issue-license", parents=[parent], help="Issue or refresh one local license record.")
    issue.add_argument("--license-key", required=True)
    issue.add_argument("--plan", default="starter", choices=["free", "starter", "growth", "scale"])
    issue.add_argument("--email", default="demo@example.com")

    validate = subparsers.add_parser("validate-license", parents=[parent], help="Validate a local license record.")
    validate.add_argument("--license-key", required=True)

    authorize = subparsers.add_parser("authorize-usage", parents=[parent], help="Reserve credits before a hosted run.")
    authorize.add_argument("--license-key", required=True)
    authorize.add_argument("--workflow-type", default="research_run")
    authorize.add_argument("--estimated-credits", type=int)
    authorize.add_argument("--idempotency-key", required=True)

    commit = subparsers.add_parser("commit-usage", parents=[parent], help="Commit actual usage after a hosted run.")
    commit.add_argument("--usage-id", required=True)
    commit.add_argument("--credits-used", type=int)
    commit.add_argument("--input-tokens", type=int, default=0)
    commit.add_argument("--output-tokens", type=int, default=0)
    commit.add_argument("--video-seconds-rendered", type=int, default=0)
    commit.add_argument("--status", default="succeeded", choices=["succeeded", "failed"])

    hosted = subparsers.add_parser("hosted-run", parents=[parent], help="Accept a hosted run request after a matching usage reservation.")
    hosted.add_argument("--payload-json", default="", help="Optional hostedRunRequest JSON copied from the extension.")
    hosted.add_argument("--license-key", default="")
    hosted.add_argument("--usage-id", default="")
    hosted.add_argument("--workflow-type", default="standard_run")
    hosted.add_argument("--estimated-credits", type=int)
    hosted.add_argument("--command-type", default="skill_entry")
    hosted.add_argument("--product-url", default="")
    hosted.add_argument("--platforms", default="")
    hosted.add_argument("--workflow-depth", default="full")
    hosted.add_argument("--local-command", default="")
    hosted.add_argument("--complete", action="store_true", help="Immediately commit usage as if the hosted worker completed.")
    hosted.add_argument("--input-tokens", type=int, default=0)
    hosted.add_argument("--output-tokens", type=int, default=0)
    hosted.add_argument("--video-seconds-rendered", type=int, default=0)
    hosted.add_argument("--status", default="succeeded", choices=["succeeded", "failed"])

    webhook = subparsers.add_parser("webhook", parents=[parent], help="Apply a simulated payment-provider webhook event.")
    webhook.add_argument("--event", required=True)
    webhook.add_argument("--license-key", default="")
    webhook.add_argument("--plan", default="starter", choices=["free", "starter", "growth", "scale"])
    webhook.add_argument("--email", default="demo@example.com")

    return parser.parse_args()


def run_command(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = Path(args.out_dir)
    state_path = resolve_state_path(args, out_dir)
    contract_path = Path(args.contract)
    contract = read_json(contract_path)
    contract_validation = validate_contract(contract)

    if args.command == "validate-contract":
        response = {"status": contract_validation["status"], "contract": contract_validation}
        write_report(out_dir, state_path, contract_validation, response)
        return response

    if contract_validation["status"] != "ready":
        response = {"status": "contract_invalid", "contract": contract_validation}
        write_report(out_dir, state_path, contract_validation, response)
        return response

    if getattr(args, "reset_state", False) and state_path.exists():
        state_path.unlink()
    state = load_state(state_path)

    if args.command == "demo":
        response = demo_flow(args, contract, state)
    elif args.command == "demo-hosted-run":
        response = hosted_demo_flow(args, contract, state)
    elif args.command == "issue-license":
        response = {
            "status": "ready",
            "license": issue_license(state, contract, args.license_key, args.plan, args.email),
        }
    elif args.command == "validate-license":
        response = {
            "status": "ready",
            "license": validate_license(state, args.license_key),
        }
    elif args.command == "authorize-usage":
        response = {
            "status": "ready",
            "usage": authorize_usage(
                state,
                contract,
                args.license_key,
                args.workflow_type,
                args.idempotency_key,
                args.estimated_credits,
            ),
        }
    elif args.command == "commit-usage":
        response = {
            "status": "ready",
            "usage": commit_usage(
                state,
                args.usage_id,
                args.credits_used,
                args.input_tokens,
                args.output_tokens,
                args.video_seconds_rendered,
                args.status,
            ),
        }
    elif args.command == "hosted-run":
        payload = hosted_payload_from_args(args, contract)
        response = {
            "status": "ready",
            "hostedRun": accept_hosted_run(state, contract, payload),
        }
        if args.complete and response["hostedRun"].get("accepted"):
            response["usageCommit"] = complete_hosted_run(
                state,
                response["hostedRun"]["runId"],
                args.input_tokens,
                args.output_tokens,
                args.video_seconds_rendered,
                args.status,
            )
    elif args.command == "webhook":
        response = {
            "status": "ready",
            "webhook": apply_webhook(state, contract, args.event, args.license_key, args.plan, args.email),
        }
    else:
        raise SystemExit(f"Unsupported command: {args.command}")

    save_state(state_path, state)
    write_report(out_dir, state_path, contract_validation, response, state)
    return response


def demo_flow(args: argparse.Namespace, contract: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    license_key = args.license_key or f"pm_demo_{uuid.uuid4().hex}"
    issued = issue_license(state, contract, license_key, args.plan, "demo@example.com")
    license_before_usage = validate_license(state, license_key)
    authorization = authorize_usage(
        state,
        contract,
        license_key,
        args.workflow_type,
        args.idempotency_key,
        None,
    )
    usage_id = authorization.get("usageId", "")
    committed = commit_usage(
        state,
        usage_id,
        authorization.get("creditsReserved"),
        args.input_tokens,
        args.output_tokens,
        0,
        "succeeded",
    )
    license_after_usage = validate_license(state, license_key)
    webhook = apply_webhook(state, contract, "invoice.payment_succeeded", license_key, args.plan, "demo@example.com")
    license_after_webhook = validate_license(state, license_key)
    return {
        "status": "ready",
        "secretStored": False,
        "license": issued,
        "licenseBeforeUsage": license_before_usage,
        "usageAuthorization": authorization,
        "usageCommit": committed,
        "licenseAfterUsage": license_after_usage,
        "webhook": webhook,
        "licenseAfterWebhook": license_after_webhook,
    }


def hosted_demo_flow(args: argparse.Namespace, contract: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    license_key = args.license_key or f"pm_demo_{uuid.uuid4().hex}"
    issued = issue_license(state, contract, license_key, args.plan, "demo@example.com")
    license_before_usage = validate_license(state, license_key)
    authorization = authorize_usage(
        state,
        contract,
        license_key,
        args.workflow_type,
        args.idempotency_key,
        None,
    )
    payload = {
        "licenseKey": license_key,
        "usageId": authorization.get("usageId", ""),
        "workflowType": args.workflow_type,
        "estimatedCredits": authorization.get("creditsReserved", workflow_credits(contract, args.workflow_type, None)),
        "commandType": args.command_type,
        "extensionVersion": contract.get("version", ""),
        "website": contract.get("website", ""),
        "requestSource": "chrome_extension",
        "idempotencyKey": f"{args.idempotency_key}:hosted-run",
        "productUrl": args.product_url,
        "platforms": parse_platforms(args.platforms),
        "workflowDepth": args.workflow_depth,
        "localCommand": args.local_command or default_hosted_local_command(args.product_url, args.platforms),
        "options": {"outputDir": ".\\promotion-output"},
        "safety": hosted_safety_defaults(),
    }
    hosted_run = accept_hosted_run(state, contract, payload)
    usage_commit = {}
    if hosted_run.get("accepted"):
        usage_commit = complete_hosted_run(
            state,
            hosted_run["runId"],
            args.input_tokens,
            args.output_tokens,
            args.video_seconds_rendered,
            "succeeded",
        )
    license_after_usage = validate_license(state, license_key)
    webhook = apply_webhook(state, contract, "invoice.payment_succeeded", license_key, args.plan, "demo@example.com")
    license_after_webhook = validate_license(state, license_key)
    return {
        "status": "ready",
        "secretStored": False,
        "license": issued,
        "licenseBeforeUsage": license_before_usage,
        "usageAuthorization": authorization,
        "hostedRun": hosted_run,
        "usageCommit": usage_commit,
        "licenseAfterUsage": license_after_usage,
        "webhook": webhook,
        "licenseAfterWebhook": license_after_webhook,
    }


def validate_contract(contract: dict[str, Any]) -> dict[str, Any]:
    missing: list[str] = []
    for key in [
        "checkoutUrl",
        "customerPortalUrl",
        "licenseEndpoint",
        "usageAuthorizeEndpoint",
        "usageCommitEndpoint",
        "hostedRunEndpoint",
        "webhookEndpoint",
        "plans",
        "creditCosts",
        "requiredWebhookEvents",
        "securityRules",
    ]:
        if not contract.get(key):
            missing.append(key)
    plans = contract.get("plans") if isinstance(contract.get("plans"), dict) else {}
    for plan in ["free", "starter", "growth", "scale"]:
        if plan not in plans:
            missing.append(f"plans.{plan}")
        elif "includedCredits" not in plans[plan]:
            missing.append(f"plans.{plan}.includedCredits")
    credit_costs = contract.get("creditCosts") if isinstance(contract.get("creditCosts"), dict) else {}
    for workflow in [
        "command_only",
        "standard_run",
        "research_run",
        "deep_strategy_review",
        "hosted_mp4_render",
        "browser_publish_session",
        "launch_unlock_pack",
        "real_evidence_inbox_setup",
        "real_evidence_inbox",
        "performance_monitor",
        "final_readiness_audit",
        "automation_config_init",
        "automation_due_run",
        "automation_windows_task",
    ]:
        if workflow not in credit_costs:
            missing.append(f"creditCosts.{workflow}")
    events = contract.get("requiredWebhookEvents") if isinstance(contract.get("requiredWebhookEvents"), list) else []
    for event in [
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.payment_succeeded",
        "invoice.payment_failed",
        "entitlements.active_entitlement_summary.updated",
    ]:
        if event not in events:
            missing.append(f"requiredWebhookEvents.{event}")
    usage_body = (contract.get("usageAuthorizeRequest") or {}).get("body") if isinstance(contract.get("usageAuthorizeRequest"), dict) else {}
    if not isinstance(usage_body, dict):
        missing.append("usageAuthorizeRequest.body")
    else:
        for key in ["licenseKey", "workflowType", "estimatedCredits", "idempotencyKey", "commandType"]:
            if key not in usage_body:
                missing.append(f"usageAuthorizeRequest.body.{key}")
    hosted_run_body = (contract.get("hostedRunRequest") or {}).get("body") if isinstance(contract.get("hostedRunRequest"), dict) else {}
    if not isinstance(hosted_run_body, dict):
        missing.append("hostedRunRequest.body")
    else:
        for key in [
            "licenseKey",
            "usageId",
            "workflowType",
            "estimatedCredits",
            "commandType",
            "productUrl",
            "platforms",
            "localCommand",
            "safety",
        ]:
            if key not in hosted_run_body:
                missing.append(f"hostedRunRequest.body.{key}")
    hosted_run_response = contract.get("hostedRunResponse") if isinstance(contract.get("hostedRunResponse"), dict) else {}
    if not hosted_run_response:
        missing.append("hostedRunResponse")
    else:
        for key in ["accepted", "runId", "status", "reason"]:
            if key not in hosted_run_response:
                missing.append(f"hostedRunResponse.{key}")
    return {
        "status": "ready" if not missing else "invalid",
        "missing": missing,
        "version": contract.get("version", ""),
        "provider": contract.get("provider", ""),
    }


def issue_license(
    state: dict[str, Any],
    contract: dict[str, Any],
    license_key: str,
    plan: str,
    email: str,
    status: str = "active",
) -> dict[str, Any]:
    license_hash = hash_license_key(license_key)
    license_id = license_id_from_hash(license_hash)
    quota = included_credits(contract, plan)
    record = {
        "id": license_id,
        "accountEmail": email,
        "licenseKeyHash": license_hash,
        "status": status,
        "plan": plan,
        "creditsRemaining": quota,
        "renewsAt": (date.today() + timedelta(days=30)).isoformat(),
        "updatedAt": utc_now(),
    }
    state["licenses"][license_id] = record
    return license_public_view(record)


def validate_license(state: dict[str, Any], license_key: str) -> dict[str, Any]:
    record = find_license(state, license_key)
    if not record:
        return {
            "active": False,
            "reason": "license_not_found",
            "plan": "",
            "creditsRemaining": 0,
            "renewsAt": "",
        }
    active = record.get("status") in ACTIVE_STATUSES
    return {
        "active": active,
        "reason": "ok" if active else "inactive_license",
        "licenseId": record["id"],
        "plan": title_plan(record.get("plan", "")),
        "creditsRemaining": int(record.get("creditsRemaining", 0)),
        "renewsAt": record.get("renewsAt", ""),
    }


def authorize_usage(
    state: dict[str, Any],
    contract: dict[str, Any],
    license_key: str,
    workflow_type: str,
    idempotency_key: str,
    estimated_credits: int | None,
) -> dict[str, Any]:
    record = find_license(state, license_key)
    if not record:
        return denied_authorization("license_not_found")
    for usage in state["usageLedger"].values():
        if usage.get("licenseId") == record["id"] and usage.get("idempotencyKey") == idempotency_key:
            return usage_authorization_public_view(usage, record, idempotent=True)
    if record.get("status") not in ACTIVE_STATUSES:
        return denied_authorization("inactive_license", record)
    credits = workflow_credits(contract, workflow_type, estimated_credits)
    if int(record.get("creditsRemaining", 0)) < credits:
        return denied_authorization("quota_exceeded", record, credits)
    record["creditsRemaining"] = int(record.get("creditsRemaining", 0)) - credits
    usage_id = f"usage_{uuid.uuid4().hex[:16]}"
    usage = {
        "id": usage_id,
        "licenseId": record["id"],
        "licenseKeyHash": record["licenseKeyHash"],
        "workflowType": workflow_type,
        "creditsReserved": credits,
        "creditsUsed": None,
        "inputTokens": 0,
        "outputTokens": 0,
        "videoSecondsRendered": 0,
        "status": "reserved",
        "idempotencyKey": idempotency_key,
        "createdAt": utc_now(),
        "committedAt": "",
    }
    state["usageLedger"][usage_id] = usage
    return usage_authorization_public_view(usage, record)


def denied_authorization(reason: str, record: dict[str, Any] | None = None, credits: int = 0) -> dict[str, Any]:
    return {
        "allowed": False,
        "usageId": "",
        "creditsReserved": 0,
        "creditsRemainingAfterReservation": int(record.get("creditsRemaining", 0)) if record else 0,
        "reason": reason,
        "requestedCredits": credits,
    }


def commit_usage(
    state: dict[str, Any],
    usage_id: str,
    credits_used: int | None,
    input_tokens: int,
    output_tokens: int,
    video_seconds_rendered: int,
    status: str,
) -> dict[str, Any]:
    usage = state["usageLedger"].get(usage_id)
    if not usage:
        return {"status": "not_found", "usageId": usage_id}
    if usage.get("status") in {"succeeded", "failed"}:
        return usage_commit_public_view(usage, "idempotent")
    record = state["licenses"].get(usage["licenseId"])
    reserved = int(usage.get("creditsReserved", 0))
    requested_used = reserved if credits_used is None else max(0, int(credits_used))
    actual_used = min(requested_used, reserved) if status == "succeeded" else 0
    refund = reserved - actual_used
    if record and refund > 0:
        record["creditsRemaining"] = int(record.get("creditsRemaining", 0)) + refund
        record["updatedAt"] = utc_now()
    usage["creditsUsed"] = actual_used
    usage["inputTokens"] = max(0, int(input_tokens))
    usage["outputTokens"] = max(0, int(output_tokens))
    usage["videoSecondsRendered"] = max(0, int(video_seconds_rendered))
    usage["status"] = status
    usage["committedAt"] = utc_now()
    return usage_commit_public_view(usage, "committed", refund)


def hosted_payload_from_args(args: argparse.Namespace, contract: dict[str, Any]) -> dict[str, Any]:
    if args.payload_json:
        payload = read_json(Path(args.payload_json))
        if not payload:
            raise SystemExit(f"Unable to read hosted run payload JSON: {args.payload_json}")
        return payload
    workflow_type = args.workflow_type
    estimated_credits = args.estimated_credits
    if estimated_credits is None:
        estimated_credits = workflow_credits(contract, workflow_type, None)
    return {
        "licenseKey": args.license_key,
        "usageId": args.usage_id,
        "workflowType": workflow_type,
        "estimatedCredits": estimated_credits,
        "commandType": args.command_type,
        "extensionVersion": contract.get("version", ""),
        "website": contract.get("website", ""),
        "requestSource": "chrome_extension",
        "idempotencyKey": f"hosted-run-{uuid.uuid4().hex}",
        "productUrl": args.product_url,
        "platforms": parse_platforms(args.platforms),
        "workflowDepth": args.workflow_depth,
        "localCommand": args.local_command,
        "options": {},
        "safety": hosted_safety_defaults(),
    }


def accept_hosted_run(state: dict[str, Any], contract: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    license_key = str(payload.get("licenseKey", ""))
    record = find_license(state, license_key)
    if not record:
        return denied_hosted_run("license_not_found")
    if record.get("status") not in ACTIVE_STATUSES:
        return denied_hosted_run("inactive_license", record)

    workflow_type = str(payload.get("workflowType", ""))
    expected_credits = workflow_credits(contract, workflow_type, payload.get("estimatedCredits"))
    usage_id = str(payload.get("usageId", ""))
    if expected_credits > 0 and not usage_id:
        return denied_hosted_run("missing_usage_reservation", record, expected_credits)

    usage = state["usageLedger"].get(usage_id) if usage_id else None
    if expected_credits > 0:
        validation_error = validate_usage_for_hosted_run(usage, record, workflow_type, expected_credits)
        if validation_error:
            return denied_hosted_run(validation_error, record, expected_credits)

    payload_error = validate_hosted_payload(payload)
    if payload_error:
        return denied_hosted_run(payload_error, record, expected_credits)

    run_id = f"run_{uuid.uuid4().hex[:16]}"
    now = utc_now()
    hosted_run = {
        "id": run_id,
        "licenseId": record["id"],
        "usageId": usage_id,
        "workflowType": workflow_type,
        "estimatedCredits": expected_credits,
        "commandType": str(payload.get("commandType", "")),
        "productUrl": str(payload.get("productUrl", "")),
        "platforms": normalize_platforms(payload.get("platforms")),
        "workflowDepth": str(payload.get("workflowDepth", "")),
        "localCommand": str(payload.get("localCommand", "")),
        "status": "queued",
        "acceptedAt": now,
        "completedAt": "",
        "safety": sanitize_safety(payload.get("safety")),
    }
    state["hostedRuns"][run_id] = hosted_run
    return hosted_run_public_view(hosted_run, "ok")


def validate_usage_for_hosted_run(
    usage: dict[str, Any] | None,
    record: dict[str, Any],
    workflow_type: str,
    expected_credits: int,
) -> str:
    if not usage:
        return "missing_usage_reservation"
    if usage.get("licenseId") != record["id"]:
        return "usage_license_mismatch"
    if usage.get("status") != "reserved":
        return "usage_not_reserved"
    if usage.get("workflowType") != workflow_type:
        return "usage_workflow_mismatch"
    if int(usage.get("creditsReserved", 0)) < expected_credits:
        return "reserved_credits_too_low"
    return ""


def validate_hosted_payload(payload: dict[str, Any]) -> str:
    command_type = str(payload.get("commandType", ""))
    if command_type in {"skill_entry", "automation_init"} and not str(payload.get("productUrl", "")).strip():
        return "missing_product_url"
    platforms = normalize_platforms(payload.get("platforms"))
    if command_type in {"skill_entry", "automation_init"} and not platforms:
        return "missing_platforms"
    if not str(payload.get("localCommand", "")).strip():
        return "missing_local_command"
    safety = payload.get("safety") if isinstance(payload.get("safety"), dict) else {}
    for key in [
        "approvalRequiredForOfficialPublish",
        "finalPublishNotClickedByExtension",
        "noPlatformSecretsInPayload",
        "noCaptchaBypass",
    ]:
        if safety.get(key) is not True:
            return f"safety_flag_missing:{key}"
    return ""


def complete_hosted_run(
    state: dict[str, Any],
    run_id: str,
    input_tokens: int,
    output_tokens: int,
    video_seconds_rendered: int,
    status: str,
) -> dict[str, Any]:
    hosted_run = state["hostedRuns"].get(run_id)
    if not hosted_run:
        return {"status": "not_found", "runId": run_id}
    if hosted_run.get("status") in {"succeeded", "failed"}:
        usage = state["usageLedger"].get(hosted_run.get("usageId", ""))
        return {"status": "idempotent", "runId": run_id, "usage": usage_commit_public_view(usage, "idempotent") if usage else {}}
    if not hosted_run.get("usageId"):
        hosted_run["status"] = status
        hosted_run["completedAt"] = utc_now()
        return {
            "status": status,
            "runId": run_id,
            "usage": {},
        }
    usage_commit = commit_usage(
        state,
        hosted_run.get("usageId", ""),
        hosted_run.get("estimatedCredits"),
        input_tokens,
        output_tokens,
        video_seconds_rendered,
        status,
    )
    hosted_run["status"] = status
    hosted_run["completedAt"] = utc_now()
    return {
        "status": status,
        "runId": run_id,
        "usage": usage_commit,
    }


def denied_hosted_run(
    reason: str,
    record: dict[str, Any] | None = None,
    requested_credits: int = 0,
) -> dict[str, Any]:
    return {
        "accepted": False,
        "runId": "",
        "status": "blocked",
        "dashboardUrl": "",
        "reportUrl": "",
        "reason": reason,
        "licenseId": record["id"] if record else "",
        "requestedCredits": requested_credits,
    }


def hosted_run_public_view(hosted_run: dict[str, Any], reason: str) -> dict[str, Any]:
    run_id = hosted_run["id"]
    return {
        "accepted": True,
        "runId": run_id,
        "status": hosted_run.get("status", ""),
        "dashboardUrl": f"https://www.enhe-tech.com.cn/promotion-manager/runs/{run_id}",
        "reportUrl": "",
        "reason": reason,
        "usageId": hosted_run.get("usageId", ""),
        "workflowType": hosted_run.get("workflowType", ""),
        "estimatedCredits": int(hosted_run.get("estimatedCredits", 0)),
    }


def parse_platforms(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def normalize_platforms(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return parse_platforms(str(value or ""))


def sanitize_safety(value: Any) -> dict[str, bool]:
    safety = value if isinstance(value, dict) else {}
    return {
        "approvalRequiredForOfficialPublish": safety.get("approvalRequiredForOfficialPublish") is True,
        "finalPublishNotClickedByExtension": safety.get("finalPublishNotClickedByExtension") is True,
        "noPlatformSecretsInPayload": safety.get("noPlatformSecretsInPayload") is True,
        "noCaptchaBypass": safety.get("noCaptchaBypass") is True,
    }


def hosted_safety_defaults() -> dict[str, bool]:
    return {
        "approvalRequiredForOfficialPublish": True,
        "finalPublishNotClickedByExtension": True,
        "noPlatformSecretsInPayload": True,
        "noCaptchaBypass": True,
    }


def default_hosted_local_command(product_url: str, platforms: str) -> str:
    return (
        "python scripts\\skill_entry.py "
        f"--link \"{product_url}\" "
        f"--platforms {platforms} "
        "--out-dir \".\\promotion-output\""
    )


def apply_webhook(
    state: dict[str, Any],
    contract: dict[str, Any],
    event: str,
    license_key: str,
    plan: str,
    email: str,
) -> dict[str, Any]:
    required_events = contract.get("requiredWebhookEvents") if isinstance(contract.get("requiredWebhookEvents"), list) else []
    if event not in required_events:
        return {"status": "unsupported_event", "event": event}
    record = find_license(state, license_key) if license_key else None
    if not record and license_key and event in {
        "checkout.session.completed",
        "customer.subscription.created",
        "invoice.payment_succeeded",
    }:
        issued = issue_license(state, contract, license_key, plan, email)
        record = state["licenses"][issued["licenseId"]]
    if not record:
        return {"status": "license_required", "event": event}

    if event in {"checkout.session.completed", "customer.subscription.created", "customer.subscription.updated"}:
        record["status"] = "active"
        record["plan"] = plan
    elif event == "invoice.payment_succeeded":
        record["status"] = "active"
        record["plan"] = plan
        record["creditsRemaining"] = included_credits(contract, plan)
        record["renewsAt"] = (date.today() + timedelta(days=30)).isoformat()
    elif event == "invoice.payment_failed":
        record["status"] = "past_due"
    elif event == "customer.subscription.deleted":
        record["status"] = "canceled"
        record["creditsRemaining"] = 0
    elif event == "entitlements.active_entitlement_summary.updated":
        record["status"] = "active" if record.get("status") in ACTIVE_STATUSES else record.get("status", "inactive")
    record["updatedAt"] = utc_now()

    event_record = {
        "id": f"evt_{uuid.uuid4().hex[:16]}",
        "event": event,
        "licenseId": record["id"],
        "plan": record.get("plan", ""),
        "statusAfterEvent": record.get("status", ""),
        "handledAt": utc_now(),
    }
    state["events"].append(event_record)
    return {"status": "handled", **event_record, "license": license_public_view(record)}


def workflow_credits(contract: dict[str, Any], workflow_type: str, estimated_credits: int | None) -> int:
    credit_costs = contract.get("creditCosts") if isinstance(contract.get("creditCosts"), dict) else {}
    if workflow_type not in credit_costs:
        raise SystemExit(f"Unknown workflow type in billing contract: {workflow_type}")
    if estimated_credits is not None:
        return max(0, int(estimated_credits))
    return max(0, int(credit_costs[workflow_type]))


def included_credits(contract: dict[str, Any], plan: str) -> int:
    plans = contract.get("plans") if isinstance(contract.get("plans"), dict) else {}
    plan_record = plans.get(plan)
    if not isinstance(plan_record, dict):
        raise SystemExit(f"Unknown plan in billing contract: {plan}")
    return max(0, int(plan_record.get("includedCredits", 0)))


def license_public_view(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "licenseId": record["id"],
        "licenseKeyHash": short_hash(record["licenseKeyHash"]),
        "status": record.get("status", ""),
        "plan": title_plan(record.get("plan", "")),
        "creditsRemaining": int(record.get("creditsRemaining", 0)),
        "renewsAt": record.get("renewsAt", ""),
        "active": record.get("status") in ACTIVE_STATUSES,
    }


def usage_authorization_public_view(
    usage: dict[str, Any],
    record: dict[str, Any],
    idempotent: bool = False,
) -> dict[str, Any]:
    return {
        "allowed": True,
        "usageId": usage["id"],
        "creditsReserved": int(usage.get("creditsReserved", 0)),
        "creditsRemainingAfterReservation": int(record.get("creditsRemaining", 0)),
        "reason": "ok",
        "idempotent": idempotent,
    }


def usage_commit_public_view(usage: dict[str, Any], result: str, credits_refunded: int = 0) -> dict[str, Any]:
    return {
        "result": result,
        "usageId": usage["id"],
        "status": usage.get("status", ""),
        "creditsReserved": int(usage.get("creditsReserved", 0)),
        "creditsUsed": int(usage.get("creditsUsed") or 0),
        "creditsRefunded": credits_refunded,
        "inputTokens": int(usage.get("inputTokens", 0)),
        "outputTokens": int(usage.get("outputTokens", 0)),
        "videoSecondsRendered": int(usage.get("videoSecondsRendered", 0)),
    }


def find_license(state: dict[str, Any], license_key: str) -> dict[str, Any] | None:
    license_hash = hash_license_key(license_key)
    license_id = license_id_from_hash(license_hash)
    record = state["licenses"].get(license_id)
    if record and record.get("licenseKeyHash") == license_hash:
        return record
    return None


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_state()
    try:
        state = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return empty_state()
    if not isinstance(state, dict):
        return empty_state()
    state.setdefault("version", "0.1.0")
    state.setdefault("licenses", {})
    state.setdefault("usageLedger", {})
    state.setdefault("hostedRuns", {})
    state.setdefault("events", [])
    return state


def empty_state() -> dict[str, Any]:
    return {"version": "0.1.0", "licenses": {}, "usageLedger": {}, "hostedRuns": {}, "events": []}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_report(
    out_dir: Path,
    state_path: Path,
    contract_validation: dict[str, Any],
    response: dict[str, Any],
    state: dict[str, Any] | None = None,
) -> None:
    directory = out_dir / REPORT_SUBDIR
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedAt": utc_now(),
        "status": response.get("status", "unknown"),
        "contract": contract_validation,
        "stateFile": str(state_path),
        "secretStored": False,
        "summary": state_summary(state or load_state(state_path)),
        "response": response,
        "guardrails": [
            "No payment provider secrets are accepted or stored by this simulator.",
            "Plaintext license keys are never written to state or reports.",
            "Production backends must add authentication, database transactions, salted hashing, and webhook signature verification.",
        ],
    }
    (directory / REPORT_FILENAME).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / MARKDOWN_FILENAME).write_text(render_markdown(payload) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Billing Contract Simulator",
        "",
        f"- Generated: {report['generatedAt']}",
        f"- Status: `{report['status']}`",
        f"- Contract: `{report['contract']['status']}`",
        f"- State file: {report['stateFile']}",
        f"- Plaintext license stored: {report['secretStored']}",
        "",
        "## Summary",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Guardrails"])
    lines.extend(f"- {item}" for item in report["guardrails"])
    return "\n".join(lines)


def state_summary(state: dict[str, Any]) -> dict[str, Any]:
    licenses = state.get("licenses") if isinstance(state.get("licenses"), dict) else {}
    ledger = state.get("usageLedger") if isinstance(state.get("usageLedger"), dict) else {}
    hosted_runs = state.get("hostedRuns") if isinstance(state.get("hostedRuns"), dict) else {}
    events = state.get("events") if isinstance(state.get("events"), list) else []
    return {
        "licenses": len(licenses),
        "activeLicenses": sum(1 for record in licenses.values() if record.get("status") in ACTIVE_STATUSES),
        "usageRecords": len(ledger),
        "committedUsageRecords": sum(1 for record in ledger.values() if record.get("status") in {"succeeded", "failed"}),
        "hostedRuns": len(hosted_runs),
        "completedHostedRuns": sum(1 for record in hosted_runs.values() if record.get("status") in {"succeeded", "failed"}),
        "webhookEvents": len(events),
    }


def resolve_state_path(args: argparse.Namespace, out_dir: Path) -> Path:
    if args.state_file:
        return Path(args.state_file)
    return out_dir / REPORT_SUBDIR / STATE_FILENAME


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def hash_license_key(license_key: str) -> str:
    return hashlib.sha256(f"{LICENSE_HASH_PREFIX}{license_key}".encode("utf-8")).hexdigest()


def license_id_from_hash(license_hash: str) -> str:
    return f"lic_{license_hash[:16]}"


def short_hash(license_hash: str) -> str:
    return f"{license_hash[:10]}...{license_hash[-6:]}"


def title_plan(plan: str) -> str:
    return str(plan or "").strip().title()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    main()
