"""
CRUD-функции для работы с БД через aiosqlite.
Все операции асинхронные.
"""
import logging
from datetime import date, datetime, timedelta
from typing import Optional

import aiosqlite

from config import DB_PATH, BOOKING_DAYS_AHEAD
from database.models import CREATE_TABLES_SQL, INITIAL_DATA_SQL

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(CREATE_TABLES_SQL)
            await db.executescript(INITIAL_DATA_SQL)
            await db.commit()
        logger.info("БД инициализирована")
        # Авто-создание слотов если нет ни одного
        await self._auto_create_slots_if_empty()

    async def _auto_create_slots_if_empty(self):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM slots") as c:
                count = (await c.fetchone())[0]
        if count == 0:
            created = await self.add_slots_by_template(
                weekdays=[0, 1, 2, 3, 4, 5],  # Пн-Сб
                start_time="10:00", end_time="20:00",
                duration=60, weeks_ahead=3
            )
            logger.info(f"Авто-создано {created} слотов (Пн-Сб 10-20)")

    # ══ ПОЛЬЗОВАТЕЛИ ══════════════════════════════════════════

    async def upsert_user(self, user_id: int, username: str, first_name: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO users (user_id, username, first_name) VALUES (?,?,?)
                   ON CONFLICT(user_id) DO UPDATE SET
                   username=excluded.username, first_name=excluded.first_name""",
                (user_id, username or "", first_name or "")
            )
            await db.commit()

    # ══ УСЛУГИ ════════════════════════════════════════════════

    async def get_categories(self) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM service_categories ORDER BY sort_order, name"
            ) as c:
                return [dict(r) for r in await c.fetchall()]

    async def get_services_by_category(self, category_id: int) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT s.*, sc.name as category_name, sc.emoji
                   FROM services s
                   LEFT JOIN service_categories sc ON s.category_id = sc.id
                   WHERE s.category_id = ? AND s.is_active = 1
                   ORDER BY s.sort_order, s.name""",
                (category_id,)
            ) as c:
                return [dict(r) for r in await c.fetchall()]

    async def get_all_active_services(self) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT s.*, sc.name as category_name, sc.emoji
                   FROM services s
                   LEFT JOIN service_categories sc ON s.category_id = sc.id
                   WHERE s.is_active = 1
                   ORDER BY sc.sort_order, s.sort_order, s.name"""
            ) as c:
                return [dict(r) for r in await c.fetchall()]

    async def get_service(self, service_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM services WHERE id = ?", (service_id,)
            ) as c:
                r = await c.fetchone()
                return dict(r) if r else None

    # ══ СЛОТЫ ═════════════════════════════════════════════════

    async def get_available_dates(self, min_duration: int = 0) -> list[str]:
        """Даты с доступными слотами >= min_duration минут."""
        today = date.today().isoformat()
        future = (date.today() + timedelta(days=BOOKING_DAYS_AHEAD)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT DISTINCT date FROM slots
                   WHERE date >= ? AND date <= ?
                   AND is_available = 1
                   AND duration_minutes >= ?
                   ORDER BY date""",
                (today, future, min_duration)
            ) as c:
                return [r["date"] for r in await c.fetchall()]

    async def get_slots_for_date(self, date_str: str, min_duration: int = 0) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT * FROM slots
                   WHERE date = ? AND is_available = 1
                   AND duration_minutes >= ?
                   ORDER BY start_time""",
                (date_str, min_duration)
            ) as c:
                return [dict(r) for r in await c.fetchall()]

    async def get_all_slots_for_date(self, date_str: str) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM slots WHERE date = ? ORDER BY start_time",
                (date_str,)
            ) as c:
                return [dict(r) for r in await c.fetchall()]

    async def get_slot(self, slot_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM slots WHERE id = ?", (slot_id,)) as c:
                r = await c.fetchone()
                return dict(r) if r else None

    async def add_slot(self, date_str: str, start_time: str, duration: int) -> Optional[int]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "INSERT INTO slots (date, start_time, duration_minutes) VALUES (?,?,?)",
                    (date_str, start_time, duration)
                ) as c:
                    slot_id = c.lastrowid
                await db.commit()
                return slot_id
        except aiosqlite.IntegrityError:
            return None

    async def delete_slot(self, slot_id: int) -> bool:
        """Удаляет только свободный слот."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT is_available FROM slots WHERE id = ?", (slot_id,)
            ) as c:
                r = await c.fetchone()
                if not r or not r[0]:
                    return False
            await db.execute("DELETE FROM slots WHERE id = ?", (slot_id,))
            await db.commit()
            return True

    async def close_day(self, date_str: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM slots WHERE date = ? AND is_available = 1", (date_str,)
            ) as c:
                count = (await c.fetchone())[0]
            await db.execute(
                "DELETE FROM slots WHERE date = ? AND is_available = 1", (date_str,)
            )
            await db.commit()
            return count

    async def add_slots_by_template(
        self, weekdays: list[int], start_time: str, end_time: str,
        duration: int, weeks_ahead: int = 4
    ) -> int:
        sh, sm = map(int, start_time.split(":"))
        eh, em = map(int, end_time.split(":"))
        times = []
        ch, cm = sh, sm
        while ch * 60 + cm + duration <= eh * 60 + em:
            times.append(f"{ch:02d}:{cm:02d}")
            total = ch * 60 + cm + duration
            ch, cm = total // 60, total % 60

        count = 0
        for offset in range(weeks_ahead * 7):
            d = date.today() + timedelta(days=offset)
            if d.weekday() in weekdays:
                for t in times:
                    if await self.add_slot(d.isoformat(), t, duration):
                        count += 1
        return count

    # ══ ЗАПИСИ ════════════════════════════════════════════════

    async def get_active_booking(self, user_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT b.*, s.date, s.start_time, s.duration_minutes,
                          sv.name as service_name, sv.price, sv.duration_minutes as svc_duration
                   FROM bookings b
                   JOIN slots s ON b.slot_id = s.id
                   LEFT JOIN services sv ON b.service_id = sv.id
                   WHERE b.user_id = ? AND b.status = 'active'
                   AND s.date >= ?
                   ORDER BY s.date, s.start_time LIMIT 1""",
                (user_id, date.today().isoformat())
            ) as c:
                r = await c.fetchone()
                return dict(r) if r else None

    async def create_booking(
        self, user_id: int, slot_id: int, service_id: int,
        client_name: str, phone: str, comment: str = None
    ) -> Optional[int]:
        """Атомарное создание записи + блокировка слота."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT is_available FROM slots WHERE id = ?", (slot_id,)
            ) as c:
                r = await c.fetchone()
                if not r or not r[0]:
                    return None
            await db.execute(
                "UPDATE slots SET is_available = 0 WHERE id = ? AND is_available = 1",
                (slot_id,)
            )
            async with db.execute(
                """INSERT INTO bookings (user_id, slot_id, service_id, client_name, phone, comment)
                   VALUES (?,?,?,?,?,?)""",
                (user_id, slot_id, service_id, client_name, phone, comment)
            ) as c:
                booking_id = c.lastrowid
            await db.commit()
            return booking_id

    async def cancel_booking(self, booking_id: int) -> Optional[dict]:
        """Отмена записи: освобождает слот, возвращает данные."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT b.*, s.date, s.start_time, s.id as slot_id_val,
                          sv.name as service_name
                   FROM bookings b
                   JOIN slots s ON b.slot_id = s.id
                   LEFT JOIN services sv ON b.service_id = sv.id
                   WHERE b.id = ?""",
                (booking_id,)
            ) as c:
                r = await c.fetchone()
                if not r:
                    return None
                data = dict(r)
            await db.execute(
                "UPDATE slots SET is_available = 1 WHERE id = ?", (data["slot_id"],)
            )
            await db.execute(
                "UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,)
            )
            await db.commit()
            return data

    async def get_bookings_for_date(self, date_str: str) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT b.*, s.date, s.start_time,
                          sv.name as service_name, sv.price
                   FROM bookings b
                   JOIN slots s ON b.slot_id = s.id
                   LEFT JOIN services sv ON b.service_id = sv.id
                   WHERE s.date = ? AND b.status = 'active'
                   ORDER BY s.start_time""",
                (date_str,)
            ) as c:
                return [dict(r) for r in await c.fetchall()]

    async def get_booking_by_id(self, booking_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT b.*, s.date, s.start_time,
                          sv.name as service_name, sv.price
                   FROM bookings b
                   JOIN slots s ON b.slot_id = s.id
                   LEFT JOIN services sv ON b.service_id = sv.id
                   WHERE b.id = ?""",
                (booking_id,)
            ) as c:
                r = await c.fetchone()
                return dict(r) if r else None

    async def get_all_active_bookings(self) -> list[dict]:
        today = date.today().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT b.*, s.date, s.start_time,
                          sv.name as service_name
                   FROM bookings b
                   JOIN slots s ON b.slot_id = s.id
                   LEFT JOIN services sv ON b.service_id = sv.id
                   WHERE b.status = 'active' AND s.date >= ?
                   ORDER BY s.date, s.start_time""",
                (today,)
            ) as c:
                return [dict(r) for r in await c.fetchall()]
