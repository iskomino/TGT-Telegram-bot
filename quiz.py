"""Тест «Какой клуб мне подходит?»: 6 вопросов по 4 варианта, результат считается по сумме баллов клубов.

Тест не хранит состояния: выбранные ответы зашиты в данные кнопки («qz:0132» = первые четыре ответа),
поэтому он не конфликтует с меню, переживает перезапуск бота и «старые» кнопки безопасны.
"""
import html
import re

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import data
import db
from store import get_lang
from texts import t

quiz_router = Router(name="quiz")

# scores: slug клуба -> баллы за этот вариант ответа
QUESTIONS = [
    {
        "q": {
            "az": "Boş vaxtınızda ən çox nə etməyi sevirsiniz?",
            "ru": "Чем вы любите заниматься в свободное время?",
            "en": "What do you like to do in your free time?",
        },
        "options": [
            ({"az": "Kitab oxumaq", "ru": "Читать книги", "en": "Read books"}, {"books": 2, "psychology": 1}),
            ({"az": "Film və ya serial izləmək", "ru": "Смотреть фильмы и сериалы", "en": "Watch films or series"}, {"cinema": 2, "books": 1}),
            ({"az": "Dostlarla intellektual oyunlar", "ru": "Интеллектуальные игры с друзьями", "en": "Play intellectual games with friends"}, {"games": 2, "debate": 1}),
            ({"az": "Başqalarına kömək etmək, məsləhət vermək", "ru": "Помогать другим, давать советы", "en": "Help others and give advice"}, {"mentor": 2, "psychology": 1}),
        ],
    },
    {
        "q": {
            "az": "Komandada adətən sizin rolunuz hansıdır?",
            "ru": "Какая у вас обычно роль в команде?",
            "en": "What is your usual role in a team?",
        },
        "options": [
            ({"az": "İstiqamət verir, kömək edirəm", "ru": "Направляю и помогаю", "en": "I guide and support"}, {"mentor": 2, "debate": 1}),
            ({"az": "Fikrimi arqumentlərlə müdafiə edirəm", "ru": "Отстаиваю мнение аргументами", "en": "I defend my view with arguments"}, {"debate": 2}),
            ({"az": "Dinləyir, insanları anlamağa çalışıram", "ru": "Слушаю и стараюсь понять людей", "en": "I listen and try to understand people"}, {"psychology": 2, "mentor": 1}),
            ({"az": "Strategiya qurur, həll yolu tapıram", "ru": "Выстраиваю стратегию, ищу решения", "en": "I build strategies and find solutions"}, {"games": 2}),
        ],
    },
    {
        "q": {
            "az": "Hansı tədbir sizi daha çox cəlb edir?",
            "ru": "Какое мероприятие вас привлекает больше?",
            "en": "Which event attracts you the most?",
        },
        "options": [
            ({"az": "Debat və canlı müzakirə", "ru": "Дебаты и живая дискуссия", "en": "A debate and lively discussion"}, {"debate": 2}),
            ({"az": "Kitab müzakirəsi", "ru": "Обсуждение книги", "en": "A book discussion"}, {"books": 2}),
            ({"az": "Film nümayişi və müzakirəsi", "ru": "Показ фильма и обсуждение", "en": "A film screening with a discussion"}, {"cinema": 2, "books": 1}),
            ({"az": "Viktorina və komanda yarışı", "ru": "Викторина и командные соревнования", "en": "A quiz and team competition"}, {"games": 2, "debate": 1}),
        ],
    },
    {
        "q": {
            "az": "Sizi ən çox nə motivasiya edir?",
            "ru": "Что вас мотивирует больше всего?",
            "en": "What motivates you the most?",
        },
        "options": [
            ({"az": "Yeni biliklər öyrənmək", "ru": "Узнавать новое", "en": "Learning new things"}, {"books": 1, "games": 1}),
            ({"az": "İnsanlara faydalı olmaq", "ru": "Быть полезным людям", "en": "Being useful to people"}, {"mentor": 2}),
            ({"az": "Özümü və başqalarını anlamaq", "ru": "Понимать себя и других", "en": "Understanding myself and others"}, {"psychology": 2}),
            ({"az": "Vizual və yaradıcı ifadə", "ru": "Визуальное и творческое самовыражение", "en": "Visual and creative expression"}, {"cinema": 2}),
        ],
    },
    {
        "q": {
            "az": "İdeal şənbə axşamınız necədir?",
            "ru": "Каким вы видите идеальный субботний вечер?",
            "en": "What does your ideal Saturday evening look like?",
        },
        "options": [
            ({"az": "Əlimdə kitab, sakit mühit", "ru": "С книгой в тишине", "en": "A book in a quiet place"}, {"books": 2}),
            ({"az": "Dostlarla məntiq və ya stolüstü oyun", "ru": "Логическая или настольная игра с друзьями", "en": "A board or logic game with friends"}, {"games": 2}),
            ({"az": "Film izləyib müzakirə etmək", "ru": "Посмотреть фильм и обсудить", "en": "Watching a film and discussing it"}, {"cinema": 2, "debate": 1}),
            ({"az": "Yeni tələbələrə universiteti tanıtmaq", "ru": "Рассказать новичкам об университете", "en": "Showing newcomers around the university"}, {"mentor": 2}),
        ],
    },
    {
        "q": {
            "az": "Hansı bacarıq sizə daha yaxındır?",
            "ru": "Какой навык вам ближе?",
            "en": "Which skill is closest to you?",
        },
        "options": [
            ({"az": "Natiqlik və inandırma", "ru": "Ораторское мастерство и убеждение", "en": "Public speaking and persuasion"}, {"debate": 2}),
            ({"az": "Empatiya və dinləmək", "ru": "Эмпатия и умение слушать", "en": "Empathy and listening"}, {"psychology": 2, "mentor": 1}),
            ({"az": "Məntiq və strateji düşüncə", "ru": "Логика и стратегическое мышление", "en": "Logic and strategic thinking"}, {"games": 2}),
            ({"az": "Dərin oxu və təhlil", "ru": "Вдумчивое чтение и анализ", "en": "Careful reading and analysis"}, {"books": 2, "cinema": 1}),
        ],
    },
]

