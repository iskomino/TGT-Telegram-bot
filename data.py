"""Исходные данные TGT-бота. Всё здесь — значения «по умолчанию»; в работе их правит админ через /admin."""

UNIVERSITY_ADDRESS = "Gəncə ş. AZ2011 Şah İsmayıl Xətai prospekti 103"
UNIVERSITY_LAT = 40.68856853905134
UNIVERSITY_LON = 46.38421577501259

# Комната TGT (в админке меняется: «TGT məlumatı» → «Otaq»)
DEFAULT_ROOM = "2318"

TGT_ABOUT = {
    "az": "TGT tələbələrin könüllülük əsasında birləşdiyi ictimai təşkilatdır. Məqsədi tələbələrin hüquq və maraqlarını qorumaq, onların bacarıq və yaradıcılıq potensialını üzə çıxarmaq, mədəni, intellektual və ictimai tədbirlər təşkil etməkdir. TGT nəzdində maraq klubları fəaliyyət göstərir.",
    "ru": "TGT — общественная организация, объединяющая студентов на добровольной основе. Её цель — защищать права и интересы студентов, раскрывать их знания и творческий потенциал, организовывать культурные, интеллектуальные и общественные мероприятия. При TGT действуют клубы по интересам.",
    "en": "TGT is a public organization that unites students on a voluntary basis. Its aim is to protect students' rights and interests, reveal their skills and creative potential, and organize cultural, intellectual and public events. Interest clubs operate under TGT.",
}

# Клубы. Описания — черновые, общие: их можно заменить в админке («Klublar» → клуб → «Təsviri dəyiş»).
CLUBS = [
    {
        "slug": "mentor",
        "emoji": "🧭",
        "name": {"az": "Mentor klubu", "ru": "Клуб менторства", "en": "Mentor Club"},
        "desc": {
            "az": "Təcrübəli tələbələr yeni tələbələrə universitet həyatına uyğunlaşmaqda, təhsildə və karyera seçimində dəstək olur.",
            "ru": "Опытные студенты помогают новичкам освоиться в университете, а также советом в учёбе и выборе карьеры.",
            "en": "Experienced students help newcomers settle into university life and support them in their studies and career choices.",
        },
    },
    {
        "slug": "debate",
        "emoji": "🎤",
        "name": {"az": "Debat klubu", "ru": "Дебатный клуб", "en": "Debate Club"},
        "desc": {
            "az": "Natiqlik, tənqidi təfəkkür və arqumentasiya bacarıqlarını inkişaf etdirən müzakirə və debat görüşləri.",
            "ru": "Встречи-дискуссии и дебаты, развивающие ораторское мастерство, критическое мышление и умение аргументировать.",
            "en": "Discussion and debate meetings that develop public speaking, critical thinking and argumentation skills.",
        },
    },
    {
        "slug": "psychology",
        "emoji": "🧠",
        "name": {"az": "Psixologiya klubu", "ru": "Клуб психологии", "en": "Psychology Club"},
        "desc": {
            "az": "Psixologiya mövzularında təlimlər, müzakirələr və özünüinkişaf görüşləri.",
            "ru": "Тренинги, обсуждения и встречи по самопознанию и психологии.",
            "en": "Trainings, discussions and self-development meetings on psychology topics.",
        },
    },
    {
        "slug": "games",
        "emoji": "♟️",
        "name": {"az": "İntellektual oyunlar klubu", "ru": "Клуб интеллектуальных игр", "en": "Intellectual Games Club"},
        "desc": {
            "az": "Məntiq və intellektual oyunlar, viktorinalar və komanda yarışları.",
            "ru": "Логические и интеллектуальные игры, викторины и командные соревнования.",
            "en": "Logic and intellectual games, quizzes and team competitions.",
        },
    },
    {
        "slug": "books",
        "emoji": "📚",
        "name": {"az": "Kitab klubu", "ru": "Книжный клуб", "en": "Book Club"},
        "desc": {
            "az": "Kitab oxu və müzakirə görüşləri, tövsiyələr və ədəbi söhbətlər.",
            "ru": "Встречи для чтения и обсуждения книг, рекомендации и литературные беседы.",
            "en": "Reading and book-discussion meetings, recommendations and literary conversations.",
        },
    },
    {
        "slug": "cinema",
        "emoji": "🎬",
        "name": {"az": "Kino klubu", "ru": "Киноклуб", "en": "Cinema Club"},
        "desc": {
            "az": "Film nümayişləri, müzakirələr və kino mədəniyyəti üzrə görüşlər.",
            "ru": "Показы фильмов, обсуждения и встречи о кинокультуре.",
            "en": "Film screenings, discussions and meetings about cinema culture.",
        },
    },
]

