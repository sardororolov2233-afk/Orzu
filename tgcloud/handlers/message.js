import { withUpdate } from '../lib/session.js';
import { onMessage } from '../lib/bot.js';

export default async function (message, ctx) {
  await withUpdate('message', message, ctx, onMessage);
}
