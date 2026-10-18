import { rpc, CommerceError } from './commerce.js';
import { send, acknowledge, notify, accessKeyboard } from './ui.js';

export function clearSession(session) {
  const lastJob = session.lastJob;
  for (const key of Object.keys(session)) delete session[key];
  if (lastJob) session.lastJob = lastJob;
}

// Each invocation may run in a different isolate. The shared PostgreSQL lease
// serializes a user's conversation; the update ledger suppresses redelivery.
export async function withUpdate(kind, payload, context, handler) {
  const user = payload.from;
  const chat = kind === 'message' ? payload.chat : payload.message?.chat;
  if (!user || user.is_bot || !chat || chat.type !== 'private' || chat.id !== user.id) return;
  const updateId = context?.update?.update_id;
  const key = Number.isSafeInteger(updateId) ? 'update:' + updateId :
    kind === 'message' ? `message:${chat.id}:${payload.message_id}` : 'callback:' + payload.id;
  const start = await rpc('orzu_bot_begin_update', { p_user_id: user.id, p_update_key: key });
  if (start.duplicate) { if (kind === 'callback_query') await acknowledge(payload); return; }
  if (start.busy) throw new Error('Previous update still processing; retry delivery');
  const session = start.session || {};
  const ctx = { user, chatId: chat.id, session, key,
    callback: kind === 'callback_query' ? payload : null,
    reply: (text, keyboard, html) => send(chat.id, text, keyboard, html),
  };
  let success = false;
  try {
    try {
      await handler(ctx, payload);
    } catch (error) {
      if (error instanceof CommerceError) {
        if (ctx.callback) await acknowledge(ctx.callback);
        await notify(ctx.chatId, error.message, accessKeyboard);
      } else if (error.code === 403) {
        // Stale updates from a blocked recipient do not need redelivery.
        console.warn('Recipient unavailable');
      } else throw error;
    }
    success = true;
  } finally {
    const finished = await rpc('orzu_bot_finish_update', {
      p_user_id: user.id, p_update_key: key, p_session: session, p_success: success,
    });
    if (success && !finished) throw new Error('Conversation lease was lost');
  }
}
