import { readFileSync, writeFileSync, mkdirSync, chmodSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const values = {};
for (const file of ['.env', '.env.serverless']) {
  try {
    for (const line of readFileSync(resolve(root, file), 'utf8').split(/\r?\n/)) {
      const match = line.match(/^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*$/);
      if (!match) continue;
      let value = match[2];
      if (/^["']/.test(value) && value.at(-1) === value[0]) value = value.slice(1, -1);
      else value = value.replace(/\s+#.*$/, '');
      values[match[1]] = value;
    }
  } catch (error) { if (error.code !== 'ENOENT') throw error; }
}
Object.assign(values, process.env);
const config = {
  supabaseUrl: (values.SUPABASE_URL || '').replace(/\/+$/, ''),
  supabaseKey: values.SUPABASE_SERVICE_ROLE_KEY || values.SUPABASE_KEY || '',
  openrouterKey: values.OPENROUTER_API_KEY || '',
  adminIds: (values.ADMIN_ID || '').split(',').map(x => x.trim()).filter(x => /^\d+$/.test(x)).map(Number),
  channel: values.CHANNEL_USERNAME || '@maqolachiuzb',
  backendUrl: (values.BACKEND_URL || (values.MINI_APP_URL || '').replace(/\/miniapp(?:\?.*)?\/?$/, '')).replace(/\/+$/, ''),
  miniAppUrl: (values.MINI_APP_URL || (values.BACKEND_URL ? values.BACKEND_URL.replace(/\/+$/, '') + '/miniapp' : '')).replace(/\/+$/, ''),
  frontendUrl: (values.FRONTEND_URL || 'https://orzu-two.vercel.app').replace(/\/+$/, ''),
};
const missing = [];
for (const [name, value] of Object.entries(config)) {
  if ((['supabaseUrl', 'supabaseKey', 'openrouterKey', 'miniAppUrl'].includes(name) && !value) ||
      (typeof value === 'string' && /YOUR_|REPLACE_|SAME_PROJECT/.test(value))) missing.push(name);
}
if (!config.adminIds.length || config.adminIds.some(x => !Number.isSafeInteger(x) || x <= 0)) missing.push('ADMIN_ID');
for (const name of ['supabaseUrl', 'backendUrl', 'miniAppUrl', 'frontendUrl']) {
  try { if (new URL(config[name]).protocol !== 'https:') missing.push(name); } catch { missing.push(name); }
}
if (!/^@[A-Za-z0-9_]{5,32}$/.test(config.channel)) missing.push('CHANNEL_USERNAME');
if (missing.length) {
  console.error('Sozlanishi kerak: ' + [...new Set(missing)].join(', ') + '. .env yoki .env.serverless ni tekshiring.');
  process.exit(1);
}
const target = resolve(root, 'tgcloud/lib/private.js');
mkdirSync(resolve(root, 'tgcloud/lib'), { recursive: true });
writeFileSync(target, '// Generated locally; backend-only. NEVER commit this file.\nexport default ' + JSON.stringify(config, null, 2) + ';\n', { mode: 0o600 });
chmodSync(target, 0o600);
console.log('Serverless sozlamalari tayyor. Maxfiy qiymatlar chiqarilmadi.');
