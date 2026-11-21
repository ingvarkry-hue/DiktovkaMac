# DiktovkaMac

Русский голосовой ввод в **любое** окно на Mac. Локально, быстро, без облака.
**Russian voice typing into any macOS app. Local, fast, offline.**

[English below](#english)

---

## Русский

Поставили курсор — нажали клавишу — говорите — нажали ещё раз — готовый текст в поле ввода.
Речь распознаёт нейросеть **Whisper** (faster-whisper) прямо на вашем Mac: запись никуда
не отправляется. Пока идёт распознавание, внизу экрана по центру крутится розовый шарик —
видно, что речь преобразуется. Закончил — шарик гаснет, текст на месте.

### Возможности

- Работает в любом приложении: браузер, Telegram, Kimi, Word, почта
- Полностью локальное распознавание — приватность по умолчанию
- Apple Silicon считает на чипе (MPS): секунда речи распознаётся примерно за секунду
- Горячая клавиша на выбор: 英数 / かな на JIS-клавиатурах или любая комбинация с модификаторами
- Лёгкий оверлей-индикатор внизу экрана — не перекрывает поле ввода
- Звуки и автоматическая отправка — по желанию

### Требования

- macOS 13 Ventura или новее
- Apple Silicon (M1–M4) или Intel
- Python 3.10+ (`brew install python3`)
- Интернет нужен только один раз — при установке (модель ~1,6 ГБ)

### Установка

```bash
git clone https://github.com/ingvarkry-hue/DiktovkaMac.git
cd DiktovkaMac
./install.sh
```

Установщик создаст виртуальное окружение, поставит библиотеки, скачает модель,
соберёт `DiktovkaMac.app` и запустит его. Вся установка живёт в одной папке —
систему не трогает.

**Первый запуск — два разрешения:**

1. **Микрофон** — macOS спросит при первой записи, разрешите.
2. **Универсальный доступ** (нужен для вставки текста и горячей клавиши):
   Системные настройки → Конфиденциальность и безопасность → Универсальный доступ →
   включите **python3.x** в списке (программа называется именно так — это нормально).
   Если включали до запуска — выключите и включите снова.

### Как пользоваться

1. Поставьте курсор в поле ввода.
2. Нажмите **英数** (eisu) — внизу экрана появится розовый шарик.
3. Говорите.
4. Нажмите клавишу ещё раз — шарик погаснет, текст окажется в поле ввода.

### Горячая клавиша

По умолчанию — **eisu** (英数, слева от пробела на JIS-клавиатуре). Варианты в `config.json`:

| Значение | Клавиша |
| --- | --- |
| `"eisu"` | 英数, слева от пробела (JIS) |
| `"kana"` | かな, справа от пробела (JIS) |
| `"alt+space"` | Option + Пробел |
| `"cmd+shift+d"` | любая комбинация модификаторов + буква |

F7–F12 на Mac — медиа-клавиши, до программ не доходят, поэтому по умолчанию — eisu/kana
или комбинация с модификаторами.

### Настройки — `config.json`

| Параметр | Что делает |
| --- | --- |
| `hotkey` | клавиша записи |
| `model` | `"large-v3-turbo"` (лучше) или `"small"` (быстрее, чуть хуже качество) |
| `device` | `"auto"` — выберет чип Apple (MPS) или процессор |
| `language` | язык речи, `"ru"` по умолчанию |
| `beep` | `true` — звук при старте и остановке записи |
| `auto_send` | `true` — после вставки сразу нажимать Return |
| `prompt` | подсказка для Whisper (стиль пунктуации) |

После правки: выход через значок 🎙 в меню-баре и `open DiktovkaMac.app` снова.

### Если что-то не так

- **Ничего не происходит по клавише** — проверьте значок 🎙 в меню-баре; нет значка —
  `open DiktovkaMac.app`. Также проверьте «Универсальный доступ».
- **Шарик есть, текста нет** — смотрите `DiktovkaMac.log` в папке программы.
- **Медленно** — поставьте `"model": "small"`.

### Удаление

Удалите папку программы — больше в системе ничего не остаётся.

---

## English

Cursor in — press the hotkey — speak — press again — finished text lands in the input field.
Speech is recognized by the **Whisper** neural network (faster-whisper) right on your Mac:
the recording never leaves the computer. While recognizing, a pink sphere spins at the
bottom-center of the screen, so you can see your speech being converted. When done, the
sphere fades out and the text is in place.

### Features

- Works in any app: browser, Telegram, Word, mail
- Fully local recognition — private by default
- Apple Silicon computes on the MPS chip: ~1 second of speech per second of audio
- Hotkey of your choice: 英数 / かな on JIS keyboards or any modifier combination
- Lightweight overlay indicator at the bottom of the screen — never covers the input field
- Optional sounds and auto-send

### Requirements

- macOS 13 Ventura or later
- Apple Silicon (M1–M4) or Intel
- Python 3.10+ (`brew install python3`)
- Internet needed only once — during install (model ~1.6 GB)

### Installation

```bash
git clone https://github.com/ingvarkry-hue/DiktovkaMac.git
cd DiktovkaMac
./install.sh
```

The installer creates a virtual environment, installs dependencies, downloads the model,
builds `DiktovkaMac.app` and launches it. Everything lives in a single folder —
the system stays untouched.

**First launch — two permissions:**

1. **Microphone** — macOS will ask on first recording; allow it.
2. **Accessibility** (required for text insertion and the hotkey):
   System Settings → Privacy & Security → Accessibility → enable **python3.x**
   (it appears under that name — that's normal). If you enabled it before launch,
   toggle it off and on again.

### Usage

1. Put the cursor into an input field.
2. Press **英数** (eisu) — a pink sphere appears at the bottom of the screen.
3. Speak.
4. Press the key again — the sphere fades out and the text appears in the field.

### Hotkey

Default is **eisu** (英数, left of the spacebar on JIS keyboards). Options in `config.json`:
`"eisu"`, `"kana"`, `"alt+space"`, `"cmd+shift+d"` — any modifier combination works.
F-keys are media keys on Mac and don't reach apps, hence eisu/kana or modifier combos.

### Configuration — `config.json`

| Option | What it does |
| --- | --- |
| `hotkey` | recording hotkey |
| `model` | `"large-v3-turbo"` (best) or `"small"` (faster, slightly worse) |
| `device` | `"auto"` — picks Apple MPS or CPU |
| `language` | speech language, `"ru"` by default |
| `beep` | `true` — sound on start/stop |
| `auto_send` | `true` — press Return after inserting |
| `prompt` | Whisper prompt (punctuation style) |

After editing: quit via the 🎙 menu-bar icon and `open DiktovkaMac.app` again.

### Troubleshooting

- **Hotkey does nothing** — check the 🎙 icon in the menu bar; if missing, run
  `open DiktovkaMac.app`. Also check Accessibility permissions.
- **Sphere shows but no text** — see `DiktovkaMac.log` in the app folder.
- **Slow** — set `"model": "small"`.

### Uninstall

Delete the app folder — nothing else is left in the system.

---

## Лицензия / License

MIT, см. [LICENSE](LICENSE).

Распознавание речи — [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
(модели OpenAI Whisper) / Speech recognition by [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
(OpenAI Whisper models).