# TGT İdarə Heyəti (Правление): 7 мест. Место 0 — руководитель, остальные 6 свободны и заполняются админом.
TEAM_SLOTS = 7

# V.M.İ.E. = «vəzifəni müvəqqəti icra edən» (временно исполняющий обязанности)
HEAD_ROLE = "TGT İdarə Heyətinin V.M.İ.E. Sədri"

# Должности, для которых бот показывает перевод на русский и английский (в азербайджанской версии — как есть).
# Любая другая должность, введённая админом, показывается без изменений.
ROLE_TRANSLATIONS = {
    HEAD_ROLE: {"ru": "И.о. председателя Правления TGT", "en": "Acting Chair of the TGT Management Board"},
    "TGT İdarə Heyətinin Sədri": {"ru": "Председатель Правления TGT", "en": "Chair of the TGT Management Board"},
    "TGT İdarə Heyətinin üzvü": {"ru": "Член Правления TGT", "en": "TGT Management Board member"},
}

# Прежнее значение должности руководителя: при запуске заменяется на HEAD_ROLE
LEGACY_HEAD_ROLES = {"TGT Sədri"}

CLUB_FIELDS = ("first_name", "last_name", "phone")
TEAM_FIELDS = ("role", "first_name", "last_name", "patronymic", "phone", "email")
EMPTY_PERSON = {field: "" for field in TEAM_FIELDS}

# Значения по умолчанию. Для сədrов и müavin клубов данных пока нет: они «не назначены», админ заполняет их сам.
DEFAULT_PEOPLE = {
    "t.0": {
        "role": HEAD_ROLE,
        "first_name": "Nazim",
        "last_name": "Huseynov",
        "patronymic": "",
        "phone": "+994 55 766 73 78",
        "email": "",
    },
}


