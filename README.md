# Полиграфический калькулятор ИИ
Расчет стоимости цифровой и офсетной печати с помощью smolagents и OpenRouter / Ollama.

## Структура проекта

```
polygraphy_calculator_curs
├─ .env
├─ data
│  ├─ MyPrices.json
│  ├─ MyPrices_full.json
│  └─ paperDigiPrice.json
├─ docs
│  └─ tool_docs
│     ├─ bc7_binding.md
│     ├─ blocknote.md
│     ├─ digital_printing.md
│     ├─ kubarik.md
│     ├─ lamination.md
│     ├─ layout.md
│     └─ offset_printing.md
├─ final_answer.py
├─ Gradio_UI.py
├─ main_or_rag.py
├─ prompts_calc_minimal.yaml
├─ prompts_rag.yaml
├─ rag_retriever.py
├─ README.md
├─ requirements.txt
├─ static
│  ├─ app.js
│  └─ style.css
├─ tools
│  ├─ bc7.py
│  ├─ blocknote.py
│  ├─ control_digital.py
│  ├─ control_offset.py
│  ├─ kubarik.py
│  ├─ lamination
│  │  ├─ calculator.py
│  │  ├─ validator.py
│  │  ├─ __init__.py
│  │  └─ __pycache__
│  │     ├─ calculator.cpython-314.pyc
│  │     ├─ prices.cpython-314.pyc
│  │     ├─ validator.cpython-314.pyc
│  │     └─ __init__.cpython-314.pyc
│  ├─ output
│  │  ├─ bc7_2026-04-08_15-03-19_Чистякова.pdf
│  │  ├─ bc7_2026-04-09_15-52-46_Чистякова.pdf
│  │  ├─ bc7_2026-04-28_15-21-53_unknown.pdf
│  │  └─ bc7_2026-04-28_15-22-15_unknown.pdf
│  ├─ prices.py
│  ├─ tools_agent.py
│  ├─ __init__.py
│  └─ __pycache__
│     ├─ bc7.cpython-314.pyc
│     ├─ blocknote.cpython-314.pyc
│     ├─ control_digital.cpython-314.pyc
│     ├─ control_offset.cpython-314.pyc
│     ├─ kubarik.cpython-314.pyc
│     ├─ prices.cpython-314.pyc
│     ├─ tools_agent.cpython-314.pyc
│     └─ __init__.cpython-314.pyc
└─ __pycache__
   ├─ final_answer.cpython-314.pyc
   ├─ Gradio_UI.cpython-314.pyc
   ├─ main.cpython-314.pyc
   ├─ main_3-4b.cpython-314.pyc
   ├─ main_or.cpython-314.pyc
   └─ rag_retriever.cpython-314.pyc

```

## Установка

### 1. Требования
- Python 3.10+
- Рекомендуется виртуальное окружение

### 2. Установите зависимости

```bash
pip install -r requirements.txt
```

### 3. Подготовьте окружение

Создайте файл `.env` в корне проекта:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
```

> Если вы хотите использовать `main.py`, тогда вместо OpenRouter потребуется локальный Ollama-сервер и `OLLAMA_API_BASE=http://localhost:11434`.

### 4. Запустите приложение

```bash
python main_or.py
```

Откройте в браузере: **http://localhost:5000**

## Что работает
- цифровая печать
- офсетная печать
- сравнение типов печати
- расчет ламинации
- расчет блокнотов
- расчет кубарик
- расчет переплета BC7

## Примеры запросов

### Цифровая печать
> цифровая печать 4+0, бумага 3р./лист, 100 листов А4

### Офсетная печать
> офсет 1000 листов А5 ч/б, бумага 2.5р/лист

### Сравнение
> сравни цифру и офсет для 500 листов А4 полноцвет, бумага 2р

### Двусторонняя печать
> цифровая двусторонняя 4+4, 200 листов А5, бумага 2р

## Коды цветности

### Цифровая печать
- `10` — ч/б 1-сторонняя (1+0)
- `11` — ч/б 2-сторонняя (1+1)
- `40` — полноцвет 1-сторонняя (4+0)
- `44` — полноцвет 2-сторонняя (4+4)
- `41` — смешанная (4+1)

### Офсетная печать
- `10` — ч/б 1-сторонняя (1+0)
- `11` — ч/б 2-сторонняя (1+1)
- `20` — 2 краски 1-сторонняя
- `22` — 2 краски 2-сторонняя
- `21` — смешанная (2+1)

## Форматы
- А3, А4, А5, А6

## Структура инструментов agentов

Все `@tool` функции импортируются из `tools/tools_agent.py`:

- `calculate_layout` — расчет макета
- `calculate_digital_printing` — расчет цифровой печати
- `calculate_offset_printing` — расчет офсетной печати
- `calculate_lamination` — расчет ламинации
- `calculate_blocknote` — расчет блокнотов
- `calculate_kubarik` — расчет кубарик
- `calculate_bc7_binding` — расчет переплета BC7
- `FinalAnswerTool` — форматирование итогового ответа

## Устранение неполадок

### Не запускается `main_or.py`
- Проверьте, что `OPENROUTER_API_KEY` указан в `.env`
- Убедитесь, что зависимости установлены: `pip install -r requirements.txt`

### Проблемы с импортами
- В каталоге `tools/` должен быть файл `__init__.py`
- Проверьте, что вы запускаете скрипт из корня проекта

## Лицензия
MIT

