// Only called AFTER a successful push: prevent a legacy service restart from
// deleting the webhook Telegram Serverless manages for this same bot.
import { readFileSync, writeFileSync, chmodSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const path = fileURLToPath(new URL('../.env', import.meta.url));
let text = '';
try { text = readFileSync(path, 'utf8'); } catch (error) { if (error.code !== 'ENOENT') throw error; }
const setting = /^\s*(?:export\s+)?BOT_TRANSPORT\s*=.*$/gm;
if (setting.test(text)) text = text.replace(setting, 'BOT_TRANSPORT=serverless');
else text = text.replace(/\s*$/, '\n') + 'BOT_TRANSPORT=serverless\n';
writeFileSync(path, text, { mode: 0o600 });
chmodSync(path, 0o600);
console.log('BOT_TRANSPORT=serverless saqlandi. Eski polling jarayoni/servisini to‘xtating.');
