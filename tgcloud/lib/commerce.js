import { fetch } from 'sdk';
import config, { PRICES } from './config.js';

export const ERRORS = {
  duplicate_receipt: 'Ushbu chek avval yuborilgan yoki tasdiqlangan.',
  insufficient_balance: 'Balans yetarli emas. Do‘st taklif qiling yoki hisobni to‘ldiring.',
  presentation_access_required: '5 ta do‘st taklif qiling yoki 25 000 so‘mga bir oylik obuna oling.',
  subscription_active: 'Bir oylik obuna allaqachon faol. Qo‘shimcha taqdimot uchun do‘st taklif qiling yoki 10 000 so‘m to‘lang.',
  user_not_registered: 'Avval /start buyrug‘ini bosing.',
  request_conflict: 'Buyurtma ma’lumotlari o‘zgargan. Menyudan yangi buyurtma boshlang.',
  unavailable: 'Hisob tizimiga ulanib bo‘lmadi. Birozdan so‘ng qayta urinib ko‘ring.',
};
export class CommerceError extends Error {
  constructor(code) { super(ERRORS[code] || ERRORS.unavailable); this.code = code; }
}
export async function rest(path, { method = 'GET', body, headers = {} } = {}) {
  const response = await fetch(config.supabaseUrl + '/rest/v1/' + path, {
    method,
    headers: { apikey: config.supabaseKey, Authorization: 'Bearer ' + config.supabaseKey,
      'Content-Type': 'application/json', ...headers },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (!response.ok) {
    const text = await response.text();
    const code = Object.keys(ERRORS).find(key => text.includes(key)) ||
      (text.includes('23505') ? 'duplicate_receipt' : 'unavailable');
    console.error('Supabase request failed', response.status, path.split('?')[0], code);
    throw new CommerceError(code);
  }
  if (response.status === 204) return null;
  const text = await response.text();
  return text ? JSON.parse(text) : null;
}
export const rpc = (name, body = {}) => rest('rpc/' + name, { method: 'POST', body });
export const status = userId => rpc('commerce_status', { p_user_id: userId });
export const register = (user, referrer = null) => rpc('commerce_register', {
  p_user_id: user.id, p_first_name: user.first_name || '', p_last_name: user.last_name || null,
  p_username: user.username || null, p_referrer_id: referrer,
});
export function parseReferrer(value = '') {
  if (!/^ref_[1-9]\d*$/.test(value)) return null;
  const id = Number(value.slice(4));
  return Number.isSafeInteger(id) ? id : null;
}
export function quote(account, service) {
  if (service === 'presentation') {
    if (account.subscription_active && account.subscription_remaining > 0) return { allowed: true, amount: 0 };
    if (account.referral_presentations > 0) return { allowed: true, amount: 0 };
    if (!account.presentation_period_active) return { allowed: false, reason: 'presentation_access_required' };
  }
  if (service === 'course' && account.course_credits > 0) return { allowed: true, amount: 0 };
  return { allowed: Number(account.balance || 0) >= PRICES[service], amount: PRICES[service], reason: 'insufficient_balance' };
}
export const money = value => String(Math.trunc(Number(value) || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
export function accountText(account) {
  const sub = account.subscription_active ? `${account.subscription_remaining} ta (${String(account.subscription_end).slice(0, 10)} gacha)` : 'faol emas';
  return `💳 Balans: ${money(account.balance)} so‘m\n👥 Tasdiqlangan takliflar: ${account.confirmed_referrals} ta\n` +
    `🎁 Keyingi mukofotgacha: ${account.next_reward_in} ta do‘st\n📊 Bepul taqdimotlar: ${account.referral_presentations} ta\n` +
    `📚 Bepul kurs ishlari: ${account.course_credits} ta\n🗓 Obuna: ${sub}`;
}
