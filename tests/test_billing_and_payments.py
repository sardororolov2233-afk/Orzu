from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from commerce import parse_referrer, quote, PAYMENT_CARD
from keyboards import main_menu, access_keyboard
from handlers import payment
from billing import charged_generation
from ai import brain
from ai.receipt_verifier import TARGET_CARD_FULL


class State:
    def __init__(self): self.data, self.state = {}, None
    async def clear(self): self.data, self.state = {}, None
    async def update_data(self, **kwargs): self.data.update(kwargs)
    async def get_data(self): return self.data
    async def set_state(self, value): self.state = value


def callback(actor=1, message_id=99):
    message = SimpleNamespace(chat=SimpleNamespace(id=actor), message_id=message_id,
        answer=AsyncMock(), edit_reply_markup=AsyncMock())
    return SimpleNamespace(from_user=SimpleNamespace(id=actor), data='approve_123',
        message=message, answer=AsyncMock())


@pytest.mark.parametrize('value', ['ref_-1', 'ref_0', 'ref_１２３', 'ref_99999999999999999999999', '123', None])
def test_invalid_referrals(value):
    assert parse_referrer(value) is None


def test_menu_and_card_contract():
    text = '\n'.join(button.text for row in main_menu.keyboard for button in row)
    assert 'Do‘stlarni taklif qilish' in text
    assert 'Hisob va limitlar' in text
    assert 'PRO' not in text and 'Oddiy' not in text
    assert PAYMENT_CARD == TARGET_CARD_FULL == '9860020144204623'
    assert any(button.callback_data == 'subscribe' for row in access_keyboard.inline_keyboard for button in row)
    assert parse_referrer('ref_12345') == 12345


async def test_only_r1_is_used_and_failure_has_no_model_fallback(monkeypatch):
    completion = AsyncMock(return_value=SimpleNamespace(choices=[SimpleNamespace(
        finish_reason='stop', message=SimpleNamespace(content='<think>reasoning</think>Academic text'))]))
    monkeypatch.setattr(brain, 'openrouter_client', SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=completion))))
    assert await brain.ask_ai('Write a paragraph', retries=1) == 'Academic text'
    assert completion.call_args.kwargs['model'] == 'deepseek/deepseek-r1-0528'
    completion.side_effect = RuntimeError('Provider unavailable')
    with pytest.raises(RuntimeError, match='DeepSeek R1'):
        await brain.ask_ai('Write a paragraph', retries=1)
    assert all(call.kwargs['model'] == brain.ACADEMIC_MODEL for call in completion.call_args_list)


async def test_unauthorized_payment_buttons_never_mutate_database(monkeypatch):
    monkeypatch.setattr(payment, 'ADMIN_IDS', [42])
    approve, reject = AsyncMock(), AsyncMock()
    monkeypatch.setattr(payment, 'approve_pending_payment', approve)
    monkeypatch.setattr(payment, 'reject_pending_payment', reject)
    event = callback(7)
    await payment.approve_payment(event, SimpleNamespace())
    event.data = 'reject_123'
    await payment.reject_payment(event, SimpleNamespace())
    approve.assert_not_awaited()
    reject.assert_not_awaited()


async def test_admin_uuid_payment_id_is_supported(monkeypatch):
    monkeypatch.setattr(payment, 'ADMIN_IDS', [42])
    approve = AsyncMock(return_value=None)
    monkeypatch.setattr(payment, 'approve_pending_payment', approve)
    event = callback(42)
    payment_id = str(uuid4())
    event.data = 'approve_' + payment_id
    await payment.approve_payment(event, SimpleNamespace())
    approve.assert_awaited_once_with(payment_id)


async def test_valid_receipt_waits_for_admin_instead_of_auto_crediting(monkeypatch):
    monkeypatch.setattr(payment, 'ADMIN_IDS', [42])
    monkeypatch.setattr(payment, 'verify_receipt_image', AsyncMock(return_value={
        'is_valid': True, 'transaction_id': 'bank-123'}))
    save, approve = AsyncMock(return_value='123'), AsyncMock()
    monkeypatch.setattr(payment, 'create_pending_payment', save)
    monkeypatch.setattr(payment, 'approve_pending_payment', approve)
    progress = SimpleNamespace(edit_text=AsyncMock())
    message = SimpleNamespace(from_user=SimpleNamespace(id=99, username='student', full_name='Student'),
        photo=[SimpleNamespace(file_id='photo')], answer=AsyncMock(return_value=progress))
    async def download(path, destination): destination.write(b'receipt image')
    bot = SimpleNamespace(get_file=AsyncMock(return_value=SimpleNamespace(file_size=20, file_path='photo')),
        download_file=download, send_photo=AsyncMock())
    state = State()
    await state.update_data(payment_amount=25000, payment_purpose='subscription')
    await payment.process_receipt(message, state, bot)
    save.assert_awaited_once()
    assert save.call_args.kwargs['purpose'] == 'subscription'
    approve.assert_not_awaited()
    bot.send_photo.assert_awaited_once()


async def test_failed_generation_refunds_and_repeated_click_does_not_generate(monkeypatch):
    import billing
    calls = []
    async def rpc(client, name, **kwargs):
        calls.append((name, kwargs))
        if name == 'commerce_reserve':
            return {'created': len([row for row in calls if row[0] == name]) == 1,
                'amount': 30000, 'source': 'balance'}
        return {'status': 'refunded'}
    monkeypatch.setattr(billing, 'rpc', rpc)
    monkeypatch.setattr(billing, 'get_supabase', lambda: object())
    count = 0
    @charged_generation('course')
    async def generate(event, state):
        nonlocal count
        count += 1
        raise RuntimeError('Provider failed')
    event, state = callback(), State()
    await generate(event, state)
    refunds = [row for row in calls if row[0] == 'commerce_finish']
    assert refunds[0][1]['p_success'] is False
    first_request = calls[0][1]['p_request_id']
    await generate(event, state)
    assert count == 1
    assert calls[-1][1]['p_request_id'] == first_request
    assert len([row for row in calls if row[0] == 'commerce_finish']) == 1


def test_dispatcher_builds_with_all_service_routers():
    from main import build_dispatcher
    dispatcher = build_dispatcher()
    assert len(dispatcher.sub_routers) == 7
