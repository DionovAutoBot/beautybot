"""SQL-схема базы данных."""

CREATE_TABLES_SQL = """
-- Категории услуг (маникюр, педикюр, ресницы, брови...)
CREATE TABLE IF NOT EXISTS service_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    emoji TEXT DEFAULT '💅',
    sort_order INTEGER DEFAULT 0
);

-- Услуги (конкретные позиции прайса)
CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER,
    name TEXT NOT NULL,
    price TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    is_active INTEGER DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY (category_id) REFERENCES service_categories(id)
);

-- Слоты рабочего времени
CREATE TABLE IF NOT EXISTS slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL DEFAULT 60,
    is_available INTEGER DEFAULT 1,
    UNIQUE(date, start_time)
);

-- Записи клиентов
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    slot_id INTEGER NOT NULL,
    service_id INTEGER,
    client_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    comment TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (slot_id) REFERENCES slots(id),
    FOREIGN KEY (service_id) REFERENCES services(id)
);

-- Пользователи
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_slots_date ON slots(date);
CREATE INDEX IF NOT EXISTS idx_slots_available ON slots(date, is_available);
CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
"""

# Стартовые данные: категории и услуги маникюрного салона
INITIAL_DATA_SQL = """
INSERT OR IGNORE INTO service_categories (id, name, emoji, sort_order) VALUES
    (1, 'Маникюр', '💅', 1),
    (2, 'Педикюр', '🦶', 2),
    (3, 'Наращивание', '💎', 3),
    (4, 'Дизайн', '🎨', 4);

INSERT OR IGNORE INTO services (id, category_id, name, price, duration_minutes, sort_order) VALUES
    -- Маникюр
    (1,  1, 'Маникюр без покрытия',            '1500₽',        60,  1),
    (2,  1, 'Маникюр + гель-лак',               '2500₽',        90,  2),
    (3,  1, 'Маникюр + гель-лак (снятие)',       '2800₽',        90,  3),
    (4,  1, 'Комбинированный маникюр + гель-лак','2700₽',        90,  4),
    (5,  1, 'Снятие гель-лака',                  '500₽',         30,  5),
    (6,  1, 'Мужской маникюр',                   '1800₽',        60,  6),
    -- Педикюр
    (7,  2, 'Педикюр без покрытия',              '2500₽',       90,  1),
    (8,  2, 'Педикюр + гель-лак',                '3500₽',       120, 2),
    (9,  2, 'Аппаратный педикюр',                '3000₽',       90,  3),
    (10, 2, 'Комплекс: маникюр + педикюр',       '5500₽',       180, 4),
    -- Наращивание
    (11, 3, 'Наращивание ногтей гелем',          'от 3500₽',    120, 1),
    (12, 3, 'Наращивание ногтей полигелем',      'от 4000₽',    120, 2),
    (13, 3, 'Наращивание: Френч',                'от 4500₽',    120, 3),
    (14, 3, 'Коррекция наращивания',             'от 2500₽',    90,  4),
    (15, 3, 'Снятие наращенных ногтей',          '600₽',        30,  5),
    -- Дизайн
    (16, 4, 'Дизайн (1 ноготь)',                 '100₽',        15,  1),
    (17, 4, 'Дизайн (все ногти)',                '500₽',        30,  2),
    (18, 4, 'Втирка / Кошачий глаз',             '300₽',        15,  3),
    (19, 4, 'Наклейки / фольга',                 '200₽',        15,  4);
"""
