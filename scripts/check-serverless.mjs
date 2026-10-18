import { readdirSync, readFileSync, existsSync } from 'node:fs';
import { resolve, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = fileURLToPath(new URL('../tgcloud/', import.meta.url));
const files = [];
function scan(dir) {
  for (const item of readdirSync(dir, { withFileTypes: true })) {
    const path = resolve(dir, item.name);
    if (item.isDirectory()) scan(path);
    else if (item.name.endsWith('.js')) files.push(path);
  }
}
scan(root);
let errors = 0;
for (const file of files) {
  const code = readFileSync(file, 'utf8');
  const result = spawnSync(process.execPath, ['--check', file], { encoding: 'utf8' });
  if (result.status !== 0) { console.error(result.stderr); errors++; }
  for (const match of code.matchAll(/\bfrom\s*['"]([^'"]+)['"]/g)) {
    const name = match[1];
    if (/^sdk(?:\/|$)/.test(name)) continue;
    const target = resolve(dirname(file), name);
    if (!name.startsWith('.') || !name.endsWith('.js') || relative(root, target).startsWith('..')) {
      console.error(relative(root, file) + ': platformaga mos kelmaydigan import: ' + name); errors++;
    } else if (!existsSync(target) && !(name === './private.js' && !process.argv.includes('--deploy'))) {
      console.error(relative(root, file) + ': modul topilmadi: ' + name); errors++;
    }
  }
}
if (errors) process.exit(1);
console.log(`${files.length} Serverless moduli tekshirildi.`);
