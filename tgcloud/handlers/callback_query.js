import { withUpdate } from '../lib/session.js';
import { onCallback } from '../lib/bot.js';

export default async function (callback, ctx) {
  await withUpdate('callback_query', callback, ctx, onCallback);
}
