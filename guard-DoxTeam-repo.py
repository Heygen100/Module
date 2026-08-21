from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from telethon import events
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.functions.messages import EditChatDefaultBannedRightsRequest
from telethon.tl.types import ChatBannedRights

from core.lib.loader.module_base import ModuleBase, command, event, watcher

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
            "check_no_target": "<blockquote>❌ Ответь на сообщение или укажи @username/ID.</blockquote>",
            "check_user_not_found": "<blockquote>❌ Пользователь не найден.</blockquote>",
            "check_result": (
                "<blockquote>🔍 <b>Проверка:</b> {user}\n"
                "ID: <code>{id}</code>\n"
                "Флаги: {flags}\n"
                "Оценка риска: <b>{score}</b>/5</blockquote>"
            ),
            "flag_none": "чисто, флагов нет",
            "flag_deleted": "удалённый аккаунт",
            "flag_scam": "помечен как SCAM",
            "flag_fake": "помечен как FAKE",
            "flag_no_photo": "нет фото профиля",
            "flag_no_username": "нет username",
            "flag_bot": "бот-аккаунт",
            "scan_start": "<blockquote>🔎 Сканирую участников...</blockquote>",
            "scan_result": "<blockquote>🔍 <b>Подозрительные участники ({count}):</b>\n{rows}</blockquote>",
            "scan_none": "<blockquote>✅ Подозрительных участников не найдено.</blockquote>",
            "joinalert_on": "<blockquote>🛡 Оповещение о подозрительных новичках включено.</blockquote>",
            "joinalert_off": "<blockquote>🛡 Оповещение о подозрительных новичках выключено.</blockquote>",
            "joinalert_msg": (
                "<blockquote>⚠️ Новый участник с флагами риска: {user}\n"
                "Флаги: {flags}</blockquote>"
            ),
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
            "check_no_target": "<blockquote>❌ Reply to a message or give @username/ID.</blockquote>",
            "check_user_not_found": "<blockquote>❌ User not found.</blockquote>",
            "check_result": (
                "<blockquote>🔍 <b>Check:</b> {user}\n"
                "ID: <code>{id}</code>\n"
                "Flags: {flags}\n"
                "Risk score: <b>{score}</b>/5</blockquote>"
            ),
            "flag_none": "clean, no flags",
            "flag_deleted": "deleted account",
            "flag_scam": "marked SCAM",
            "flag_fake": "marked FAKE",
            "flag_no_photo": "no profile photo",
            "flag_no_username": "no username",
            "flag_bot": "bot account",
            "scan_start": "<blockquote>🔎 Scanning members...</blockquote>",
            "scan_result": "<blockquote>🔍 <b>Suspicious members ({count}):</b>\n{rows}</blockquote>",
            "scan_none": "<blockquote>✅ No suspicious members found.</blockquote>",
            "joinalert_on": "<blockquote>🛡 Suspicious-newcomer alerts enabled.</blockquote>",
            "joinalert_off": "<blockquote>🛡 Suspicious-newcomer alerts disabled.</blockquote>",
            "joinalert_msg": (
                "<blockquote>⚠️ New member with risk flags: {user}\n"
                "Flags: {flags}</blockquote>"
            ),
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
        raw = await self.db.db_get(self.name, f"flood_{chat_id}")
        if raw:
            try:
                cfg = json.loads(raw)
                if isinstance(cfg, dict):
                    return cfg
            except Exception:
                pass
        return {
            "enabled": False,
            "count": self.DEFAULT_FLOOD_COUNT,
            "window": self.DEFAULT_FLOOD_WINDOW,
            "mute": self.DEFAULT_MUTE_MINUTES,
        }

    async def _save_flood_cfg(self, chat_id: int, cfg: dict[str, Any]) -> None:
        await self.db.db_set(self.name, f"flood_{chat_id}", json.dumps(cfg))

    async def _mute_user(self, chat_id: int, user: Any, minutes: int) -> None:
        until = datetime.now(UTC) + timedelta(minutes=minutes)
        await self.client(
            EditBannedRequest(
                chat_id,
                user,
                ChatBannedRights(until_date=until, send_messages=True),
            )
        )

    # ---------- suspicious-account detection ----------

    def _suspicion_flags(self, user: Any) -> tuple[int, list[str]]:
        """Score a user using only public Telegram-provided fields
        (deleted/scam/fake/bot flags, presence of photo/username).
        Heuristic only — meant to help a human admin review, not to
        auto-punish anyone."""
        flags: list[str] = []
        if getattr(user, "deleted", False):
            flags.append("flag_deleted")
        if getattr(user, "scam", False):
            flags.append("flag_scam")
        if getattr(user, "fake", False):
            flags.append("flag_fake")
        if getattr(user, "bot", False):
            flags.append("flag_bot")
        if not getattr(user, "photo", None):
            flags.append("flag_no_photo")
        if not getattr(user, "username", None):
            flags.append("flag_no_username")
        return len(flags), flags

    async def _resolve_target(
        self, event: events.NewMessage.Event, args: list[str]
    ) -> Any | None:
        if event.reply_to_msg_id:
            try:
                reply = await event.get_reply_message()
                if reply and reply.sender:
                    return reply.sender
            except Exception:
                pass
        if args:
            first = args[0]
            try:
                if first.startswith("@"):
                    return await self.client.get_entity(first)
                if first.lstrip("-").isdigit():
                    return await self.client.get_entity(int(first))
            except Exception:
                return None
        return None

    async def _get_joinalert_cfg(self, chat_id: int) -> bool:
        raw = await self.db.db_get(self.name, f"joinalert_{chat_id}")
        return raw == "1"

    async def _save_joinalert_cfg(self, chat_id: int, enabled: bool) -> None:
        await self.db.db_set(self.name, f"joinalert_{chat_id}", "1" if enabled else "0")

    @event("chataction")
    async def on_chat_action(self, event_: events.ChatAction.Event) -> None:
        if not event_.user_joined and not event_.user_added:
            return
        try:
            if not await self._get_joinalert_cfg(event_.chat_id):
                return
            user = await event_.get_user()
        except Exception:
            return
        if user is None or getattr(user, "is_self", False):
            return

        score, flags = self._suspicion_flags(user)
        if score < 2:
            return

        flag_text = ", ".join(self.strings[f] for f in flags)
        try:
            await self.client.send_message(
                event_.chat_id,
                self.strings("joinalert_msg", user=self._user_link(user), flags=flag_text),
                parse_mode="html",
            )
        except Exception:
            pass

    @command(
        "checkuser",
        alias=["cu"],
        doc_ru="Проверить аккаунт на подозрительные признаки. Ответь на сообщение или укажи @username/ID.",
        doc_en="Check an account for suspicious signals. Reply to a message or give @username/ID.",
    )
    async def cmd_checkuser(self, event: events.NewMessage.Event) -> None:
        if not event.is_group:
            await self.edit(event, self.strings["not_a_group"], as_html=True)
            return

        args = self.args_raw(event).split()
        user = await self._resolve_target(event, args)
        if user is None:
            await self.edit(event, self.strings["check_no_target"], as_html=True)
            return

        score, flags = self._suspicion_flags(user)
        flag_text = ", ".join(self.strings[f] for f in flags) if flags else self.strings["flag_none"]

        await self.edit(
            event,
            self.strings(
                "check_result",
                user=self._user_link(user),
                id=user.id,
                flags=flag_text,
                score=score,
            ),
            as_html=True,
        )

    @command(
        "scan",
        doc_ru="Просканировать участников чата на подозрительные признаки.",
        doc_en="Scan chat members for suspicious signals.",
    )
    async def cmd_scan(self, event: events.NewMessage.Event) -> None:
        if not event.is_group:
            await self.edit(event, self.strings["not_a_group"], as_html=True)
            return

        await self.edit(event, self.strings["scan_start"], as_html=True)

        suspicious: list[tuple[Any, int, list[str]]] = []
        try:
            async for user in self.client.iter_participants(event.chat_id, limit=2000):
                score, flags = self._suspicion_flags(user)
                if score >= 2:
                    suspicious.append((user, score, flags))
        except Exception:
            await self.edit(event, self.strings["error"], as_html=True)
            return

        if not suspicious:
            await self.edit(event, self.strings["scan_none"], as_html=True)
            return

        suspicious.sort(key=lambda t: t[1], reverse=True)
        rows = []
        for user, score, flags in suspicious[:25]:
            flag_text = ", ".join(self.strings[f] for f in flags)
            rows.append(f"• {self._user_link(user)} ({score}/5) — {flag_text}")

        await self.edit(
            event,
            self.strings("scan_result", count=len(suspicious), rows="\n".join(rows)),
            as_html=True,
        )

    @command(
        "joinalert",
        doc_ru="Вкл/выкл оповещение о подозрительных новичках. Использование: joinalert {on/off}",
        doc_en="Enable/disable suspicious-newcomer alerts. Usage: joinalert {on/off}",
    )
    async def cmd_joinalert(self, event: events.NewMessage.Event) -> None:
        if not event.is_group:
            await self.edit(event, self.strings["not_a_group"], as_html=True)
            return

        arg = self.args_raw(event).strip().lower()
        enabled = arg != "off"
        await self._save_joinalert_cfg(event.chat_id, enabled)

        key = "joinalert_on" if enabled else "joinalert_off"
        await self.edit(event, self.strings[key], as_html=True)

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

        if event.reply_to_msg_id:
            start_id = event.reply_to_msg_id
        elif raw.isdigit():
            start_id = max(1, event.id - max(1, int(raw)))
        else:
            await self.edit(event, self.strings["purge_need_reply_or_count"], as_html=True)
            return

        # Message IDs are sequential per chat, so the exact set to delete can
        # be built directly instead of relying on iter_messages(min_id=,
        # max_id=) pagination quirks. delete_messages silently ignores IDs
        # that don't exist (already deleted / service messages), so this is
        # safe even across small gaps. Capped to avoid deleting huge ranges
        # by accident.
        ids = list(range(start_id, event.id + 1))[:3000]

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
