# Platform Publishing Reference

Publishing capabilities are time-sensitive. Refresh official docs before implementing or claiming direct publishing.

## Default First-Version Modes

| Platform | Default mode | Notes |
| --- | --- | --- |
| YouTube | `official_api_publish` candidate | Official YouTube Data API can upload videos with OAuth and quota constraints. Generate packs first; publish only after user approval. |
| GitHub | `official_api_publish` candidate | Official APIs can create/update repository content, releases, issues, and discussions. Do not write to repos without approval. |
| TikTok | `official_api_publish` candidate | Content Posting API requires developer access and scopes. Treat as candidate until verified. |
| Douyin | `browser_assisted_publish` | Current operator authorization is unavailable, so Douyin defaults to browser-assisted/manual publishing. `--douyin-video-file` attaches an MP4 asset to the payload; the official upload/create executor is a reserved future port only. |
| Xiaohongshu | `manual_publish_required` | Default to manual/browser-assisted drafts. Do not use unverified direct publishing endpoints. |
| Zhihu | `manual_publish_required` | Default to manual/browser-assisted drafts. Do not use unofficial direct publishing endpoints. |

## Safety Rules

- No automatic login.
- No cookie/token/password storage.
- No captcha bypass.
- No final publish click by the agent.
- No fabricated published URL.
- No fabricated platform data.
- All publishing requires human approval.

## Official Executor Coverage

`scripts/publish_queue.py` converts generated publish packs into a single queue:

- GitHub and YouTube records can call `scripts/publish_executor.py` in dry-run mode by default.
- Douyin records are written as browser-assisted tasks by default; `--douyin-video-file` only attaches the rendered MP4 asset to the payload.
- Zhihu, Xiaohongshu, Douyin, and unverified platforms are written as manual or browser-assisted tasks with copy-ready drafts.
- Real official writes still require `--execute --approval I_APPROVE_PUBLISH` and the relevant environment credential.

`scripts/browser_publish_assistant.py` prepares payload JSON, clipboard text, checklist files, and a copy-ready `scripts/browser_publish_form_fill.py` command for manual/browser-assisted platforms. `scripts/browser_publish_form_fill.py` may fill visible form fields from one payload and write a screenshot/report, but it must not login, bypass challenges, or click the final publish/submit button.

`scripts/browser_publish_session.py` is the manager-facing wrapper for that semi-automatic path. It runs the assistant, optionally runs visible-field form fill for each prepared payload, writes per-platform screenshots/reports, and returns URL registration plus evidence inbox commands for after the user performs the final publish action.

`scripts/publish_readiness_runner.py` audits an existing queue or builds one first with `--build-queue`. It reports per-platform readiness, missing target fields, credential presence by environment variable name, approval status, and next actions. It does not store secret values and does not bypass the explicit approval gate.

`scripts/publish_setup_assistant.py` converts a readiness report into a setup kit: platform credential environment variable names, missing targets, official setup references, required capabilities, approval gates, safe rerun/execution commands, `publish-credentials.example.env`, `publish-setup-checklist.md`, and `platform-setup-guide.{json,md}`. The env file is a template only and must not contain real secrets.

`scripts/platform_access_audit.py` creates the official access boundary report before implementation or execution decisions. It maps each platform to implemented official API paths, official app-review candidates, manual/browser-assisted fallbacks, metrics evidence sources, required environment variable names, and implementation gaps. Use `--check-live` only when you want to verify that official documentation URLs are reachable.
When `--check-live` is used, the report records `officialDocEvidenceStatus`, live HTTP status, final URL, content type, UTC check time, and `officialDocSummary`. A reachable official documentation page is evidence that the documented path exists; it is not evidence that the current account has approved scopes, quota, app review, or publish permission.
The report also includes `officialDocGapResearch` for missing or limited capabilities. Candidate official sources in that section are research leads and fallback justification only; they are not treated as verified direct-publish or analytics APIs unless the capability has a specific `officialDocs` entry for the documented path.

`scripts/publish_executor.py` supports:

- GitHub file create/update through the repository contents REST API.
- GitHub issue creation through the issues REST API.
- GitHub release creation through the releases REST API.
- YouTube video upload through `videos.insert` when an OAuth access token is available.
- Reserved future port: Douyin Open Platform video upload/create, only if verified authorization becomes available and the operator explicitly re-enables that path.
- YouTube OAuth consent and same-process upload through `scripts/youtube_oauth_publish.py`.

The executor defaults to dry-run. Real writes require `--execute --approval I_APPROVE_PUBLISH` plus the relevant environment credential. It must not write credentials to reports.
The YouTube OAuth helper also defaults to dry-run. Execution requires a Google OAuth client ID and client secret from environment variables, opens or prints a Google authorization URL, exchanges the authorization code for a temporary access token, uploads, and does not save the token.
Douyin current execution path is browser-assisted/manual. The low-level official upload/create executor remains in the repository for future reviewed authorization work, but the default queue and readiness reports do not require `DOUYIN_*` credentials or call it.

## Reference URLs

- Google OAuth 2.0 for installed apps: https://developers.google.com/identity/protocols/oauth2/native-app
- YouTube videos.insert: https://developers.google.com/youtube/v3/docs/videos/insert
- GitHub Contents API: https://docs.github.com/en/rest/repos/contents
- GitHub Releases API: https://docs.github.com/en/rest/releases/releases
- GitHub Discussions GraphQL: https://docs.github.com/en/graphql/guides/using-the-graphql-api-for-discussions
- TikTok Content Posting API: https://developers.tiktok.com/doc/content-posting-api-get-started/
- Douyin publishing solution: https://open.douyin.com/platform/resource/docs/ability/content-management/douyin-publish-solution
- Douyin upload/create video APIs: https://open.douyin.com/platform/resource/docs/openapi/video-management/douyin/create/upload/ and https://open.douyin.com/platform/resource/docs/openapi/video-management/douyin/create/create-video
- Xiaohongshu open platform docs: https://open.xiaohongshu.com/document/api
