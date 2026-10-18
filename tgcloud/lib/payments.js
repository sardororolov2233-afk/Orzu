import { api } from 'sdk';
import config, { PAYMENT_CARD } from './config.js';
import { rpc, rest, status, accountText, money, CommerceError } from './commerce.js';
import { sha256 } from './bytes.js';
import { reviewReceipt } from './ai.js';
import { clearSession } from './session.js';
import { acknowledge, removeButtons, paymentKeyboard, receiptKeyboard, approvalKeyboard, accessKeyboard, escape, notify } from './ui.js';

export async function paymentMenu(ctx) {
  clearSession(ctx.session);
  await ctx.reply('💳 ' + accountText(await status(ctx.user.id)).split('\n')[0].replace(/^💳 /, '') +
    '\n\nObuna — 25 000 so‘mga bir oy va 10 ta taqdimot. Boshqa summalar balansga qo‘shiladi.', paymentKeyboard);
}
export async function pendingPayments(ctx) {
  if (!config.adminIds.includes(ctx.user.id)) return;
  const rows = await rest('payments?status=eq.pending&select=*&order=created_at.asc&limit=30');
  if (!rows?.length) return ctx.reply('Kutilayotgan to‘lovlar yo‘q.');
  for (const payment of rows) {
    await api.sendPhoto({ chat_id: ctx.chatId, photo: payment.receipt_file_id,
      caption: `To‘lov #${payment.id} | ${payment.user_id} | ${money(payment.amount)} so‘m | ${payment.purpose}`,
      reply_markup: approvalKeyboard(payment.id) });
  }
}
export async function paymentCallback(ctx, callback) {
  const data = callback.data;
  if (data === 'payment') { await acknowledge(callback); await paymentMenu(ctx); return true; }
  const choices = { pay_8000: 8000, pay_10000: 10000, pay_30000: 30000, pay_50000: 50000, pay_subscription: 25000 };
  if (Object.hasOwn(choices, data)) {
    await acknowledge(callback);
    clearSession(ctx.session);
    ctx.session.step = 'payment_amount';
    ctx.session.payment = { amount: choices[data], purpose: data === 'pay_subscription' ? 'subscription' : 'topup' };
    await ctx.reply(`💳 <b>${data === 'pay_subscription' ? 'Bir oylik obuna (10 ta taqdimot)' : 'Balansni to‘ldirish'}</b>\n` +
      `Summa: ${money(choices[data])} so‘m\nKarta: <code>${PAYMENT_CARD}</code>\nKarta egasi: O‘ralov Sardorbek\n\n` +
      'To‘lovdan keyin chek rasmini yuboring. Kartaga pul tushgani admin tomonidan tekshirilgach balans yoki obuna faollashadi.', receiptKeyboard, true);
    return true;
  }
  if (data === 'send_receipt') {
    await acknowledge(callback);
    if (!ctx.session.payment || ctx.session.step !== 'payment_amount') await paymentMenu(ctx);
    else { ctx.session.step = 'payment_receipt'; await ctx.reply('📸 Chek rasmini yuboring:'); }
    return true;
  }
  if (/^(approve|reject)_[a-zA-Z0-9-]{1,40}$/.test(data)) {
    if (!config.adminIds.includes(ctx.user.id)) { await acknowledge(callback, 'Ruxsat yo‘q.', true); return true; }
    const approve = data.startsWith('approve_');
    const payment = await rpc(approve ? 'commerce_approve_payment' : 'commerce_reject_payment', {
      p_payment_id: data.slice(data.indexOf('_') + 1),
    });
    if (!payment) { await acknowledge(callback, 'Bu to‘lov allaqachon ko‘rib chiqilgan.', true); return true; }
    await acknowledge(callback, approve ? 'To‘lov tasdiqlandi.' : 'To‘lov rad etildi.');
    await removeButtons(callback);
    await notify(payment.user_id, approve ? '✅ To‘lov tasdiqlandi.\n\n' + accountText(await status(payment.user_id)) :
      `❌ ${money(payment.amount)} so‘mlik to‘lov tasdiqlanmadi. Yordam: @sardorbekuralov`, approve ? accessKeyboard : paymentKeyboard);
    return true;
  }
  return false;
}
export async function receiptMessage(ctx, message) {
  if (ctx.session.step !== 'payment_receipt') return false;
  const photo = message.photo?.at(-1);
  if (!photo) { await ctx.reply('📸 Chekni rasm ko‘rinishida yuboring.'); return true; }
  const payment = ctx.session.payment;
  if (!payment) { await paymentMenu(ctx); return true; }
  if (photo.file_size > 10 * 1024 * 1024) { await ctx.reply('Chek rasmi 10 MB dan kichik bo‘lsin.'); return true; }
  await ctx.reply('⏳ Chek qabul qilinmoqda...');
  const bytes = await api.getFileContent(photo.file_id);
  if (bytes.length > 10 * 1024 * 1024) { await ctx.reply('Chek rasmi 10 MB dan kichik bo‘lsin.'); return true; }
  const hash = sha256(bytes);
  const live = await rest(`payments?receipt_hash=eq.${hash}&status=in.(pending,completed)&select=id&limit=1`);
  const old = await rest(`commerce_receipt_keys?kind=eq.hash&key=eq.${hash}&select=key&limit=1`);
  if (live?.length || old?.length) throw new CommerceError('duplicate_receipt');
  const review = await reviewReceipt(bytes, payment.amount);
  const rows = await rest('payments', { method: 'POST', headers: { Prefer: 'return=representation' }, body: {
    user_id: ctx.user.id, amount: payment.amount, purpose: payment.purpose,
    receipt_file_id: photo.file_id, receipt_hash: hash, receipt_tx: review.transaction_id || null,
    review, status: 'pending', username: ctx.user.username || null,
    full_name: [ctx.user.first_name, ctx.user.last_name].filter(Boolean).join(' '),
  } });
  const id = rows?.[0]?.id;
  if (!id) throw new Error('Receipt was not persisted');
  clearSession(ctx.session);
  await ctx.reply(`✅ Chek saqlandi. To‘lov #${id}. Admin tushumni tekshiradi.`, accessKeyboard);
  const note = review.is_valid ? 'AI: mos' : 'AI: ' + (review.rejection_reason || 'Qo‘lda tekshiring.');
  for (const adminId of config.adminIds) {
    try {
      await api.sendPhoto({ chat_id: adminId, photo: photo.file_id,
        caption: `💳 To‘lov #${escape(id)}\nFoydalanuvchi: ${escape(ctx.user.first_name)}\nID: ${ctx.user.id}\n` +
          `Summa: ${money(payment.amount)} so‘m\nTuri: ${payment.purpose}\n${escape(note.slice(0, 350))}\n\nKartaga pul kelganini tekshirib tasdiqlang.`,
        parse_mode: 'HTML', reply_markup: approvalKeyboard(id) });
    } catch { console.warn('Admin notification failed; payment is available in /payments'); }
  }
  return true;
}
