import { fetch } from 'sdk';
import config from './config.js';
import { rpc, rest, status, quote, ERRORS, money } from './commerce.js';
import { generatePlan } from './ai.js';
import { requestId } from './bytes.js';
import { clearSession } from './session.js';
import { inline, button, escape, acknowledge, removeButtons, mainMenu, accessKeyboard, webApp, withQuery } from './ui.js';

const languages = { uz: "O'zbek", en: 'English', ru: 'Русский', fr: 'Français' };
const fields = [
  ['tema', '📝 Mavzuni to‘liq kiriting:', 3, 500],
  ['ish_turi', '📄 Ish turini tanlang:'],
  ['universitet', '🏛 Universitet nomini yozing:', 1, 250],
  ['fakultet', '🏢 Fakultet nomini yozing (kerak bo‘lmasa —):', 1, 250],
  ['muallif', '👤 Ish muallifi — ism va familiya:', 2, 150],
  ['kurs_guruh', '👨‍🎓 Kurs va guruhni yozing:', 1, 150],
  ['sahifa', '📄 Taxminiy sahifa soni (5–100):'],
  ['til', '🌐 Ish qaysi tilda yozilsin?'],
];
const label = key => ({ tema: 'Mavzu', ish_turi: 'Ish turi', universitet: 'Universitet', fakultet: 'Fakultet',
  muallif: 'Muallif', kurs_guruh: 'Kurs / guruh', sahifa: 'Taxminiy sahifa', til: 'Til' })[key];
const tag = session => session.doc.nonce + '.' + session.doc.revision;
const action = (session, name) => `d:${name}:${tag(session)}`;

