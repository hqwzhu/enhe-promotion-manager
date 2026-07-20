# Platform research guide

Platform research is intended to collect reviewable content structures, creator leads, public metrics, and user feedback. It does not promise a particular distribution result. Every evidence item should preserve its source, time, platform, acquisition method, and status.

## Supported research paths

### Public and official paths

- Product websites: public HTML, sitemaps, browser snapshots, and page files saved by the user.
- YouTube: public pages, publicly visible metrics, and user-authorized official API paths.
- GitHub: public repositories, README files, Issues, Releases, commit information, and public interactions.
- Zhihu, Xiaohongshu, and Douyin: public pages, browser-visible pages, user-provided exports, and an optional local Sidecar.

Research reports mark only pages, links, metrics, and comments that were actually acquired as evidence. If access fails, public numbers are unavailable, or the user has not provided an export, retain `missing`, `partial_ready`, `provider_unavailable`, or the relevant blocked status.

### Browser-visible research

After Playwright/Chromium is installed, the workflow can read dynamically rendered public pages, screenshots, and visible text. Browser assistance does not obtain content beyond the current permissions of the user and browser, and it does not upload Chrome login profiles to the public repository.

### MediaCrawler Sidecar with local login state

Sidecar is a separate upstream dependency that supports `search`, `detail`, and `creator` modes for Zhihu, Xiaohongshu, and Douyin. Installation and execution both take place on the local computer:

```powershell
python scripts\platform_data_manager.py setup --check
```

Run installation only after the user explicitly agrees to the network operation and confirms the upstream license and platform terms:

```powershell
python scripts\platform_data_manager.py setup --install
```

Example keyword collection:

```powershell
python scripts\platform_data_manager.py collect `
  --platform xiaohongshu `
  --mode search `
  --query "AI product promotion" `
  --max-contents 10 `
  --max-comments 20 `
  --out-dir ".\promotion-output"
```

By default, Sidecar connects to user-controlled local Chrome, disables proxies, and limits collection volume and concurrency. Cookies, login profiles, the checkout, virtual environment, identity salt, and raw data remain outside the public repository. The default raw directory is cleaned after normalization. Use `--keep-raw` only for local debugging; raw files may contain sensitive identifiers and must not be uploaded.

## Platform limitations

### Zhihu

Public questions, answers, and user-visible pages can serve as evidence, but page structure, login requirements, anti-automation limits, and collapsed content can produce partial results. When verification or login is requested, stop at `manual_verification_required` or `waiting_login`; the user handles the prompt and then decides whether to continue.

### Xiaohongshu

Anonymous pages often contain incomplete content, changing link parameters, or login restrictions. Detail mode should use a real content URL or ID, while search and comment counts remain controlled. When platform risk controls, verification, or login is required, stop collection and preserve the status. Do not report an empty response as "no relevant content."

### Douyin

Browser-visible content, comments, and creator information depend on login, region, page rendering, and platform permissions. Research results record only information that was actually visible. Official publishing permission is a separate requirement from research access; successful research does not mean that the account has a publishing API permission.

## Evidence statuses

| Status | Meaning | Recommended action |
| --- | --- | --- |
| `ready` | A controlled request completed and produced evidence that can be normalized | Review the source, time, and content before using it in a draft |
| `partial_ready` | Some content was acquired, but comments, fields, or targets are incomplete | Use the available evidence while creating an additional collection task |
| `provider_unavailable` | Sidecar, the browser, the pinned version, or a dependency is unavailable | Check the installation or use a public page or user export instead |
| `waiting_login` | The user must complete local login or scan a code | Retry after the user logs in, and do not share login state |
| `manual_verification_required` | The platform requires human verification | The user handles platform verification and then decides whether to continue |
| `blocked_by_platform` | Platform risk controls or access restrictions prevent the request | Stop the current path and use official, public, or user-exported evidence |
| `missing` | The target, page, or evidence file does not exist | Provide a real target or mark it as not acquired |

## Research boundaries

- Hosted Worker remains disabled; platform research runs locally.
- The tool does not evade CAPTCHA, platform risk controls, login checks, account authorization, or regional restrictions.
- Cookies and Chrome login profiles stay on the local computer and are not uploaded to this public repository or its public release packages.
- Final publishing requires user review and action; research results do not trigger platform publishing.
- Only real URLs, metrics, comments, orders, and revenue are used as real evidence; evidence is not fabricated.
- Payment, subscription, license, credits, and billing backends are excluded only from the feature parity conclusion; the extension's existing billing UI and `billing-contract.json` remain included.
