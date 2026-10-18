import { api } from 'sdk';
import config from './config.js';

export const inline = (...rows) => ({ inline_keyboard: rows });
export const button = (text, callback_data) => ({ text, callback_data });
export const mainMenu = { resize_keyboard: true, keyboard: [
  ['📊 Taqdimot yaratish', 'Kurs ishi'], ['📄 Referat yaratish', '📝 Maqola yaratish'],
  ['🎁 Do‘stlarni taklif qilish', '👤 Hisob va limitlar'], ["💳 Hisobni to'ldirish", '💵 Narxlar'],
  ['📋 Obyektivka tayyorlash', '🆘 Yordam'],
].map(row => row.map(text => ({ text }))) };
export const accessKeyboard = inline([button('🎁 5 ta do‘st taklif qilish', 'invite')],
  [button('🗓 Bir oylik obuna — 25 000 so‘m', 'subscribe')],
  [button('💳 Hisobni to‘ldirish', 'payment'), button('👤 Limitlarim', 'account')]);
export const channelKeyboard = inline([{ text: '📢 Kanalga a’zo bo‘lish', url: 'https://t.me/' + config.channel.slice(1) }],
  [button('✅ Tasdiqlash', 'check_subscription')]);
export const paymentKeyboard = inline([button('🗓 Obuna — 25 000 so‘m', 'pay_subscription')],
  [button('8 000 so‘m', 'pay_8000'), button('10 000 so‘m', 'pay_10000')],
  [button('30 000 so‘m', 'pay_30000'), button('50 000 so‘m', 'pay_50000')], [button('⬅️ Orqaga', 'back_main')]);
export const subscriptionKeyboard = inline([button('✅ Balansdan 25 000 so‘mga sotib olish', 'subscribe_confirm')],
  [button('💳 Karta orqali 25 000 so‘m to‘lash', 'pay_subscription')], [button('🎁 Do‘st taklif qilish', 'invite')]);
export const receiptKeyboard = inline([button('📤 Chek yuborish', 'send_receipt')], [button('⬅️ Bekor qilish', 'payment_cancel')]);
export const approvalKeyboard = id => inline([button('✅ Tasdiqlash', 'approve_' + id), button('❌ Rad etish', 'reject_' + id)]);
export const escape = value => String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
export const withQuery = (url, key, value) => url + (url.includes('?') ? '&' : '?') + encodeURIComponent(key) + '=' + encodeURIComponent(value);
export const webApp = (text, url) => inline([{ text, web_app: { url } }]);
export const send = (chatId, text, replyMarkup, html = false) => api.sendMessage({
  chat_id: chatId, text, ...(replyMarkup ? { reply_markup: replyMarkup } : {}), ...(html ? { parse_mode: 'HTML' } : {}),
});
export async function notify(chatId, text, replyMarkup) {
  try { return await send(chatId, text, replyMarkup); }
  catch { console.warn('User notification unavailable'); return null; }
}
export async function acknowledge(callback, text, alert = false) {
  try { await api.answerCallbackQuery({ callback_query_id: callback.id, ...(text ? { text } : {}), show_alert: alert }); }
  catch (error) { if (error.code !== 400) throw error; }
}
export async function removeButtons(callback) {
  try { await api.editMessageReplyMarkup({ chat_id: callback.message.chat.id,
    message_id: callback.message.message_id, reply_markup: { inline_keyboard: [] } }); }
  catch (error) { if (error.code !== 400) console.warn('Old keyboard could not be updated'); }
}
