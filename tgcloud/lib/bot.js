import { api } from 'sdk';
import config, { POLICY } from './config.js';
import { register, parseReferrer, rpc, status, quote, ERRORS, accountText } from './commerce.js';
import { clearSession } from './session.js';
import { startDocument, documentMessage, documentCallback, jobStatus } from './documents.js';
import { paymentMenu, paymentCallback, receiptMessage, pendingPayments } from './payments.js';
import { adminMenu, adminCallback, broadcastMessage } from './admin.js';
import { send, inline, button, notify, acknowledge, removeButtons, mainMenu, accessKeyboard, channelKeyboard,
  webApp, withQuery } from './ui.js';

async function isMember(userId) {
  try {
    const member = await api.getChatMember({ chat_id: config.channel, user_id: userId });
    return ['member', 'administrator', 'creator'].includes(member.status) || (member.status === 'restricted' && member.is_member === true);
  } catch (error) {
    if (error.code === 400 || error.code === 403) { console.warn('Channel membership check unavailable'); return false; }
    throw error;
  }
}
async function confirmReferral(userId) {
  const result = await rpc('commerce_confirm_referral', { p_user_id: userId });
  if (result.awarded) await notify(result.referrer_id,
    '🎉 Yangi do‘stingiz tasdiqlandi! Umumiy hisobingizga 1 kvota qo‘shildi.', accessKeyboard);
}
async function gate(ctx) {
  await register(ctx.user);
  if (config.adminIds.includes(ctx.user.id)) return true;
  if (!await isMember(ctx.user.id)) {
    if (ctx.callback) await acknowledge(ctx.callback);
    await ctx.reply('Avval rasmiy kanalga a’zo bo‘ling va Tasdiqlash tugmasini bosing.', channelKeyboard); return false;
  }
  await confirmReferral(ctx.user.id); return true;
}
async function welcome(ctx) {
  await ctx.reply('👋 Xush kelibsiz! Bepul xizmatlardan foydalaning yoki do‘st taklif qilib kvota oling.\n\n' + POLICY, accessKeyboard);
  await ctx.reply('Kerakli xizmatni tanlang:', mainMenu);
}
async function invite(ctx) {
  const me = await api.getMe();
  const account = await status(ctx.user.id);
  await ctx.reply(`🎁 Do‘stlaringizga shu havolani yuboring:\nhttps://t.me/${me.username}?start=ref_${ctx.user.id}\n\n` +
    `Tasdiqlangan: ${account.confirmed_referrals} ta. Qolgan kvota: ${account.referral_credits} ta.\n\n` +
    'Har bir yangi do‘st — 1 kvota. Taqdimot/dizayn — 1, kurs ishi — 2 kvota. Do‘st havola orqali /start bosib, kanal a’zoligini tasdiqlashi kerak. ' +
    'O‘zingiz va avval ro‘yxatdan o‘tgan foydalanuvchilar hisoblanmaydi.', accessKeyboard);
}
async function account(ctx) {
  await ctx.reply(accountText(await status(ctx.user.id)) + '\n\n' + POLICY, accessKeyboard);
  if (ctx.session.lastJob) await ctx.reply('Oxirgi buyurtmangiz:', inline([button('🔄 Buyurtma holati', 'job_' + ctx.session.lastJob)]));
}
async function openService(ctx, service) {
  const offer = quote(await status(ctx.user.id), service);
  if (!offer.allowed) return ctx.reply(ERRORS[offer.reason], accessKeyboard);
  clearSession(ctx.session);
  if (service === 'article') {
    return ctx.reply('📝 Maqola Standart oynasida. Uchala standart xizmatga jami 3 ta bepul foydalanish, keyingi har biri — 1 kvota.',
      webApp('📝 Standart oynani ochish', withQuery(config.frontendUrl, 'tab', 'standard')));
  }
  await ctx.reply('📊 Taqdimot yaratish — 1 kvota.',
    webApp('📊 Taqdimot yaratish', withQuery(config.miniAppUrl, 'tab', 'presentations')));
}

