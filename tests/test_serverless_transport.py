import pytest


@pytest.mark.asyncio
async def test_legacy_polling_cannot_remove_serverless_webhook(monkeypatch):
    import main
    monkeypatch.setenv('BOT_TRANSPORT', 'serverless')

    async def forbidden_rpc(*args, **kwargs):
        pytest.fail('Legacy startup must stop before contacting external services')

    monkeypatch.setattr(main, 'rpc', forbidden_rpc)
    with pytest.raises(RuntimeError, match='Serverless'):
        await main.main()
