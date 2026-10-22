import { registerHooks } from 'node:module';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
import { test } from 'node:test';

const testConfig = { supabaseUrl: 'https://db.invalid', supabaseKey: 'test-service-key',
  openrouterKey: 'test-ai-key', adminIds: [42], channel: '@test_channel',
  backendUrl: 'https://backend.invalid', miniAppUrl: 'https://backend.invalid/miniapp', frontendUrl: 'https://frontend.invalid' };
registerHooks({
  resolve(specifier, context, next) {
    if (specifier === 'sdk') return { url: 'orzu-test:sdk', shortCircuit: true };
    if (specifier === './private.js') return { url: 'orzu-test:config', shortCircuit: true };
    return next(specifier, context);
  },
  load(url, context, next) {
    if (url === 'orzu-test:sdk') return { format: 'module', shortCircuit: true, source:
      'export const api = new Proxy({}, {get: (_, name) => (...args) => globalThis.harness.api(name, ...args)});' +
      'export const fetch = (...args) => globalThis.harness.fetch(...args);' };
    if (url === 'orzu-test:config') return { format: 'module', shortCircuit: true, source: 'export default ' + JSON.stringify(testConfig) };
    return next(url, context);
  },
});
const { default: messageHandler } = await import('../../tgcloud/handlers/message.js');
const { default: callbackHandler } = await import('../../tgcloud/handlers/callback_query.js');
const { sha256, base64 } = await import('../../tgcloud/lib/bytes.js');
const response = (body, code = 200) => ({ ok: code >= 200 && code < 300, status: code,
  json: async () => body, text: async () => body === null ? '' : JSON.stringify(body) });

function harness() {
  const h = { calls: [], sessions: new Map(), done: new Set(), credits: new Map(), balances: new Map(), subscriptions: new Set(),
    users: new Map(), payments: [], jobs: new Map(), member: true, ready: true, blocked: false, sequence: 100,
    bytes: Uint8Array.from([1, 2, 3, 4]), rpcCalls: [] };
  h.account = id => ({ access_mode: 'referral_only', referral_credits: h.credits.get(id) || 0, balance: h.balances.get(id) || 0, confirmed_referrals: 0, next_reward_in: 5,
    referral_presentations: 0, course_credits: 0, subscription_active: h.subscriptions.has(id),
    subscription_remaining: h.subscriptions.has(id) ? 10 : 0, presentation_period_active: h.subscriptions.has(id),
    subscription_end: '2026-11-18T00:00:00Z' });
  h.api = async (method, params) => {
    h.calls.push({ method, params });
    if (method === 'getChatMember') return { status: h.member ? 'member' : 'left' };
    if (method === 'getMe') return { username: 'Yordamchi_taalaba_bot' };
    if (method === 'getFileContent') return h.bytes;
    if (h.blocked && method === 'sendMessage') throw Object.assign(new Error('Forbidden'), { code: 403 });
    return { message_id: ++h.sequence, chat: { id: params.chat_id } };
  };
  h.fetch = async (url, options = {}) => {
    if (url === 'https://backend.invalid/health') return response({ features: h.ready ? ['serverless-referral-only-v2'] : [] });
    if (url === 'https://openrouter.ai/api/v1/chat/completions') {
      const body = JSON.parse(options.body); h.calls.push({ method: 'AI', params: body });
      return response({ choices: [{ finish_reason: 'stop', message: { content: body.model === 'anthropic/claude-haiku-5.5' ?
        'MUNDARIJA\nKIRISH\nI BOB: History\n1.1. Origins\n1.2. Development\nII BOB: Analysis\n2.1. Results\n2.2. Proposals\nXULOSA\nADABIYOTLAR' :
        '{"is_receipt":true,"status":"success","detected_amount":25000,"transaction_id":"TX1234","recipient_card":"4623"}' } }] });
    }
    assert.ok(url.startsWith('https://db.invalid/rest/v1/'), 'Unexpected real network access: ' + url);
    assert.equal(options.headers.apikey, 'test-service-key');
    const path = url.slice('https://db.invalid/rest/v1/'.length);
    const body = options.body ? JSON.parse(options.body) : {};
    if (path.startsWith('rpc/')) {
      const name = path.slice(4); h.rpcCalls.push({ name, body });
      if (name === 'orzu_bot_begin_update') {
        if (h.done.has(body.p_update_key)) return response({ duplicate: true });
        return response({ session: structuredClone(h.sessions.get(body.p_user_id) || {}) });
      }
      if (name === 'orzu_bot_finish_update') {
        if (body.p_success) { h.sessions.set(body.p_user_id, structuredClone(body.p_session)); h.done.add(body.p_update_key); }
        return response(true);
      }
      if (name === 'commerce_register') { h.users.set(body.p_user_id, body); h.calls.push({ method: 'register', params: body }); return response({}); }
      if (name === 'commerce_confirm_referral') return response({ awarded: false });
      if (name === 'commerce_status') return response(h.account(body.p_user_id));
      if (name === 'commerce_subscribe') {
        if (h.subscriptions.has(body.p_user_id)) return response({ message: 'subscription_active' }, 409);
        if ((h.balances.get(body.p_user_id) || 0) < 25000) return response({ message: 'insufficient_balance' }, 402);
        h.balances.set(body.p_user_id, h.balances.get(body.p_user_id) - 25000); h.subscriptions.add(body.p_user_id); return response({});
      }
      if (name === 'commerce_approve_payment' || name === 'commerce_reject_payment') {
        const payment = h.payments.find(x => String(x.id) === body.p_payment_id && x.status === 'pending');
        if (!payment) return response(null);
        payment.status = name === 'commerce_approve_payment' ? 'completed' : 'rejected';
        if (payment.status === 'completed') h.balances.set(payment.user_id, (h.balances.get(payment.user_id) || 0) + payment.amount);
        return response(payment);
      }
      if (name === 'commerce_enqueue') {
        const existing = h.jobs.get(body.p_request_id);
        if (existing) { assert.deepEqual(existing.payload, body.p_payload); return response({ created: false, amount: 0, credit_units: body.p_service === 'course' ? 2 : 0 }); }
        const units = body.p_service === 'course' ? 2 : 0;
        const available = h.credits.get(body.p_user_id) || 0;
        if (available < units) return response({message:'insufficient_referral_credits'},409);
        h.credits.set(body.p_user_id, available - units);
        h.jobs.set(body.p_request_id, { id: body.p_request_id, payload: body.p_payload, status: 'queued' });
        return response({ created: true, amount: 0, credit_units: units });
      }
      throw new Error('Unimplemented RPC ' + name);
    }
    if (path.startsWith('payments')) {
      if (options.method === 'POST') { const p = { ...body, id: h.payments.length + 1 }; h.payments.push(p); return response([p]); }
      const hash = path.match(/receipt_hash=eq\.([^&]+)/)?.[1];
      return response(h.payments.filter(p => !hash || p.receipt_hash === hash));
    }
    if (path.startsWith('commerce_receipt_keys')) return response([]);
    if (path.startsWith('commerce_jobs')) return response([]);
    throw new Error('Unimplemented table ' + path);
  };
  globalThis.harness = h;
  h.message = async (text, id = 1000, extra = {}, updateId = ++h.sequence) => messageHandler({
    message_id: updateId, chat: { id, type: 'private' }, from: { id, first_name: 'Test', is_bot: false }, text, ...extra,
  }, { update: { update_id: updateId } });
  h.callback = async (data, id = 1000, updateId = ++h.sequence) => callbackHandler({ id: 'cb' + updateId, data,
    from: { id, first_name: 'Test', is_bot: false }, message: { message_id: 99,
      chat: { id, type: 'private' }, from: { id: 8277429715, is_bot: true } },
  }, { update: { update_id: updateId } });
  return h;
}

