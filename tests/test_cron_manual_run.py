from types import SimpleNamespace

import pytest

from nanobot.cli import commands
from nanobot.cron.service import CronService
from nanobot.cron.types import CronJob, CronJobState, CronPayload, CronSchedule


@pytest.mark.asyncio
async def test_run_job_without_handler_marks_error(tmp_path):
    service = CronService(tmp_path / "jobs.json")
    job = service.add_job(
        name="daily",
        schedule=CronSchedule(kind="every", every_ms=60_000),
        message="Good morning!",
    )

    ok = await service.run_job(job.id)

    assert ok is False
    updated = service.list_jobs(include_disabled=True)[0]
    assert updated.state.last_status == "error"
    assert updated.state.last_error is not None
    assert "handler is not configured" in updated.state.last_error


class _FakeChannel:
    def __init__(self):
        self.started = False
        self.stopped = False
        self.sent = []

    async def start(self):
        self.started = True

    async def send(self, msg):
        self.sent.append(msg)

    async def stop(self):
        self.stopped = True


class _FakeCronService:
    last_instance = None

    def __init__(self, store_path):
        self.store_path = store_path
        self.on_job = None
        self._job = CronJob(
            id="0c954077",
            name="daily",
            enabled=True,
            schedule=CronSchedule(kind="cron", expr="0 9 * * *"),
            payload=CronPayload(
                kind="agent_turn",
                message="Good morning!",
                deliver=True,
                channel="matrix",
                to="!room:example.org",
            ),
            state=CronJobState(),
        )
        _FakeCronService.last_instance = self

    def list_jobs(self, include_disabled=False):
        return [self._job]

    async def run_job(self, job_id: str, force: bool = False):
        assert job_id == self._job.id
        assert self.on_job is not None
        await self.on_job(self._job)
        return True


class _FakeAgentLoop:
    last_instance = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = []
        _FakeAgentLoop.last_instance = self

    async def process_direct(self, content: str, session_key: str, channel: str, chat_id: str):
        self.calls.append((content, session_key, channel, chat_id))
        return "Scheduled response"


class _FakeChannelManager:
    def __init__(self, config, bus):
        self.config = config
        self.bus = bus

    def get_channel(self, name: str):
        assert name == "matrix"
        return _fake_channel


class _FakeSessionManager:
    def __init__(self, workspace):
        self.workspace = workspace


_fake_channel = _FakeChannel()


def _fake_config(workspace):
    return SimpleNamespace(
        workspace_path=workspace,
        agents=SimpleNamespace(
            defaults=SimpleNamespace(
                model="test-model",
                max_tool_iterations=3,
                memory_window=10,
            )
        ),
        tools=SimpleNamespace(
            web=SimpleNamespace(search=SimpleNamespace(provider="duckduckgo")),
            exec=SimpleNamespace(timeout=10),
            restrict_to_workspace=False,
        ),
    )


def test_cron_run_deliver_uses_configured_channel(monkeypatch, tmp_path):
    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)
    monkeypatch.setattr("nanobot.config.loader.load_config", lambda: _fake_config(tmp_path))
    monkeypatch.setattr("nanobot.cron.service.CronService", _FakeCronService)
    monkeypatch.setattr("nanobot.agent.loop.AgentLoop", _FakeAgentLoop)
    monkeypatch.setattr("nanobot.channels.manager.ChannelManager", _FakeChannelManager)
    monkeypatch.setattr("nanobot.session.manager.SessionManager", _FakeSessionManager)
    monkeypatch.setattr(commands, "_make_provider", lambda config: object())

    commands.cron_run("0c954077", force=False)

    assert _fake_channel.started is True
    assert _fake_channel.stopped is True
    assert len(_fake_channel.sent) == 1

    outbound = _fake_channel.sent[0]
    assert outbound.channel == "matrix"
    assert outbound.chat_id == "!room:example.org"
    assert outbound.content == "Scheduled response"

    agent = _FakeAgentLoop.last_instance
    assert agent is not None
    assert agent.calls == [
        ("Good morning!", "cron:0c954077", "matrix", "!room:example.org")
    ]
