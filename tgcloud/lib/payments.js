import { clearSession } from './session.js';
import { acknowledge, removeButtons, accessKeyboard } from './ui.js';
export const RETIRED_MESSAGE = 'Obuna va to‘lovlar bekor qilingan. Har bir yangi do‘st taklifi uchun 1 kvota oling.';
export async function paymentMenu(ctx) { clearSession(ctx.session); await ctx.reply(RETIRED_MESSAGE, accessKeyboard); }
export const pendingPayments = paymentMenu;
export async function paymentCallback(ctx, callback) {
  if (!/^(?:payment|subscribe|subscribe_confirm|send_receipt|admin_payments|pay_.*|approve_.*|reject_.*)$/.test(callback.data)) return false;
  await acknowledge(callback); await removeButtons(callback); await paymentMenu(ctx); return true;
}
export async function receiptMessage(ctx) {
  if (!['payment_amount', 'payment_receipt', 'payment_review', 'amount_selection', 'waiting_receipt', 'reviewing'].includes(ctx.session.step) && !ctx.session.step?.startsWith('payment_')) return false;
  await paymentMenu(ctx); return true;
}
