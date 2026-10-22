import { fetch } from 'sdk';
import config, { QUOTA_COSTS } from './config.js';

export const ERRORS = {
  insufficient_referral_credits: 'Taklif kvotasi yetarli emas. Har bir yangi do‘st — 1 kvota. Taqdimot/dizayn — 1, kurs ishi — 2 kvota.',
  subscriptions_disabled: 'Obuna bekor qilingan. Do‘st taklif qilib kvota oling.',
  payments_disabled: 'To‘lovlar yopilgan. Do‘st taklif qilib kvota oling.',
  invalid_service: 'Noto‘g‘ri xizmat tanlandi.',
  policy_mismatch: 'Xizmat yangilanmoqda. Birozdan so‘ng qayta urinib ko‘ring.',
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
  let required = QUOTA_COSTS[service];
  if (['referat', 'article', 'obyektivka'].includes(service) && !account.standard_trial_enabled) return { allowed: false, reason: 'policy_mismatch' };
  if (['referat', 'article', 'obyektivka'].includes(service) && Number(account.standard_free_remaining || 0) > 0) required = 0;
  const available = Number(account.referral_credits || 0);
  if (!Number.isInteger(required)) return { allowed: false, reason: 'invalid_service' };
  if (account.access_mode !== 'referral_only') return { allowed: false, reason: 'policy_mismatch' };
  return { allowed: available >= required, amount: 0, source: required ? 'referral' : 'free',
    required_credits: required, missing_credits: Math.max(0, required - available),
    reason: available < required ? 'insufficient_referral_credits' : null };
}
export const money = value => String(Math.trunc(Number(value) || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
export function accountText(account) {
  return `👥 Tasdiqlangan takliflar: ${account.confirmed_referrals} ta\n🎁 Qolgan umumiy kvota: ${account.referral_credits} ta\n` +
    `📊 Taqdimot yoki dizayn: ${account.referral_credits} martagacha\n📚 Yoki kurs ishi: ${account.course_credits} martagacha\n` +
    `📄 Referat/maqola/obyektivka uchun qolgan bepul foydalanish: ${account.standard_free_remaining || 0}/3.\n` +
    'Bu imkoniyatlar bitta umumiy kvotadan sarflanadi.';
}