export async function onMessage(ctx, message) {
  const text = (message.text || '').trim();
  const command = text.match(/^\/(\w+)(?:@[a-zA-Z0-9_]+)?(?:\s+(.*))?$/);
  if (command?.[1] === 'start') {
    clearSession(ctx.session);
    const argument = (command[2] || '').split(/\s/)[0];
    // Save first attribution before the channel-join screen, exactly as before.
    await register(ctx.user, parseReferrer(argument));
    ctx.session.startAction = argument;
    if (!await isMember(ctx.user.id)) return ctx.reply('Avval rasmiy kanalga a’zo bo‘ling va Tasdiqlash tugmasini bosing.', channelKeyboard);
    await confirmReferral(ctx.user.id);
    if (argument === 'payment') await paymentMenu(ctx);
    else { clearSession(ctx.session); await welcome(ctx); }
    return;
  }
  if (!await gate(ctx)) return;
  if (['menu', 'cancel'].includes(command?.[1]) || text === '⬅️ Asosiy menyu') {
    clearSession(ctx.session); await ctx.reply('Asosiy menyu:', mainMenu);
  } else if (command?.[1] === 'help' || text === '🆘 Yordam') {
    clearSession(ctx.session); await ctx.reply('Yordam: @sardorbekuralov\n/start — menyu\n/cancel — bekor qilish\n👤 Hisob va limitlar — umumiy kvota va qolgan imkoniyatlar.', mainMenu);
  } else if (command?.[1] === 'admin') await adminMenu(ctx);
  else if (command?.[1] === 'payments') await pendingPayments(ctx);
  else if (['💵 Narxlar', '📌 Foydalanish qoidalari'].includes(text)) { clearSession(ctx.session); await ctx.reply(POLICY, accessKeyboard); }
  else if (text === '🎁 Do‘stlarni taklif qilish') { clearSession(ctx.session); await invite(ctx); }
  else if (text === '👤 Hisob va limitlar') { clearSession(ctx.session); await account(ctx); }
  else if (["💳 Hisobni to'ldirish", '💳 Hisobni to‘ldirish'].includes(text)) await paymentMenu(ctx);
  else if (text === '📊 Taqdimot yaratish') await openService(ctx, 'presentation');
  else if (text === '🎨 Dizayn yaratish') {
    const offer = quote(await status(ctx.user.id), 'design');
    if (!offer.allowed) return ctx.reply(ERRORS[offer.reason], accessKeyboard);
    clearSession(ctx.session); await ctx.reply('🎨 Dizayn — 1 umumiy kvota.', webApp('🎨 Dizayn yaratish', withQuery(config.miniAppUrl, 'tab', 'designs')));
  }
  else if (text === '📝 Maqola yaratish') await openService(ctx, 'article');
  else if (text === '📄 Referat yaratish') await startDocument(ctx, 'referat');
  else if (['Kurs ishi', '📚 Kurs ishi', '🎓 Kurs ishi'].includes(text)) await startDocument(ctx, 'course');
  else if (['📋 Obyektivka tayyorlash', 'Obyektivka tayyorlash'].includes(text)) {
    const offer = quote(await status(ctx.user.id), 'obyektivka');
    if (!offer.allowed) return ctx.reply(ERRORS[offer.reason], accessKeyboard);
    clearSession(ctx.session); await ctx.reply('📋 Obyektivka: jami 3 ta bepul standart foydalanish, keyin 1 kvota.', webApp('📋 Standart oynani ochish', withQuery(config.frontendUrl, 'tab', 'standard')));
  } else if (await receiptMessage(ctx, message)) return;
  else if (await broadcastMessage(ctx, message)) return;
  else if (await documentMessage(ctx, message)) return;
  else await ctx.reply('Kerakli xizmatni menyudan tanlang:', mainMenu);
}

export async function onCallback(ctx, callback) {
  if (!callback.data) return acknowledge(callback);
  if (callback.data === 'check_subscription') {
    await register(ctx.user);
    if (!await isMember(ctx.user.id)) return acknowledge(callback, 'Hali kanalga a’zo bo‘lmadingiz yoki a’zolik tekshirilmadi.', true);
    await confirmReferral(ctx.user.id);
    const action = ctx.session.startAction;
    clearSession(ctx.session);
    await acknowledge(callback, 'A’zolik tasdiqlandi!'); await removeButtons(callback);
    if (action === 'payment') await paymentMenu(ctx); else await welcome(ctx);
    return;
  }
  if (!await gate(ctx)) return;
  // Retired payment callbacks must never reach a financial RPC.
  if (await paymentCallback(ctx, callback)) return;
  if (await documentCallback(ctx, callback)) return;
  const handled = await adminCallback(ctx, callback);
  if (handled) { if (handled === 'payments') await pendingPayments(ctx); return; }
  const data = callback.data;
  if (data === 'invite') { await acknowledge(callback); await invite(ctx); }
  else if (data === 'account') { await acknowledge(callback); await account(ctx); }
  else if (['back_main', 'payment_cancel'].includes(data)) {
    clearSession(ctx.session); await acknowledge(callback); await ctx.reply('Asosiy menyu:', mainMenu);
  } else if (data.startsWith('job_')) { await acknowledge(callback); await jobStatus(ctx, data.slice(4)); }
  else await acknowledge(callback, 'Bu tugma eskirgan. Menyudan qayta boshlang.', true);
}