async function askField(ctx) {
  const doc = ctx.session.doc;
  if (doc.service === 'course' && doc.field === 1) doc.field++;
  const [key, prompt] = fields[doc.field];
  ctx.session.step = 'document_input';
  let keyboard;
  if (key === 'ish_turi') keyboard = inline([button('📄 Referat', action(ctx.session, 'type_REFERAT')),
    button('📝 Mustaqil ish', action(ctx.session, 'type_MUSTAQIL'))]);
  if (key === 'til') keyboard = inline(...Object.entries(languages).map(([id, name]) => [button(name, action(ctx.session, 'lang_' + id))]));
  await ctx.reply(prompt, keyboard);
}
async function nextField(ctx) {
  if (ctx.session.doc.editing) {
    delete ctx.session.doc.editing;
    return confirmation(ctx);
  }
  ctx.session.doc.field++;
  if (ctx.session.doc.field < fields.length) return askField(ctx);
  return confirmation(ctx);
}
async function confirmation(ctx) {
  const doc = ctx.session.doc;
  ctx.session.step = 'document_confirmation';
  await ctx.reply('📋 <b>Ma’lumotlarni tekshiring:</b>\n\n' +
    fields.map(([key]) => `<b>${label(key)}:</b> ${escape(doc.data[key])}`).join('\n'),
    inline([button('📝 Reja tuzish', action(ctx.session, 'plan'))],
      [button('✏️ O‘zgartirish', action(ctx.session, 'edit')), button('🚫 Bekor qilish', action(ctx.session, 'cancel'))]), true);
}
async function showPlan(ctx) {
  const plan = ctx.session.doc.plan;
  for (let i = 0; i < plan.length; i += 3500) await ctx.reply(plan.slice(i, i + 3500));
  const course = ctx.session.doc.service === 'course';
  await ctx.reply(course ? 'Kurs ishi: taklif mukofotidan yoki 30 000 so‘m. Rejani tasdiqlang.' : 'Referat / mustaqil ish: 8 000 so‘m. Rejani tasdiqlang.',
    inline([button('✅ Yaratishni tasdiqlash', action(ctx.session, 'build'))],
      [button('🔄 Boshqa reja', action(ctx.session, 'regenerate')), button('🚫 Bekor qilish', action(ctx.session, 'cancel'))]));
}
async function makePlan(ctx) {
  const doc = ctx.session.doc;
  const offer = quote(await status(ctx.user.id), doc.service);
  if (!offer.allowed) return ctx.reply(ERRORS[offer.reason], accessKeyboard);
  await ctx.reply('⏳ DeepSeek R1 reja tuzmoqda...');
  try {
    const plan = await generatePlan(doc.service, doc.data);
    doc.plan = plan; doc.revision++;
    ctx.session.step = 'document_plan';
    await showPlan(ctx);
  } catch {
    await ctx.reply('Reja tuzilmadi. Pul yoki limit yechilmadi. Qayta urinib ko‘ring.');
    if (doc.plan) { ctx.session.step = 'document_plan'; await showPlan(ctx); }
    else await confirmation(ctx);
  }
}
export async function startDocument(ctx, service) {
  const offer = quote(await status(ctx.user.id), service);
  if (!offer.allowed) return ctx.reply(ERRORS[offer.reason], accessKeyboard);
  let ready = false;
  try {
    const response = await fetch(config.backendUrl + '/health');
    ready = response.ok && (await response.json()).features?.includes('serverless-academic-queue-v1');
  } catch { /* Fail closed before accepting an order on an older backend. */ }
  if (!ready) return ctx.reply('Bu xizmat hozircha tayyor emas. Birozdan so‘ng qayta urinib ko‘ring. Pul yechilmadi.', mainMenu);
  clearSession(ctx.session);
  const id = requestId('orzu:' + service + ':' + ctx.user.id + ':' + ctx.key);
  ctx.session.doc = { service, requestId: id, nonce: id.replaceAll('-', '').slice(0, 10), revision: 0,
    field: 0, data: { uslub: 'Akademik', ish_turi: service === 'course' ? 'KURS ISHI' : 'REFERAT' } };
  await askField(ctx);
}
export async function documentMessage(ctx, message) {
  if (!ctx.session.step?.startsWith('document_')) return false;
  if (ctx.session.step !== 'document_input') {
    await ctx.reply('Davom etish uchun oxirgi xabardagi tugmalardan foydalaning.'); return true;
  }
  const doc = ctx.session.doc;
  const [key, prompt, min, max] = fields[doc.field];
  if (key === 'ish_turi' || key === 'til') { await askField(ctx); return true; }
  const text = (message.text || '').trim();
  if (key === 'sahifa') {
    if (!/^\d+$/.test(text) || Number(text) < 5 || Number(text) > 100) { await ctx.reply(prompt); return true; }
    doc.data.sahifa = Number(text);
  } else {
    if (text.length < min || text.length > max) { await ctx.reply(`${prompt}\n${min}–${max} belgi kiriting.`); return true; }
    doc.data[key] = text;
  }
  await nextField(ctx); return true;
}
export async function documentCallback(ctx, callback) {
  if (!callback.data.startsWith('d:')) return false;
  const [, name, token] = callback.data.split(':');
  const session = ctx.session;
  if (!session.doc || token !== tag(session)) {
    await acknowledge(callback, 'Bu tugma eskirgan. Oxirgi tugmadan foydalaning.', true); return true;
  }
  await acknowledge(callback);
  const doc = session.doc;
  if (name === 'cancel') { clearSession(session); await removeButtons(callback); await ctx.reply('Bekor qilindi.', mainMenu); }
  else if (name.startsWith('type_') && session.step === 'document_input' && fields[doc.field][0] === 'ish_turi') {
    if (!['type_REFERAT', 'type_MUSTAQIL'].includes(name)) return true;
    doc.data.ish_turi = name === 'type_MUSTAQIL' ? 'MUSTAQIL ISH' : 'REFERAT';
    await removeButtons(callback); await nextField(ctx);
  } else if (name.startsWith('lang_') && session.step === 'document_input' && fields[doc.field][0] === 'til') {
    const language = languages[name.slice(5)];
    if (!language) return true;
    doc.data.til = language; await removeButtons(callback); await nextField(ctx);
  } else if ((name === 'plan' && session.step === 'document_confirmation') || (name === 'regenerate' && session.step === 'document_plan')) {
    await removeButtons(callback); await makePlan(ctx);
  } else if (name === 'edit' && session.step === 'document_confirmation') {
    session.step = 'document_edit';
    await ctx.reply('Qaysi ma’lumotni o‘zgartirasiz?', inline(...fields.filter(([key]) => key !== 'ish_turi' || doc.service !== 'course')
      .map(([key]) => [button(label(key), action(session, 'field_' + key))])));
  } else if (name.startsWith('field_') && session.step === 'document_edit') {
    const index = fields.findIndex(([key]) => key === name.slice(6));
    if (index < 0 || (doc.service === 'course' && index === 1)) return true;
    doc.field = index; doc.editing = true; doc.revision++; delete doc.plan;
    await removeButtons(callback); await askField(ctx);
  } else if (name === 'build' && session.step === 'document_plan') {
    const payload = { ...doc.data, plan: doc.plan, send_to_telegram: true };
    const charge = await rpc('commerce_enqueue', { p_user_id: ctx.user.id, p_service: doc.service,
      p_request_id: doc.requestId, p_payload: payload });
    session.lastJob = doc.requestId;
    clearSession(session);
    await removeButtons(callback);
    await ctx.reply(`✅ Buyurtma navbatga qo‘shildi. To‘lov: ${money(charge.amount)} so‘m.\n` +
      'Tayyor fayl shu chatga yuboriladi. Botdan chiqib ketsangiz ham buyurtma saqlanadi.',
      inline([button('🔄 Buyurtma holati', 'job_' + session.lastJob)]));
  } else await ctx.reply('Bu tugma eskirgan. Oxirgi xabardagi tugmadan foydalaning.');
  return true;
}
export async function jobStatus(ctx, id) {
  if (!/^[0-9a-f-]{36}$/i.test(id)) return;
  const jobs = await rest(`commerce_jobs?id=eq.${id}&user_id=eq.${ctx.user.id}&select=id,status,result&limit=1`);
  const job = jobs?.[0];
  if (!job) return ctx.reply('Buyurtma topilmadi.');
  const labels = { queued: '⏳ Buyurtma navbatda.', processing: '⏳ Ishingiz tayyorlanmoqda.',
    failed: 'Ish yakunlanmadi. Band qilingan pul yoki limit qaytarildi.', completed: '✅ Faylingiz tayyor.' };
  if (job.status === 'completed') await ctx.reply(labels.completed,
    webApp('📥 Faylni yuklab olish', withQuery(config.miniAppUrl, 'job', id)));
  else await ctx.reply(labels[job.status] || 'Buyurtma saqlangan.',
    job.status === 'failed' ? mainMenu : inline([button('🔄 Yangilash', 'job_' + id)]));
}