test('SHA256 and base64 match standard implementations, including block boundaries', () => {
  for (const length of [0, 3, 55, 56, 63, 64, 65, 8192, 200000]) {
    const bytes = Uint8Array.from({ length }, (_, i) => i % 251);
    assert.equal(sha256(bytes), createHash('sha256').update(bytes).digest('hex'));
    assert.equal(base64(bytes), Buffer.from(bytes).toString('base64'));
  }
});
test('referral is attributed before membership and survives the next invocation', async () => {
  const h = harness(); h.member = false;
  await h.message('/start ref_987');
  assert.equal(h.calls[0].method, 'register');
  assert.equal(h.calls[0].params.p_referrer_id, 987);
  assert.equal(h.rpcCalls.filter(x => x.name === 'commerce_confirm_referral').length, 0);
  h.member = true; await h.callback('check_subscription');
  assert.equal(h.rpcCalls.filter(x => x.name === 'commerce_confirm_referral').length, 1);
  assert.equal(h.users.get(1000).p_user_id, 1000);
});
test('all stale payment and subscription buttons are retired without financial RPCs', async () => {
  const h = harness(); h.balances.set(1000, 45000);
  h.sessions.set(1000, {step: 'payment_receipt'});
  for (const data of ['subscribe','subscribe_confirm','payment','pay_subscription','pay_10000','send_receipt','approve_12','reject_12','admin_payments']) {
    await h.callback(data); await h.callback(data,42);
  }
  await h.message('/payments');
  await h.message(undefined,1000,{photo:[{file_id:'photo'}]});
  assert.equal(h.balances.get(1000),45000);
  assert.equal(h.payments.length,0);
  assert.ok(!h.rpcCalls.some(x => /subscribe|approve_payment|reject_payment/.test(x.name)));
  assert.ok(!h.calls.some(x => x.method === 'AI'));
});
test('one shared wallet gates paid-quota services while referat and article remain free', async () => {
  const h = harness();
  for (const text of ['Kurs ishi','📊 Taqdimot yaratish','🎨 Dizayn yaratish']) await h.message(text);
  assert.equal(h.sessions.get(1000).doc, undefined);
  assert.ok(!h.calls.some(x => x.params?.reply_markup?.inline_keyboard?.flat().some(b => b.web_app)));
  await h.message('📄 Referat yaratish');
  assert.equal(h.sessions.get(1000).doc.service, 'referat');
  await h.message('📝 Maqola yaratish');
  assert.ok(h.calls.some(x => x.params?.text?.includes('Maqola Claude')));
});
test('course wizard persists across updates, uses Haiku and enqueues once with the approved plan', async () => {
  const h = harness(); h.credits.set(1000, 3);
  await h.message('Kurs ishi');
  for (const value of ['Kushon davlati', 'Universitet', 'Tarix', 'Sardor Orolov', '4-kurs 401-guruh', '30']) await h.message(value);
  let doc = h.sessions.get(1000).doc;
  assert.equal(h.sessions.get(1000).step, 'document_input');
  await h.callback(`d:lang_uz:${doc.nonce}.${doc.revision}`);
  await h.callback(`d:plan:${doc.nonce}.${doc.revision}`);
  doc = h.sessions.get(1000).doc;
  assert.equal(h.sessions.get(1000).step, 'document_plan');
  assert.equal(h.calls.find(x => x.method === 'AI').params.model, 'anthropic/claude-haiku-5.5');
  const data = `d:build:${doc.nonce}.${doc.revision}`;
  await h.callback(data); await h.callback(data);
  assert.equal(h.jobs.size, 1); assert.equal(h.credits.get(1000), 1);
  const job = [...h.jobs.values()][0]; assert.equal(job.payload.plan, doc.plan);
  assert.equal(job.payload.ish_turi, 'KURS ISHI'); assert.equal(job.payload.send_to_telegram, true);
});
test('older backend cannot accept an academic order', async () => {
  const h = harness(); h.ready = false; h.credits.set(1000, 2);
  await h.message('Kurs ishi'); assert.equal(h.sessions.get(1000).doc, undefined);
  assert.equal(h.jobs.size, 0); assert.equal(h.credits.get(1000), 2);
});
test('private conversation cannot be driven by a group message', async () => {
  const h = harness(); await h.message('/start', 1000, { chat: { id: -100, type: 'supergroup' } });
  assert.equal(h.rpcCalls.length, 0);
});
test('blocked recipient completes the stale update without a retry loop', async () => {
  const h = harness(); h.blocked = true;
  await h.message('/start', 1000, {}, 12345);
  assert.ok(h.done.has('update:12345'));
});

