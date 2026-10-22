from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from commerce import parse_referrer, quote, QUOTA_COSTS, CommerceError
from keyboards import main_menu, access_keyboard
from handlers import payment
from billing import charged_generation
from ai import brain


class State:
    def __init__(self): self.data, self.state = {}, None
    async def clear(self): self.data, self.state = {}, None
    async def update_data(self, **kwargs): self.data.update(kwargs)
    async def get_data(self): return self.data
    async def set_state(self, value): self.state = value


def callback(actor=1, message_id=99):
    message = SimpleNamespace(chat=SimpleNamespace(id=actor), message_id=message_id,
        answer=AsyncMock(), edit_reply_markup=AsyncMock())
    return SimpleNamespace(from_user=SimpleNamespace(id=actor), data='subscribe_confirm',
        message=message, answer=AsyncMock())


@pytest.mark.parametrize('value', ['ref_-1', 'ref_0', 'ref_１２３', 'ref_99999999999999999999999', '123', None])
def test_invalid_referrals(value):
    assert parse_referrer(value) is None


def test_menu_has_referrals_and_no_payment_purchase():
    text = '\n'.join(button.text for row in main_menu.keyboard for button in row)
    assert 'Do‘stlarni taklif qilish' in text and 'Hisob va limitlar' in text
    assert 'Dizayn yaratish' in text
    buttons = [button for row in access_keyboard.inline_keyboard for button in row]
    assert {button.callback_data for button in buttons} == {'invite', 'account'}
    assert 'to‘ldirish' not in text and "to'ldirish" not in text and 'so‘m' not in text
    assert parse_referrer('ref_12345') == 12345


def test_shared_credit_costs_and_free_services_ignore_money_and_old_subscription():
    account = {'referral_credits': 1, 'balance': 1000000, 'subscription_active': True, 'subscription_remaining': 10}
    assert quote(account, 'course')['allowed'] is False
    assert quote(account, 'course')['missing_credits'] == 1
    assert quote(account, 'presentation')['required_credits'] == 1
    assert quote(account, 'design')['allowed'] is True
    for service in ['referat', 'article', 'obyektivka']:
        assert quote({}, service)['allowed'] is True
        assert quote({}, service)['amount'] == 0
        assert quote({}, service)['source'] == 'free'
    assert QUOTA_COSTS['course'] == 2


async def test_only_haiku_is_used_and_failure_has_no_model_fallback(monkeypatch):
    completion = AsyncMock(return_value=SimpleNamespace(choices=[SimpleNamespace(
        finish_reason='stop', message=SimpleNamespace(content='Academic text'))]))
    monkeypatch.setattr(brain, 'openrouter_client', SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=completion))))
    assert await brain.ask_ai('Write a paragraph', retries=1) == 'Academic text'
    assert completion.call_args.kwargs['model'] == 'anthropic/claude-haiku-5.5'
    completion.side_effect = RuntimeError('Provider unavailable')
    with pytest.raises(RuntimeError, match='Claude Haiku 5.5'):
        await brain.ask_ai('Write a paragraph', retries=1)
    assert all(call.kwargs['model'] == brain.ACADEMIC_MODEL for call in completion.call_args_list)


async def test_stale_payment_buttons_only_show_referral_policy():
    event, state = callback(), State()
    await state.update_data(payment_amount=25000)
    await payment.payment_start_callback(event, state)
    event.answer.assert_awaited_once()
    event.message.answer.assert_awaited_once()
    assert 'bekor qilingan' in event.message.answer.call_args.args[0]
    assert await state.get_data() == {}


async def test_new_payments_are_rejected_before_database_access(monkeypatch):
    import database
    def fail(): raise AssertionError('Payment must not access Supabase')
    monkeypatch.setattr(database, 'get_supabase', fail)
    with pytest.raises(CommerceError, match='To‘lovlar yopilgan'):
        await database.create_pending_payment(1, 25000, 'receipt')


async def test_failed_generation_refunds_and_repeated_click_does_not_generate(monkeypatch):
    import billing
    calls = []
    async def rpc(client, name, **kwargs):
        calls.append((name, kwargs))
        if name == 'commerce_reserve':
            return {'created': len([row for row in calls if row[0] == name]) == 1,
                'amount': 0, 'source': 'referral', 'credit_units': 2}
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
