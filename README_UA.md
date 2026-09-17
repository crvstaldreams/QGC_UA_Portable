# QGroundControl-UA — Windows CI

Цей репозиторій збирає **QGroundControl-UA** у GitHub Actions, без локального Windows-білдера.

## Що саме збирається

- upstream: **QGroundControl v5.0.8**;
- pinned commit: `e0816c957602789200ae5ba0af45217f0f2f1db4`;
- Qt: **6.8.3 / MSVC 2022 x64**;
- GStreamer: **1.22.12**;
- Release build + `--simple-boot-test`;
- NSIS installer і portable ZIP.

Збережені наші зміни: українська мова за замовчуванням, UTF-8 у MAVLink Console, STREAM-TECHNO чорно-жовтий стиль, а також MAVLink Status без автозакриття при кліку поза popup і зі збільшеним шрифтом тільки в цьому status-вікні.

## Перший запуск

1. Створіть новий порожній GitHub-репозиторій, наприклад `QGC-UA-Build`.
2. Завантажте **весь вміст** цього пакета в корінь репозиторію, включно з `.github`.
3. Відкрийте вкладку **Actions**.
4. Якщо GitHub просить дозволити Actions — увімкніть їх для репозиторію.
5. Виберіть workflow **Build QGroundControl UA for Windows**.
6. Натисніть **Run workflow** → **Run workflow**.
7. Після завершення відкрийте запуск і внизу сторінки завантажте artifact **QGroundControl-UA-Windows**.

У ньому будуть:

- `QGroundControl-UA-installer.exe`
- `QGroundControl-UA-portable.zip`
- `SHA256SUMS.txt`
- `build-metadata.txt`

Окремий artifact **QGroundControl-UA-logs** зберігається навіть при падінні workflow і потрібен для діагностики.

## Локальний ПК

На локальному ПК більше не потрібні Qt, Visual Studio, GStreamer, CMake, Ninja або NSIS для збірки. Потрібен лише браузер для GitHub і готовий installer/portable artifact після CI.

## Якщо змінюємо патчі

Пуш змін у `custom/`, `patches/`, `tools/`, `scripts/` або workflow автоматично запускає новий CI build. Одночасно старіший build тієї самої гілки скасовується.

## GitHub-підключення в ChatGPT

Якщо підключити GitHub plugin у ChatGPT, надалі можна буде працювати з репозиторієм/CI без ручного перенесення ZIP між чатами й GitHub. Підключення потребує вашого підтвердження в інтерфейсі ChatGPT.