test('design opens the correct miniapp tab and old receipt sessions cannot upload a payment', async () => {
  const h = harness(); h.credits.set(1000, 1);
  await h.message('🎨 Dizayn yaratish');
  const buttons = h.calls.flatMap(x => x.params?.reply_markup?.inline_keyboard?.flat() || []);
  assert.ok(buttons.some(b => b.web_app?.url.endsWith('?tab=designs')));
  h.sessions.set(1000, {step:'payment_receipt', payment:{amount:25000}});
  await h.message(undefined,1000,{photo:[{file_id:'photo'}]});
  assert.equal(h.payments.length,0);
  assert.equal(h.sessions.get(1000).step,undefined);
});
test('a lost course allowance before confirmation does not enqueue or consume another wallet', async () => {
  const h = harness(); h.credits.set(1000, 2);
  await h.message('Kurs ishi');
  for (const value of ['History topic','University','Faculty','Test Author','Group 1','30']) await h.message(value);
  let doc = h.sessions.get(1000).doc;
  await h.callback(`d:lang_uz:${doc.nonce}.${doc.revision}`);
  await h.callback(`d:plan:${doc.nonce}.${doc.revision}`);
  doc = h.sessions.get(1000).doc;
  h.credits.set(1000,0); h.balances.set(1000,100000);
  await h.callback(`d:build:${doc.nonce}.${doc.revision}`);
  assert.equal(h.jobs.size,0);
  assert.equal(h.balances.get(1000),100000);
  assert.equal(h.credits.get(1000),0);
});

test('saved course draft cannot enqueue against an older worker after deployment', async () => {
  const h = harness(); h.credits.set(1000, 2); h.ready = false;
  h.sessions.set(1000,{step:'document_plan',doc:{service:'course',nonce:'saved',revision:1,requestId:'saved-order',plan:'Approved outline',data:{}}});
  await h.callback('d:build:saved.1');
  assert.equal(h.jobs.size,0);
  assert.equal(h.credits.get(1000),2);
  assert.ok(!h.rpcCalls.some(x=>x.name==='commerce_enqueue'));
});