_ANSWERS_RE = re.compile(r"^qz:([0-3]{0,6})$")


def rank_clubs(answers: str) -> list[tuple[int, int]]:
    """[(индекс_клуба, баллы)] по убыванию баллов; при равенстве — в порядке списка клубов."""
    totals = {club["slug"]: 0 for club in data.CLUBS}
    for question, choice in zip(QUESTIONS, answers):
        for slug, points in question["options"][int(choice)][1].items():
            totals[slug] += points
    ranking = [(index, totals[club["slug"]]) for index, club in enumerate(data.CLUBS)]
    return sorted(ranking, key=lambda item: (-item[1], item[0]))


def _question_view(lang: str, answers: str) -> tuple[str, InlineKeyboardMarkup]:
    step = len(answers)
    question = QUESTIONS[step]
    text = t(lang, "quiz_question", n=step + 1, total=len(QUESTIONS), question=html.escape(question["q"][lang]))
    rows = [
        [InlineKeyboardButton(text=option[0][lang][:60], callback_data=f"qz:{answers}{i}")]
        for i, option in enumerate(question["options"])
    ]
    rows.append([InlineKeyboardButton(text=t(lang, "btn_back_inline"), callback_data="club:list")])
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def _result_view(lang: str, answers: str) -> tuple[str, InlineKeyboardMarkup, str]:
    ranking = rank_clubs(answers)
    best_index, best_score = ranking[0]
    best = data.CLUBS[best_index]
    near = [data.CLUBS[i]["name"][lang] for i, score in ranking[1:3] if score > 0 and score >= best_score - 1]
    others = t(lang, "quiz_others", clubs=html.escape(", ".join(near))) if near else ""
    from content import get_description  # локальный импорт: модуль зависит от БД, тесту рейтинга он не нужен

    text = t(
        lang,
        "quiz_result",
        emoji=best["emoji"],
        club=html.escape(best["name"][lang]),
        desc=html.escape(get_description(best["slug"], lang)),
        others=others,
    )
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_join"), callback_data=f"join:{best_index}")],
            [InlineKeyboardButton(text=t(lang, "btn_club_info"), callback_data=f"club:{best_index}")],
            [InlineKeyboardButton(text=t(lang, "btn_quiz_again"), callback_data="qz:")],
        ]
    )
    return text, markup, best["slug"]


@quiz_router.callback_query(F.data.regexp(_ANSWERS_RE.pattern))
async def cb_quiz(call: CallbackQuery):
    lang = get_lang(call.from_user.id)
    answers = _ANSWERS_RE.match(call.data or "").group(1)
    await call.answer()
    if len(answers) < len(QUESTIONS):
        text, markup = _question_view(lang, answers)
        if not answers:  # статистика: сколько человек начали тест
            try:
                await db.log_event("quiz")
            except Exception:  # noqa: BLE001
                pass
    else:
        text, markup, slug = _result_view(lang, answers[: len(QUESTIONS)])
        try:  # статистика: какой клуб чаще всего рекомендуется
            await db.log_event(f"quiz.{slug}")
        except Exception:  # noqa: BLE001
            pass
    if isinstance(call.message, Message):
        try:
            await call.message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest:
            pass
