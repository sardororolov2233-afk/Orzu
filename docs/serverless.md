# Orzu Telegram Serverless — referral-only

Use the existing bot and shared Supabase project. Never run Python polling alongside the platform-managed webhook.

## Policy

Each newly confirmed friend earns one permanent shared credit. Presentation/design cost one, coursework two. Referat, article and obyektivka share three lifetime free uses, after which each costs one credit. Subscriptions and payments are disabled; old payment/approval buttons cannot mutate money or credits. Failed academic jobs refund credits atomically through the existing queue.

Text uses `anthropic/claude-haiku-5.5` without fallback. Presentation/design images run in the backend, with at most three generated images per presentation. The configured Seedream model must be available to the project's provider; local tests do not establish that availability.

## Database and backend

Apply `20261017_commerce.sql`, `20261018_serverless.sql`, `20261022_referral_only.sql`, `20261023_standard_trial.sql` in order to the same database; do not re-create it. Migrations preserve existing data and unused earned credits. The backend branch must combine the referral-only changes with the Serverless academic worker. `/health` must include `serverless-referral-only-v2`; course/referat orders, including saved drafts, fail closed before enqueue when it does not. The backend remains always on and requires persistent job storage. Serverless does not replace it.

## Configure and deploy

Node 24 is supported. Use the existing isolated checkout, not a worktree. Run:

```bash
npm ci --ignore-scripts --cache /workspace/.cache/npm
npm run configure
npm run check
npm test
NODE_USE_ENV_PROXY=1 npm run deploy
NODE_USE_ENV_PROXY=1 npm run webhook
```

`configure` reads ignored `.env`, `.env.serverless`, and secure runtime variables. Required: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY), OPENROUTER_API_KEY, ADMIN_ID, BACKEND_URL. CHANNEL_USERNAME defaults to @yordamch_AI; set it if using another channel. Keep generated `tgcloud/lib/private.js` private and untracked. Never dump config or enable CLI debug logging while uploading it.

Authenticate using a secure TGCLOUD_TOKEN binding or interactive `npm run login`; this is a Serverless CLI token, not a Bot API token. Never paste tokens into chat or commit them. The managed cloud proxy requires NODE_USE_ENV_PROXY=1 for CLI network requests. No Telegram database migration is needed. Never call raw setWebhook/deleteWebhook. Successful deploy writes BOT_TRANSPORT=serverless locally, guarding against accidental polling.

Verify webhook is in sync, then manually check /start, credits, invitation, free article, design, and course/referat. Local tests mock AI and Telegram; they do not perform purchases, broadcasts or paid model requests.
