import { api } from 'sdk';
import config from './config.js';
import { rpc, rest, money } from './commerce.js';
import { clearSession } from './session.js';
import { inline, button, acknowledge, removeButtons } from './ui.js';

const adminKeyboard = inline([button('📊 Statistika', 'admin_stats')],
  [button('💳 Kutilayotgan to‘lovlar', 'admin_payments')], [button('📢 Hammaga xabar yuborish', 'admin_broadcast')]);
export async function adminMenu(ctx) {
  if (config.adminIds.includes(ctx.user.id)) await ctx.reply('🔐 Admin paneli', adminKeyboard);
}
export async function adminCallback(ctx, callback) {
  if (!/^(admin_|broadcast_)/.test(callback.data)) return false;
  if (!config.adminIds.includes(ctx.user.id)) { await acknowledge(callback, 'Ruxsat yo‘q.', true); return true; }
  await acknowledge(callback);
  if (callback.data === 'admin_stats') {
    const stats = await rpc('orzu_bot_stats');
    await ctx.reply(`📊 Foydalanuvchilar: ${stats.users}\nShu oyda qo‘shilganlar: ${stats.monthly_users}\n` +
      `Kutilayotgan to‘lovlar: ${stats.pending_payments}\nShu oygi tushum: ${money(stats.monthly_revenue)} so‘m\n` +
      `Jami tushum: ${money(stats.revenue)} so‘m\nBajarilgan ishlar: ${stats.completed_jobs}`, adminKeyboard);
  } else if (callback.data === 'admin_payments') {
    // Reuse the same receipt list and approval code as /payments.
    return 'payments';
  } else if (callback.data === 'admin_broadcast') {
    clearSession(ctx.session); ctx.session.step = 'broadcast_input';
    await ctx.reply('Barcha foydalanuvchilarga yuboriladigan matn, rasm yoki videoni yuboring. Bekor qilish: /cancel');
  } else if (callback.data.startsWith('broadcast_go_')) {
    const batch = ctx.session.broadcast;
    if (!batch || callback.data !== 'broadcast_go_' + batch.token + '_' + batch.cursor) {
      await ctx.reply('Bu yuborish tugmasi eskirgan. Oxirgi tugmadan foydalaning.'); return true;
    }
    await removeButtons(callback);
    const users = await rest(`users?select=telegram_id&telegram_id=gt.${batch.cursor}&order=telegram_id.asc&limit=15`);
    for (const row of users || []) {
      try {
        await api.copyMessage({ chat_id: row.telegram_id, from_chat_id: batch.chatId, message_id: batch.messageId });
        batch.sent++;
      } catch { batch.failed++; }
      batch.cursor = row.telegram_id;
    }
    const text = `📢 Yuborildi: ${batch.sent}. Yuborilmadi: ${batch.failed}.`;
    if ((users?.length || 0) < 15) { clearSession(ctx.session); await ctx.reply(text, adminKeyboard); }
    else await ctx.reply(text + '\nKeyingi 15 foydalanuvchiga davom ettirish:',
      inline([button('Davom ettirish', 'broadcast_go_' + batch.token + '_' + batch.cursor)]));
  }
  return true;
}
export async function broadcastMessage(ctx, message) {
  if (ctx.session.step !== 'broadcast_input' || !config.adminIds.includes(ctx.user.id)) return false;
  if (!message.text && !message.photo && !message.video) { await ctx.reply('Matn, rasm yoki video yuboring.'); return true; }
  ctx.session.step = 'broadcast_confirm';
  ctx.session.broadcast = { chatId: ctx.chatId, messageId: message.message_id,
    token: String(message.message_id), cursor: 0, sent: 0, failed: 0 };
  await api.copyMessage({ chat_id: ctx.chatId, from_chat_id: ctx.chatId, message_id: message.message_id });
  await ctx.reply('Ushbu xabarni foydalanuvchilarga yuborishni tasdiqlang:',
    inline([button('✅ Yuborish', 'broadcast_go_' + message.message_id + '_0')], [button('❌ Bekor qilish', 'back_main')]));
  return true;
}
