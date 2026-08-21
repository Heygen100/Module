from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

from telethon import events
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.functions.messages import EditChatDefaultBannedRightsRequest
from telethon.tl.types import ChatBannedRights

from core.lib.loader.module_base import ModuleBase, command, watcher

UTC = timezone.utc

LOCK_TYPES: dict[str, str] = {
    "media": "send_media",
    "stickers": "send_stickers",
    "gifs": "send_gifs",
    "polls": "send_polls",
    "links": "embed_links",
    "forwards": "send_plain",
    "all": "send_messages",
}


class Guard(ModuleBase):
    name = "Guard"
    version = "1.0.0"
    author = "@rich_beluga"
    description = {
        "ru": "Антифлуд, лок чата и массовая чистка сообщений.",
        "en": "Antiflood, chat lock, and bulk message purge.",
    }

    DEFAULT_FLOOD_COUNT = 8
    DEFAULT_FLOOD_WINDOW = 10
    DEFAULT_MUTE_MINUTES = 15

    strings = {
        "ru": {
            "not_a_group": '<blockquote>❌ Команда работает только в группах/супергруппах.</blockquote>',
            "flood_on": "<blockquote>🛡 Антифлуд включён для этого чата.</blockquote>",
            "flood_off": "<blockquote>🛡 Антифлуд выключен для этого чата.</blockquote>",
            "flood_set": "<blockquote>🛡 Настройки антифлуда: <code>{count}</code> сообщ. за <code>{window}</code>с → мут на <code>{mute}</code>мин.</blockquote>",
            "flood_bad_args": "<blockquote>❌ Использование: <code>setflood {количество} {секунды} {минуты_мута}</code></blockquote>",
            "flood_triggered": "<blockquote>🚫 <code>{user}</code> замучен на {mute}мин за флуд.</blockquote>",
            "lock_bad_type": "<blockquote>❌ Тип: <code>media, stickers, gifs, polls, links, forwards, all</code></blockquote>",
            "locked": "<blockquote>🔒 <code>{type}</code> заблокирован в этом чате.</blockquote>",
            "unlocked": "<blockquote>🔓 <code>{type}</code> разблокирован в этом чате.</blockquote>",
            "purge_need_reply_or_count": "<blockquote>❌ Ответь на сообщение (удалит всё до него) или укажи число: <code>purge {N}</code></blockquote>",
            "purge_done": "<blockquote>🧹 Удалено сообщений: <b>{count}</b>.</blockquote>",
            "error": "<blockquote>❌ Внутренняя ошибка. Подробности в логе.</blockquote>",
        },
        "en": {
            "not_a_group": '<blockquote>❌ This command only works in groups/supergroups.</blockquote>',
            "flood_on": "<blockquote>🛡 Antiflood enabled for this chat.</blockquote>",
            "flood_off": "<blockquote>🛡 Antiflood disabled for this chat.</blockquote>",
            "flood_set": "<blockquote>🛡 Antiflood settings: <code>{count}</code> msgs / <code>{window}</code>s → mute for <code>{mute}</code>min.</blockquote>",
            "flood_bad_args": "<blockquote>❌ Usage: <code>setflood {count} {seconds} {mute_minutes}</code></blockquote>",
            "flood_triggered": "<blockquote>🚫 <code>{user}</code> muted for {mute}min for flooding.</blockquote>",
            "lock_bad_type": "<blockquote>❌ Type: <code>media, stickers, gifs, polls, links, forwards, all</code></blockquote>",
            "locked": "<blockquote>🔒 <code>{type}</code> locked in this chat.</blockquote>",
            "unlocked": "<blockquote>🔓 <code>{type}</code> unlocked in this chat.</blockquote>",
            "purge_need_reply_or_count": "<blockquote>❌ Reply to a message (deletes everything up to it) or give a number: <code>purge {N}</code></blockquote>",
            "purge_done": "<blockquote>🧹 Deleted messages: <b>{count}</b>.</blockquote>",
            "error": "<blockquote>❌ Internal error. Details written to the log.</blockquote>",
        },
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # in-memory sliding-window message timestamps: {chat_id: {user_id: [ts, ...]}}
        self._flood_track: dict[int, dict[int, list[float]]] = {}

    # ---------- helpers ----------

    def _user_link(self, user: Any) -> str:
        name = (
            getattr(user, "first_name", None)
            or getattr(user, "title", None)
            or str(user.id)
        )
        return f'<a href="tg://user?id={user.id}">{name}</a>'

    async def _get_flood_cfg(self, chat_id: int) -> dict[str, Any]:
        cfg = await self.db.get(f"flood_{chat_id}")
        if isinstance(cfg, dict):
            return cfg
        return {
            "enabled": False,
            "count": self.DEFAULT_FLOOD_COUNT,
            "window": self.DEFAULT_FLOOD_WINDOW,
            "mute": self.DEFAULT_MUTE_MINUTES,
        }

    async def _save_flood_cfg(self, chat_id: int, cfg: dict[str, Any]) -> None:
        await self.db.set(f"flood_{chat_id}", cfg)

    async def _mute_user(self, chat_id: int, user: Any, minutes: int) -> None:
        until = datetime.now(UTC) + timedelta(minutes=minutes)
        await self.client(
            EditBannedRequest(
                chat_id,
                user,
                ChatBannedRights(until_date=until, send_messages=True),
            )
        )

    # ---------- antiflood watcher ----------

    @watcher(incoming=True, only_groups=True)
    async def flood_watcher(self, event: events.NewMessage.Event) -> None:
        if not getattr(event, "sender_id", None):
            return

        chat_id = event.chat_id
        cfg = await self._get_flood_cfg(chat_id)
        if not cfg.get("enabled"):
            return

        now = time.monotonic()
        window = float(cfg.get("window", self.DEFAULT_FLOOD_WINDOW))
        limit = int(cfg.get("count", self.DEFAULT_FLOOD_COUNT))
        mute_minutes = int(cfg.get("mute", self.DEFAULT_MUTE_MINUTES))

        chat_track = self._flood_track.setdefault(chat_id, {})
        stamps = [t for t in chat_track.get(event.sender_id, []) if now - t < window]
        stamps.append(now)
        chat_track[event.sender_id] = stamps

        if len(stamps) < limit:
            return

        chat_track[event.sender_id] = []

        try:
            sender = await event.get_sender()
        except Exception:
            return
        if sender is None or getattr(sender, "is_self", False):
            return

        try:
            await self._mute_user(chat_id, sender, mute_minutes)
        except Exception:
            self.log.warning(f"Antiflood: failed to mute {event.sender_id} in {chat_id}")
            return

        try:
            await self.client.send_message(
                chat_id,
                self.strings(
                    "flood_triggered",
                    user=self._user_link(sender),
                    mute=mute_minutes,
                ),
                parse_mode="html",
            )
        except Exception:
            pass

    # ---------- antiflood commands ----------

    @command(
        "antiflood",
        doc_ru="Вкл/выкл антифлуд для чата. Использование: antiflood {on/off}",
        doc_en="Enable/disable antiflood for this chat. Usage: antiflood {on/off}",
    )
    async def cmd_antiflood(self, event: events.NewMessage.Event) -> None:
        if not event.is_group:
            await self.edit(event, self.strings["not_a_group"], as_html=True)
            return

        arg = self.args_raw(event).strip().lower()
        cfg = await self._get_flood_cfg(event.chat_id)
        cfg["enabled"] = arg != "off"
        await self._save_flood_cfg(event.chat_id, cfg)

        key = "flood_on" if cfg["enabled"] else "flood_off"
        await self.edit(event, self.strings[key], as_html=True)

    @command(
        "setflood",
        doc_ru="Настроить антифлуд. Использование: setflood {кол-во} {секунды} {минуты_мута}",
        doc_en="Configure antiflood. Usage: setflood {count} {seconds} {mute_minutes}",
    )
    async def cmd_setflood(self, event: events.NewMessage.Event) -> None:
        if not event.is_group:
            await self.edit(event, self.strings["not_a_group"], as_html=True)
            return

        parts = self.args_raw(event).split()
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            await self.edit(event, self.strings["flood_bad_args"], as_html=True)
            return

        count, window, mute = (int(p) for p in parts)
        cfg = await self._get_flood_cfg(event.chat_id)
        cfg.update({"count": max(2, count), "window": max(2, window), "mute": max(1, mute)})
        await self._save_flood_cfg(event.chat_id, cfg)

        await self.edit(
            event,
            self.strings("flood_set", count=cfg["count"], window=cfg["window"], mute=cfg["mute"]),
            as_html=True,
        )

    # ---------- lock / unlock ----------

    async def _set_lock(self, event: events.NewMessage.Event, locked: bool) -> None:
        if not event.is_group:
            await self.edit(event, self.strings["not_a_group"], as_html=True)
            return

        lock_type = self.args_raw(event).strip().lower() or "all"
        field = LOCK_TYPES.get(lock_type)
        if not field:
            await self.edit(event, self.strings["lock_bad_type"], as_html=True)
            return

        rights_kwargs = {field: locked}
        try:
            await self.client(
                EditChatDefaultBannedRightsRequest(
                    peer=event.chat_id,
                    banned_rights=ChatBannedRights(until_date=None, **rights_kwargs),
                )
            )
        except Exception:
            await self.edit(event, self.strings["error"], as_html=True)
            return

        key = "locked" if locked else "unlocked"
        await self.edit(event, self.strings(key, type=lock_type), as_html=True)

    @command(
        "lock",
        doc_ru="Заблокировать тип сообщений в чате. Использование: lock {media/stickers/gifs/polls/links/forwards/all}",
        doc_en="Lock a message type in the chat. Usage: lock {media/stickers/gifs/polls/links/forwards/all}",
    )
    async def cmd_lock(self, event: events.NewMessage.Event) -> None:
        await self._set_lock(event, True)

    @command(
        "unlock",
        doc_ru="Разблокировать тип сообщений в чате. Использование: unlock {тип}",
        doc_en="Unlock a message type in the chat. Usage: unlock {type}",
    )
    async def cmd_unlock(self, event: events.NewMessage.Event) -> None:
        await self._set_lock(event, False)

    # ---------- purge ----------

    @command(
        "purge",
        doc_ru="Массово удалить сообщения. Ответь на сообщение или укажи число.",
        doc_en="Bulk-delete messages. Reply to a message or give a count.",
    )
    async def cmd_purge(self, event: events.NewMessage.Event) -> None:
        if not event.is_group:
            await self.edit(event, self.strings["not_a_group"], as_html=True)
            return

        raw = self.args_raw(event).strip()
        ids: list[int] = []

        try:
            if event.reply_to_msg_id:
                async for msg in self.client.iter_messages(
                    event.chat_id,
                    min_id=event.reply_to_msg_id - 1,
                    max_id=event.id,
                ):
                    ids.append(msg.id)
            elif raw.isdigit():
                count = max(1, int(raw))
                async for msg in self.client.iter_messages(event.chat_id, limit=count + 1):
                    ids.append(msg.id)
            else:
                await self.edit(event, self.strings["purge_need_reply_or_count"], as_html=True)
                return
        except Exception:
            await self.edit(event, self.strings["error"], as_html=True)
            return

        if not ids:
            await self.edit(event, self.strings["purge_need_reply_or_count"], as_html=True)
            return

        try:
            await self.client.delete_messages(event.chat_id, ids)
        except Exception:
            await self.edit(event, self.strings["error"], as_html=True)
            return

        try:
            note = await self.client.send_message(
                event.chat_id,
                self.strings("purge_done", count=len(ids)),
                parse_mode="html",
            )
            await note.delete()
        except Exception:
            pass

    async def on_load(self) -> None:
        self.log.info(f"{self.name} v{self.version} by {self.author} — loaded")