# ---------- FAQ (часто задаваемые вопросы) ----------
# Азербайджанские тексты — ровно те, что предоставил заказчик (кроме вопроса №4: в присланном тексте его не было,
# формулировка «TGT hansı tədbirləri təşkil edir?» подобрана по смыслу ответа). Переводы на ru/en — черновые.
# При первом запуске эти вопросы записываются в базу, дальше их правит админ (/admin → FAQ).
DEFAULT_FAQ = [
    {
        "q": {
            "az": "Tələbə Gənclər Təşkilatı (TGT) nədir?",
            "ru": "Что такое Студенческая молодёжная организация (TGT)?",
            "en": "What is the Student Youth Organization (TGT)?",
        },
        "a": {
            "az": "Tələbə Gənclər Təşkilatı tələbələrin ictimai fəallığının artırılması, şəxsi inkişafının dəstəklənməsi, liderlik bacarıqlarının formalaşdırılması və tələbə həyatının daha maraqlı təşkili istiqamətində fəaliyyət göstərən tələbə təşkilatıdır.",
            "ru": "Студенческая молодёжная организация — это студенческая организация, которая работает над повышением общественной активности студентов, поддержкой их личностного развития, формированием лидерских качеств и более интересной организацией студенческой жизни.",
            "en": "The Student Youth Organization is a student organization that works to increase students' public activity, support their personal development, build leadership skills and make student life more interesting.",
        },
    },
    {
        "q": {
            "az": "TGT-yə necə üzv ola bilərəm?",
            "ru": "Как вступить в TGT?",
            "en": "How can I become a member of TGT?",
        },
        "a": {
            "az": "TGT-yə üzv olmaq üçün təşkilatın rəhbərliyi ilə əlaqə saxlaya və ya təşkilatın elan etdiyi qeydiyyat forması vasitəsilə müraciət edə bilərsiniz. Üzvlük və qeydiyyat qaydaları barədə ətraflı məlumat təşkilat tərəfindən təqdim olunur.",
            "ru": "Чтобы вступить в TGT, вы можете связаться с руководством организации или подать заявку через регистрационную форму, которую объявляет организация. Подробную информацию о правилах членства и регистрации предоставляет сама организация.",
            "en": "To become a member of TGT, you can contact the organization's leadership or apply through the registration form announced by the organization. Detailed information on membership and registration rules is provided by the organization.",
        },
    },
    {
        "q": {
            "az": "TGT-yə üzvlük ödənişlidirmi?",
            "ru": "Платное ли членство в TGT?",
            "en": "Is TGT membership paid?",
        },
        "a": {
            "az": "TGT-yə üzvlük qaydaları təşkilatın müəyyən etdiyi şərtlərə uyğun tənzimlənir. Üzvlük haqqının olub-olmaması barədə dəqiq məlumatı təşkilatın rəhbərliyindən əldə edə bilərsiniz.",
            "ru": "Правила членства в TGT регулируются условиями, установленными организацией. Точную информацию о том, есть ли членский взнос, можно получить у руководства организации.",
            "en": "TGT membership rules are governed by the conditions set by the organization. For exact information on whether there is a membership fee, contact the organization's leadership.",
        },
    },
    {
        "q": {
            "az": "TGT hansı tədbirləri təşkil edir?",
            "ru": "Какие мероприятия организует TGT?",
            "en": "What events does TGT organize?",
        },
        "a": {
            "az": "TGT tərəfindən təlimlər, seminarlar, görüşlər, intellektual oyunlar, idman yarışları, sosial layihələr, könüllülük fəaliyyətləri və digər tələbəyönümlü tədbirlər təşkil oluna bilər. Qarşıdan gələn tədbirlər haqqında elanları izləməklə məlumat əldə edə bilərsiniz.",
            "ru": "TGT может организовывать тренинги, семинары, встречи, интеллектуальные игры, спортивные соревнования, социальные проекты, волонтёрскую деятельность и другие мероприятия для студентов. Узнавать о предстоящих мероприятиях можно, следя за объявлениями.",
            "en": "TGT may organize trainings, seminars, meetings, intellectual games, sports competitions, social projects, volunteering activities and other student-oriented events. You can learn about upcoming events by following the announcements.",
        },
    },
    {
        "q": {
            "az": "TGT tədbirlərində necə iştirak edə bilərəm?",
            "ru": "Как принять участие в мероприятиях TGT?",
            "en": "How can I take part in TGT events?",
        },
        "a": {
            "az": "Tədbirlərdə iştirak etmək üçün TGT-nin rəsmi elanlarını izləmək və tələb olunduğu halda qeydiyyatdan keçmək lazımdır. Tədbirin tarixi, yeri və iştirak şərtləri elanlarda qeyd olunur.",
            "ru": "Чтобы участвовать в мероприятиях, нужно следить за официальными объявлениями TGT и при необходимости зарегистрироваться. Дата, место и условия участия указываются в объявлениях.",
            "en": "To take part in events, follow TGT's official announcements and register when required. The date, place and participation conditions are given in the announcements.",
        },
    },
    {
        "q": {
            "az": "TGT-də könüllü kimi fəaliyyət göstərə bilərəmmi?",
            "ru": "Могу ли я работать в TGT волонтёром?",
            "en": "Can I volunteer at TGT?",
        },
        "a": {
            "az": "Bəli, təşkilatın fəaliyyət istiqamətlərinə uyğun olaraq könüllülər müxtəlif tədbirlərin təşkili, iştirakçıların koordinasiyası, kommunikasiya və layihələrin həyata keçirilməsi prosesində iştirak edə bilərlər. Bunun üçün təşkilata müraciət edə bilərsiniz.",
            "ru": "Да, в соответствии с направлениями деятельности организации волонтёры могут участвовать в организации различных мероприятий, координации участников, коммуникации и реализации проектов. Для этого можно обратиться в организацию.",
            "en": "Yes. In line with the organization's areas of activity, volunteers can take part in organizing various events, coordinating participants, communication and carrying out projects. You can contact the organization to do so.",
        },
    },
    {
        "q": {
            "az": "TGT-də hansı klublar və fəaliyyət istiqamətləri mövcuddur?",
            "ru": "Какие клубы и направления деятельности есть в TGT?",
            "en": "What clubs and areas of activity exist in TGT?",
        },
        "a": {
            "az": "TGT çərçivəsində yaradıcılıq, musiqi, idman, intellektual inkişaf, sosial layihələr və digər istiqamətlər üzrə klub və fəaliyyətlər təşkil oluna bilər. Mövcud klublar haqqında ətraflı məlumatı təşkilatdan əldə edə bilərsiniz.",
            "ru": "В рамках TGT могут организовываться клубы и деятельность по творчеству, музыке, спорту, интеллектуальному развитию, социальным проектам и другим направлениям. Подробную информацию о действующих клубах можно получить в организации.",
            "en": "Within TGT, clubs and activities may be organized in creativity, music, sports, intellectual development, social projects and other areas. You can get detailed information about the existing clubs from the organization.",
        },
    },
    {
        "q": {
            "az": "TGT-yə üzv olmaq üçün hansı sənədlər tələb olunur?",
            "ru": "Какие документы нужны для вступления в TGT?",
            "en": "What documents are required to join TGT?",
        },
        "a": {
            "az": "Üzvlük üçün tələb olunan sənədlər və məlumatlar qeydiyyat qaydalarından asılıdır. Adətən tələbə haqqında əsas məlumatlar və əlaqə vasitələri tələb oluna bilər. Dəqiq siyahı üçün təşkilatın elanlarını izləməyiniz tövsiyə olunur.",
            "ru": "Необходимые для членства документы и сведения зависят от правил регистрации. Обычно могут запрашиваться основные сведения о студенте и контактные данные. Для точного списка рекомендуется следить за объявлениями организации.",
            "en": "The documents and information required for membership depend on the registration rules. Basic information about the student and contact details may usually be requested. For the exact list, we recommend following the organization's announcements.",
        },
    },
    {
        "q": {
            "az": "TGT ilə necə əlaqə saxlaya bilərəm?",
            "ru": "Как связаться с TGT?",
            "en": "How can I contact TGT?",
        },
        "a": {
            "az": "TGT ilə əlaqə saxlamaq üçün təşkilatın rəsmi sosial media hesablarından, əlaqə nömrəsindən və ya universitetdə fəaliyyət göstərən nümayəndələrindən istifadə edə bilərsiniz. Müraciətinizin mövzusunu qeyd etməyiniz daha operativ cavab almağınıza kömək edəcək.",
            "ru": "Чтобы связаться с TGT, можно воспользоваться официальными аккаунтами организации в социальных сетях, контактным номером или её представителями в университете. Если указать тему обращения, вы быстрее получите ответ.",
            "en": "To contact TGT, you can use the organization's official social media accounts, its contact number or its representatives at the university. Stating the subject of your message will help you get a faster reply.",
        },
    },
]

