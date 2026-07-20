# Data and privacy

The public distribution uses a local-first data boundary. Read the complete official privacy policy at https://www.enhe-tech.com.cn/promotion-manager/privacy.

## Where data is stored

| Data type | Default location | Included in the public repository or release packages? |
| --- | --- | --- |
| Product facts, drafts, media, publishing packs, and reports | The local `--out-dir` selected by the user, usually `promotion-output` | No |
| Real-evidence inbox | A local directory selected by the user, usually `promotion-evidence-inbox` | No |
| Chrome extension language and interface settings | Chrome extension local storage | No |
| Existing extension license and billing settings | Chrome extension local storage; sent only according to interface notices when the user explicitly invokes a configured ENHE endpoint | No |
| Cookies and Chrome login profiles | The user's local Chrome profile or Sidecar local directory | No |
| MediaCrawler checkout, virtual environment, and identity salt | `%LOCALAPPDATA%\ENHE\promotion-manager\mediacrawler` or a user-selected directory | No |
| Sidecar raw collection files | A local temporary directory; cleaned after normalization by default and managed by the user under `--keep-raw` | No |

The public repository does not contain Cookies, Chrome profiles, runtime state, user output, account credentials, order data, or client data. The public distribution build excludes `.env`, `promotion-output`, user-data directories, and other runtime paths.

## Hosted Worker

Hosted Worker: disabled. The public edition does not require a hosted backend and does not describe hosted execution as an available service. The local Skill runs without a subscription.

The extension's existing license, payment, subscription, credits, and billing UI remains included, but those capabilities are outside the conclusion that non-payment commands match the bundled Skill. `billing-contract.json` also remains included. Only when a user explicitly operates a related interface should they review data transfer and endpoint status against the product page and privacy policy.

## Data retention

- Users control local output, evidence inboxes, and media. They remain until the user deletes them.
- Chrome manages extension-local settings. Users can remove them through extension settings, by clearing browser site or extension data, or by uninstalling the extension.
- Sidecar cleans normalized temporary raw data by default. The user decides how long to retain files created under explicit `--keep-raw`; sensitive raw content that is no longer needed should be deleted promptly.
- The public repository and public release packages must not retain user Cookies, login profiles, real order data, or revenue data.
- Content that a user deliberately submits to an official platform or ENHE website is governed by that platform's or website's retention policy.

## How users should protect data

- Store API or OAuth credentials in environment variables or a local `.env` file; do not commit them to Git.
- Before sharing reports, inspect URL parameters, screenshots, comments, orders, revenue, and logs for personal information.
- Do not upload Chrome profiles, Cookie files, Sidecar raw directories, or license keys.
- When working for clients, use separate output and evidence directories for each client and share only reviewed deliverables.

## Contact for access and deletion requests

For questions about data handling by the ENHE product page or extension, or to request access or deletion, email huqingwei5942@gmail.com. Include the installation source, version, request scope, and non-sensitive information that can identify the relevant record. Do not paste passwords, complete Cookies, payment-card information, or platform access tokens into the email.

## Privacy boundaries

- Cookies and Chrome login profiles stay on the local computer and are not uploaded to this public repository or its public release packages.
- Final publishing requires user review and action; the tool does not complete the final platform submission for the user.
- The tool does not evade CAPTCHA, platform risk controls, login checks, or account authorization.
- Only real URLs, metrics, comments, orders, and revenue can be treated as real evidence; data is not fabricated.
- Payment, subscription, license, credits, and billing backends are excluded only from the feature parity conclusion; the extension's existing billing UI and `billing-contract.json` remain included.
