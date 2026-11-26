-- Схема БД проекта CourseMatch (пакет skillrec).
-- Версия 1. Уточняется по мере работы с реальными данными.
--
-- Слои данных:
--   raw       — сырые ответы API, неизменяемые файлы в data/raw (вне БД);
--   processed — vacancies, courses и связи с навыками;
--   derived   — role_profiles, recommendations, eval_*.
--
-- База считается производной от data/raw: её можно удалить и пересоздать
-- командой `python -m skillrec init-db --force` без потери исходных данных.
--
-- Роли и поисковые запросы (roles, role_queries) заполняются на этапе сбора
-- данных из config.yaml, а не при создании схемы.

PRAGMA foreign_keys = ON;

-- Прогоны стадий. run_id — идентификатор прогона (хэш стадии и параметров),
-- нужен, чтобы отличать результаты, посчитанные с разными настройками.
CREATE TABLE IF NOT EXISTS runs (
    run_id      TEXT PRIMARY KEY,
    stage       TEXT NOT NULL,
    params_json TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ИТ-роли из config.yaml.
CREATE TABLE IF NOT EXISTS roles (
    id    TEXT PRIMARY KEY,
    title TEXT NOT NULL
);

-- Поисковые запросы, которыми роль собирается на источнике вакансий.
CREATE TABLE IF NOT EXISTS role_queries (
    role_id TEXT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    query   TEXT NOT NULL,
    PRIMARY KEY (role_id, query)
);

-- Вакансии. Первичный ключ составной: источник + его идентификатор.
-- role_id — роль, для которой вакансия собрана; при пересечении запросов
-- сохраняется роль, встретившаяся первой.
CREATE TABLE IF NOT EXISTS vacancies (
    source           TEXT NOT NULL DEFAULT 'hh',
    source_id        TEXT NOT NULL,
    role_id          TEXT NOT NULL REFERENCES roles(id),
    query            TEXT,
    name             TEXT NOT NULL,
    employer         TEXT,
    area             TEXT,
    experience       TEXT,
    schedule         TEXT,
    employment       TEXT,
    salary_from      INTEGER,
    salary_to        INTEGER,
    salary_currency  TEXT,
    published_at     TEXT,
    archived         INTEGER NOT NULL DEFAULT 0,
    url              TEXT,
    description_html TEXT,
    description_text TEXT,
    run_id           TEXT REFERENCES runs(run_id),
    fetched_at       TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (source, source_id)
);

-- Канонический словарь навыков. name — каноническое написание.
CREATE TABLE IF NOT EXISTS skills (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL UNIQUE,
    category  TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);

-- Синонимы навыков: каждый синоним указывает ровно на один канонический навык.
CREATE TABLE IF NOT EXISTS skill_aliases (
    alias    TEXT PRIMARY KEY,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE
);

-- Навыки вакансий. extracted_from: key_skills, description или both.
CREATE TABLE IF NOT EXISTS vacancy_skills (
    source         TEXT NOT NULL,
    source_id      TEXT NOT NULL,
    skill_id       INTEGER NOT NULL REFERENCES skills(id),
    extracted_from TEXT NOT NULL DEFAULT 'key_skills'
                   CHECK (extracted_from IN ('key_skills', 'description', 'both')),
    weight         REAL NOT NULL DEFAULT 1.0,
    run_id         TEXT REFERENCES runs(run_id),
    PRIMARY KEY (source, source_id, skill_id),
    FOREIGN KEY (source, source_id) REFERENCES vacancies(source, source_id) ON DELETE CASCADE
);

-- Курсы Stepik. Текст описания хранится уже очищенным от HTML.
CREATE TABLE IF NOT EXISTS courses (
    source          TEXT NOT NULL DEFAULT 'stepik',
    source_id       TEXT NOT NULL,
    title           TEXT NOT NULL,
    summary         TEXT,
    description     TEXT,
    requirements    TEXT,
    target_audience TEXT,
    language        TEXT,
    is_paid         INTEGER,
    price           REAL,
    difficulty      TEXT,
    learners_count  INTEGER,
    time_to_complete INTEGER,
    lessons_count   INTEGER,
    review_summary  TEXT,
    url             TEXT,
    run_id          TEXT REFERENCES runs(run_id),
    fetched_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (source, source_id)
);

-- Навыки курсов. weight — значимость навыка в курсе (бинарно или по частоте).
CREATE TABLE IF NOT EXISTS course_skills (
    source         TEXT NOT NULL,
    source_id      TEXT NOT NULL,
    skill_id       INTEGER NOT NULL REFERENCES skills(id),
    extracted_from TEXT,
    weight         REAL NOT NULL DEFAULT 1.0,
    run_id         TEXT REFERENCES runs(run_id),
    PRIMARY KEY (source, source_id, skill_id),
    FOREIGN KEY (source, source_id) REFERENCES courses(source, source_id) ON DELETE CASCADE
);

-- Профиль компетенций роли: вес навыка и число вакансий, где он встретился.
-- Разные прогоны хранятся отдельно, поэтому run_id входит в первичный ключ.
CREATE TABLE IF NOT EXISTS role_profiles (
    run_id          TEXT NOT NULL REFERENCES runs(run_id),
    role_id         TEXT NOT NULL REFERENCES roles(id),
    skill_id        INTEGER NOT NULL REFERENCES skills(id),
    weight          REAL NOT NULL,
    vacancies_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (run_id, role_id, skill_id)
);

-- Рекомендации: снимок выдачи для прогона.
-- covered_skills и uncovered_skills — JSON-массивы идентификаторов навыков;
-- денормализованы намеренно, чтобы выдача читалась одним запросом.
CREATE TABLE IF NOT EXISTS recommendations (
    run_id            TEXT NOT NULL REFERENCES runs(run_id),
    role_id           TEXT NOT NULL REFERENCES roles(id),
    rank              INTEGER NOT NULL,
    course_source     TEXT NOT NULL,
    course_source_id  TEXT NOT NULL,
    score             REAL NOT NULL,
    method            TEXT NOT NULL DEFAULT 'coverage',
    covered_skills    TEXT,
    uncovered_skills  TEXT,
    PRIMARY KEY (run_id, role_id, course_source, course_source_id),
    FOREIGN KEY (course_source, course_source_id)
        REFERENCES courses(source, source_id) ON DELETE CASCADE
);

-- Ручная разметка релевантности пары «роль — курс»: 0, 1 или 2.
-- Одна разметка не зависит от метода ранжирования.
CREATE TABLE IF NOT EXISTS eval_labels (
    role_id          TEXT NOT NULL REFERENCES roles(id),
    course_source    TEXT NOT NULL,
    course_source_id TEXT NOT NULL,
    relevance        INTEGER NOT NULL CHECK (relevance BETWEEN 0 AND 2),
    annotator        TEXT,
    labeled_at       TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (role_id, course_source, course_source_id),
    FOREIGN KEY (course_source, course_source_id)
        REFERENCES courses(source, source_id) ON DELETE CASCADE
);

-- Метрики качества по прогонам и методам. k = 0 означает «без отсечения по k».
CREATE TABLE IF NOT EXISTS eval_metrics (
    run_id  TEXT NOT NULL REFERENCES runs(run_id),
    role_id TEXT NOT NULL REFERENCES roles(id),
    method  TEXT NOT NULL,
    metric  TEXT NOT NULL,
    k       INTEGER NOT NULL DEFAULT 0,
    value   REAL NOT NULL,
    PRIMARY KEY (run_id, role_id, method, metric, k)
);

CREATE INDEX IF NOT EXISTS idx_vacancies_role ON vacancies(role_id);
CREATE INDEX IF NOT EXISTS idx_vacancy_skills_skill ON vacancy_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_course_skills_skill ON course_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_role_profiles_role ON role_profiles(role_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_role ON recommendations(role_id, rank);

PRAGMA user_version = 1;
