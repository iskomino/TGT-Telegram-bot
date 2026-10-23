"""Тексты бота на трёх языках. Чтобы изменить текст, правится только этот файл."""
from store import DEFAULT_LANG

LANGS = {"az": "🇦🇿 Azərbaycanca", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}

_CHOOSE = "🌐 Dil seçin / Выберите язык / Choose language"

T: dict[str, dict[str, str]] = {
    "az": {
        "choose_lang": _CHOOSE,
        "welcome": "👋 Salam! Mən <b>Azərbaycan Texnologiya Universitetinin Tələbə Gənclər Təşkilatının (TGT)</b> məlumat botuyam.\n\nAşağıdakı menyudan bölmə seçin.",
        "menu_title": "📋 Əsas menyu",
        "btn_clubs": "🎭 Klublar",
        "btn_about": "ℹ️ TGT haqqında",
        "btn_board": "🏛 TGT İdarə Heyəti",
        "board_header": "🏛 <b>TGT İdarə Heyəti</b>\nAzərbaycan Texnologiya Universiteti",
        "board_empty": "Məlumat tezliklə əlavə olunacaq.",
        "btn_lang": "🌐 Dil",
        "btn_back_inline": "⬅️ Geri",
        "clubs_title": "🎭 <b>TGT klubları</b>\n\nKlubu seçin:",
        "role_chair": "Sədr",
        "role_deputy": "Sədr müavini",
        "role_member": "İdarə Heyəti üzvü",
        "vacant": "təyin edilməyib",
        "about_header": "ℹ️ <b>Tələbə Gənclər Təşkilatı (TGT)</b>\nAzərbaycan Texnologiya Universiteti",
        "room_line": "🚪 TGT otağı: {room}",
        "address_line": "📍 {address}",
        "help": "ℹ️ <b>Kömək</b>\n\n🎭 «Klublar» bölməsində TGT-nin bütün klublarını, onların sədrlərini və əlaqə məlumatlarını görə bilərsiniz.\n🏛 «TGT İdarə Heyəti» bölməsində İdarə Heyətinin üzvləri və əlaqə məlumatları göstərilir.\nℹ️ «TGT haqqında» bölməsində təşkilat, rəhbər, otaq və ünvan göstərilir.\n\n<b>Əmrlər</b>\n/start — başlamaq\n/menu — əsas menyu\n/help — kömək\n/cancel — cari əməliyyatı ləğv etmək",
        "throttled": "⏳ Çox tez-tez sorğu göndərirsiniz. Zəhmət olmasa bir neçə saniyə gözləyin.",
        "unknown": "Zəhmət olmasa menyudan bölmə seçin 👇",
        "cancelled": "Əməliyyat ləğv edildi.",
    },
    "ru": {
        "choose_lang": _CHOOSE,
        "welcome": "👋 Здравствуйте! Я информационный бот <b>Студенческой молодёжной организации (TGT) Азербайджанского технологического университета</b>.\n\nВыберите раздел в меню ниже.",
        "menu_title": "📋 Главное меню",
        "btn_clubs": "🎭 Клубы",
        "btn_about": "ℹ️ О TGT",
        "btn_board": "🏛 Правление TGT",
        "board_header": "🏛 <b>Правление TGT</b>\nАзербайджанский технологический университет",
        "board_empty": "Информация скоро появится.",
        "btn_lang": "🌐 Язык",
        "btn_back_inline": "⬅️ Назад",
        "clubs_title": "🎭 <b>Клубы TGT</b>\n\nВыберите клуб:",
        "role_chair": "Председатель",
        "role_deputy": "Заместитель председателя",
        "role_member": "Член Правления",
        "vacant": "не назначен",
        "about_header": "ℹ️ <b>Студенческая молодёжная организация (TGT)</b>\nАзербайджанский технологический университет",
        "room_line": "🚪 Комната TGT: {room}",
        "address_line": "📍 {address}",
        "help": "ℹ️ <b>Помощь</b>\n\n🎭 В разделе «Клубы» вы увидите все клубы TGT, их председателей и контакты.\n🏛 В разделе «Правление TGT» указаны члены Правления и их контакты.\nℹ️ В разделе «О TGT» указаны организация, руководитель, комната и адрес.\n\n<b>Команды</b>\n/start — начать\n/menu — главное меню\n/help — помощь\n/cancel — отменить текущее действие",
        "throttled": "⏳ Слишком много запросов. Пожалуйста, подождите несколько секунд.",
        "unknown": "Пожалуйста, выберите раздел в меню 👇",
        "cancelled": "Действие отменено.",
    },
    "en": {
        "choose_lang": _CHOOSE,
        "welcome": "👋 Hello! I am the information bot of the <b>Student Youth Organization (TGT) of Azerbaijan Technology University</b>.\n\nChoose a section from the menu below.",
        "menu_title": "📋 Main menu",
        "btn_clubs": "🎭 Clubs",
        "btn_about": "ℹ️ About TGT",
        "btn_board": "🏛 TGT Board",
        "board_header": "🏛 <b>TGT Management Board</b>\nAzerbaijan Technology University",
        "board_empty": "Information will be added soon.",
        "btn_lang": "🌐 Language",
        "btn_back_inline": "⬅️ Back",
        "clubs_title": "🎭 <b>TGT clubs</b>\n\nChoose a club:",
        "role_chair": "Chair",
        "role_deputy": "Deputy chair",
        "role_member": "Board member",
        "vacant": "not assigned",
        "about_header": "ℹ️ <b>Student Youth Organization (TGT)</b>\nAzerbaijan Technology University",
        "room_line": "🚪 TGT room: {room}",
        "address_line": "📍 {address}",
        "help": "ℹ️ <b>Help</b>\n\n🎭 In the «Clubs» section you can see all TGT clubs, their chairs and contacts.\n🏛 The «TGT Board» section shows the members of the Management Board and their contacts.\nℹ️ The «About TGT» section shows the organization, its head, the room and the address.\n\n<b>Commands</b>\n/start — start\n/menu — main menu\n/help — help\n/cancel — cancel the current action",
        "throttled": "⏳ Too many requests. Please wait a few seconds.",
        "unknown": "Please choose a section from the menu 👇",
        "cancelled": "Cancelled.",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    text = T.get(lang, T[DEFAULT_LANG]).get(key) or T[DEFAULT_LANG][key]
    return text.format(**kwargs) if kwargs else text


# ---------- Заявки в клубы, мероприятия, обращения ----------

_EXTRA3 = {
    "az": {
        "help": "ℹ️ <b>Kömək</b>\n\n🎭 «Klublar»: TGT klubları, onların sədrləri, əlaqə məlumatları və klubа qoşulmaq üçün müraciət.\n📅 «Tədbirlər»: yaxınlaşan tədbirlər və qeydiyyat (bir gün əvvəl xatırlatma göndərilir).\n🏛 «TGT İdarə Heyəti»: İdarə Heyətinin üzvləri.\nℹ️ «TGT haqqında»: təşkilat, rəhbər, otaq və ünvan.\n✉️ «Müraciət»: təklif, şikayət və ya sual göndərin (istəsəniz anonim).\n\n<b>Əmrlər</b>\n/start — başlamaq\n/menu — əsas menyu\n/help — kömək\n/cancel — cari əməliyyatı ləğv etmək",
        "btn_events": "📅 Tədbirlər",
        "btn_feedback": "✉️ Müraciət",
        "btn_join": "📝 Qoşul",
        "btn_register": "✅ Qeydiyyatdan keç",
        "btn_unregister": "❌ Qeydiyyatı ləğv et",
        "btn_cancel_inline": "❌ Ləğv et",
        "btn_send": "✅ Göndər",
        "btn_anon": "🕶 Anonim",
        "btn_named": "👤 Adımla",
        "btn_open_event": "📅 Ətraflı",
        "kind_s": "💡 Təklif",
        "kind_c": "❗ Şikayət",
        "kind_q": "❓ Sual",
        "join_intro": "📝 <b>«{club}» klubuna müraciət</b>\n\nMəlumatlarınız yalnız TGT adminlərinə və klub rəhbərliyinə göstəriləcək. Şəxsi məlumatlarınızı (şifrə, FİN) yazmayın.\n\nAd və soyadınızı yazın:",
        "join_ask_faculty": "Fakültə və kurs/qrupunuzu yazın (məsələn: Rəqəmsal texnologiyalar, 2-ci kurs):",
        "join_ask_phone": "Əlaqə üçün telefon nömrəniz (məcburi deyil). Nümunə: +994 55 123 45 67\nKeçmək üçün «-» göndərin.",
        "join_confirm": "📝 <b>Müraciətinizi yoxlayın</b>\n\n🎭 {club}\n👤 {name}\n🏛 {faculty}\n☎️ {phone}\n\nGöndərilsin?",
        "join_done": "✅ Müraciətiniz qəbul olundu (№{id}). Klub rəhbərliyi tezliklə sizinlə əlaqə saxlayacaq.",
        "join_duplicate": "Bu klub üçün müraciətiniz artıq nəzərdən keçirilir.",
        "join_limit": "Eyni anda ən çox 5 açıq müraciətiniz ola bilər. Cavabı gözləyin.",
        "err_join_name": "Ad və soyad 2–60 simvol olmalıdır.",
        "err_join_faculty": "Fakültə və kurs 2–80 simvol olmalıdır.",
        "err_join_phone": "Nömrəni belə yazın: +994 55 123 45 67 (və ya «-»).",
        "app_accepted": "🎉 «{club}» klubuna müraciətiniz qəbul edildi! Klub rəhbərliyi sizinlə əlaqə saxlayacaq.",
        "app_declined": "«{club}» klubuna müraciətiniz bu dəfə təsdiqlənmədi. Digər klublara qoşula bilərsiniz.",
        "events_title": "📅 <b>Yaxınlaşan tədbirlər</b>\n\nƏtraflı məlumat və qeydiyyat üçün tədbiri seçin:",
        "events_empty": "📅 Hələlik planlaşdırılmış tədbir yoxdur. Yeniliklər üçün botu izləyin!",
        "ev_registered": "👥 Qeydiyyatdan keçən: {count}",
        "ev_registered_cap": "👥 Qeydiyyatdan keçən: {count}/{capacity}",
        "reg_ok": "✅ Qeydiyyatdan keçdiniz! Tədbirdən bir gün əvvəl xatırlatma göndərəcəyəm.\n(Adınız və istifadəçi adınız təşkilatçılara göstərilir.)",
        "reg_already": "Siz artıq qeydiyyatdan keçmisiniz.",
        "reg_full": "⚠️ Təəssüf ki, bütün yerlər dolub.",
        "reg_closed": "Bu tədbir artıq başlayıb və ya bitib.",
        "unreg_ok": "Qeydiyyatınız ləğv edildi.",
        "ev_missing": "Bu tədbir artıq mövcud deyil.",
        "event_reminder": "⏰ <b>Xatırlatma:</b> tədbirə 24 saatdan az qalıb!\n\n{card}",
        "event_changed": "ℹ️ <b>Tədbirin məlumatları dəyişdi</b>\n\n{card}",
        "event_cancelled": "❌ <b>Tədbir ləğv edildi:</b> {title}",
        "event_announce": "📣 <b>Yeni tədbir!</b>\n\n{card}",
        "fb_intro": "✉️ <b>TGT-yə müraciət</b>\n\nTəklif, şikayət və ya sualınızı göndərə bilərsiniz. Növü seçin:",
        "fb_ask_anon": "Adınız (Telegram profil adınız) adminlərə göstərilsin?\n\n🕶 Anonim göndərsəniz, adınız adminlərə göstərilməyəcək, amma cavabı yenə də bu botda ala biləcəksiniz.",
        "fb_ask_text": "✍️ Mətni yazın (10–1000 simvol). Şəxsi məlumatlarınızı (şifrə, FİN) yazmayın.",
        "fb_done": "✅ Müraciətiniz göndərildi (№{id}). Cavab bu botda gələcək.",
        "fb_limit": "Eyni anda ən çox 3 açıq müraciətiniz ola bilər. Cavabı gözləyin.",
        "fb_cooldown": "⏳ Yeni müraciət üçün bir az gözləyin.",
        "fb_muted": "Müraciət göndərmək müvəqqəti məhdudlaşdırılıb.",
        "err_fb_text": "Mətn 10–1000 simvol olmalıdır.",
        "fb_reply": "💬 <b>TGT cavabı</b> (müraciət №{id})\n\n{reply}",
        "only_text": "Zəhmət olmasa mətn göndərin.",
    },
    "ru": {
        "help": "ℹ️ <b>Помощь</b>\n\n🎭 «Клубы»: клубы TGT, их председатели, контакты и заявка на вступление.\n📅 «Мероприятия»: ближайшие события и запись (за сутки приходит напоминание).\n🏛 «Правление TGT»: члены Правления.\nℹ️ «О TGT»: организация, руководитель, комната и адрес.\n✉️ «Обращение»: отправьте предложение, жалобу или вопрос (можно анонимно).\n\n<b>Команды</b>\n/start — начать\n/menu — главное меню\n/help — помощь\n/cancel — отменить текущее действие",
        "btn_events": "📅 Мероприятия",
        "btn_feedback": "✉️ Обращение",
        "btn_join": "📝 Вступить",
        "btn_register": "✅ Записаться",
        "btn_unregister": "❌ Отменить запись",
        "btn_cancel_inline": "❌ Отмена",
        "btn_send": "✅ Отправить",
        "btn_anon": "🕶 Анонимно",
        "btn_named": "👤 От моего имени",
        "btn_open_event": "📅 Подробнее",
        "kind_s": "💡 Предложение",
        "kind_c": "❗ Жалоба",
        "kind_q": "❓ Вопрос",
        "join_intro": "📝 <b>Заявка в клуб «{club}»</b>\n\nВаши данные увидят только администраторы TGT и руководство клуба. Не указывайте личные данные (пароли, FİN).\n\nНапишите ваши имя и фамилию:",
        "join_ask_faculty": "Напишите ваш факультет и курс/группу (например: Цифровые технологии, 2 курс):",
        "join_ask_phone": "Телефон для связи (необязательно). Пример: +994 55 123 45 67\nЧтобы пропустить, отправьте «-».",
        "join_confirm": "📝 <b>Проверьте заявку</b>\n\n🎭 {club}\n👤 {name}\n🏛 {faculty}\n☎️ {phone}\n\nОтправить?",
        "join_done": "✅ Заявка принята (№{id}). Руководство клуба скоро свяжется с вами.",
        "join_duplicate": "Ваша заявка в этот клуб уже рассматривается.",
        "join_limit": "Одновременно может быть не более 5 открытых заявок. Дождитесь ответа.",
        "err_join_name": "Имя и фамилия: от 2 до 60 символов.",
        "err_join_faculty": "Факультет и курс: от 2 до 80 символов.",
        "err_join_phone": "Введите номер так: +994 55 123 45 67 (или «-»).",
        "app_accepted": "🎉 Ваша заявка в клуб «{club}» принята! Руководство клуба свяжется с вами.",
        "app_declined": "Ваша заявка в клуб «{club}» в этот раз не одобрена. Вы можете присоединиться к другим клубам.",
        "events_title": "📅 <b>Ближайшие мероприятия</b>\n\nВыберите мероприятие для подробностей и записи:",
        "events_empty": "📅 Пока нет запланированных мероприятий. Следите за обновлениями!",
        "ev_registered": "👥 Записались: {count}",
        "ev_registered_cap": "👥 Записались: {count}/{capacity}",
        "reg_ok": "✅ Вы записаны! За сутки до начала я пришлю напоминание.\n(Ваше имя и username видны организаторам.)",
        "reg_already": "Вы уже записаны.",
        "reg_full": "⚠️ К сожалению, все места заняты.",
        "reg_closed": "Это мероприятие уже началось или прошло.",
        "unreg_ok": "Запись отменена.",
        "ev_missing": "Это мероприятие больше не существует.",
        "event_reminder": "⏰ <b>Напоминание:</b> до мероприятия меньше суток!\n\n{card}",
        "event_changed": "ℹ️ <b>Данные мероприятия изменились</b>\n\n{card}",
        "event_cancelled": "❌ <b>Мероприятие отменено:</b> {title}",
        "event_announce": "📣 <b>Новое мероприятие!</b>\n\n{card}",
        "fb_intro": "✉️ <b>Обращение в TGT</b>\n\nВы можете отправить предложение, жалобу или вопрос. Выберите тип:",
        "fb_ask_anon": "Показать ваше имя (имя в профиле Telegram) администраторам?\n\n🕶 При отправке анонимно ваше имя администраторам показано не будет, но ответ вы всё равно получите в этом боте.",
        "fb_ask_text": "✍️ Напишите текст (10–1000 символов). Не указывайте личные данные (пароли, FİN).",
        "fb_done": "✅ Обращение отправлено (№{id}). Ответ придёт в этом боте.",
        "fb_limit": "Одновременно может быть не более 3 открытых обращений. Дождитесь ответа.",
        "fb_cooldown": "⏳ Подождите немного перед новым обращением.",
        "fb_muted": "Отправка обращений временно ограничена.",
        "err_fb_text": "Текст должен быть от 10 до 1000 символов.",
        "fb_reply": "💬 <b>Ответ TGT</b> (обращение №{id})\n\n{reply}",
        "only_text": "Пожалуйста, отправьте текстовое сообщение.",
    },
    "en": {
        "help": "ℹ️ <b>Help</b>\n\n🎭 «Clubs»: TGT clubs, their chairs, contacts and an application to join.\n📅 «Events»: upcoming events and registration (a reminder arrives a day before).\n🏛 «TGT Board»: members of the Management Board.\nℹ️ «About TGT»: the organization, its head, the room and the address.\n✉️ «Contact us»: send a suggestion, complaint or question (anonymously if you wish).\n\n<b>Commands</b>\n/start — start\n/menu — main menu\n/help — help\n/cancel — cancel the current action",
        "btn_events": "📅 Events",
        "btn_feedback": "✉️ Contact us",
        "btn_join": "📝 Join",
        "btn_register": "✅ Register",
        "btn_unregister": "❌ Cancel registration",
        "btn_cancel_inline": "❌ Cancel",
        "btn_send": "✅ Send",
        "btn_anon": "🕶 Anonymously",
        "btn_named": "👤 With my name",
        "btn_open_event": "📅 Details",
        "kind_s": "💡 Suggestion",
        "kind_c": "❗ Complaint",
        "kind_q": "❓ Question",
        "join_intro": "📝 <b>Application to «{club}»</b>\n\nYour details will be seen only by TGT administrators and the club leaders. Do not include personal data (passwords, FİN).\n\nWrite your first and last name:",
        "join_ask_faculty": "Write your faculty and year/group (for example: Digital Technologies, year 2):",
        "join_ask_phone": "A phone number to reach you (optional). Example: +994 55 123 45 67\nSend «-» to skip.",
        "join_confirm": "📝 <b>Check your application</b>\n\n🎭 {club}\n👤 {name}\n🏛 {faculty}\n☎️ {phone}\n\nSend it?",
        "join_done": "✅ Your application is received (№{id}). The club leaders will contact you soon.",
        "join_duplicate": "Your application to this club is already being reviewed.",
        "join_limit": "You can have at most 5 open applications at a time. Please wait for a reply.",
        "err_join_name": "First and last name must be 2 to 60 characters.",
        "err_join_faculty": "Faculty and year must be 2 to 80 characters.",
        "err_join_phone": "Enter the number like this: +994 55 123 45 67 (or «-»).",
        "app_accepted": "🎉 Your application to «{club}» has been accepted! The club leaders will contact you.",
        "app_declined": "Your application to «{club}» was not approved this time. You can join other clubs.",
        "events_title": "📅 <b>Upcoming events</b>\n\nChoose an event for details and registration:",
        "events_empty": "📅 No events are scheduled yet. Stay tuned!",
        "ev_registered": "👥 Registered: {count}",
        "ev_registered_cap": "👥 Registered: {count}/{capacity}",
        "reg_ok": "✅ You are registered! I will send a reminder a day before the event.\n(Your name and username are visible to the organizers.)",
        "reg_already": "You are already registered.",
        "reg_full": "⚠️ Unfortunately, all places are taken.",
        "reg_closed": "This event has already started or is over.",
        "unreg_ok": "Registration cancelled.",
        "ev_missing": "This event no longer exists.",
        "event_reminder": "⏰ <b>Reminder:</b> less than 24 hours until the event!\n\n{card}",
        "event_changed": "ℹ️ <b>Event details have changed</b>\n\n{card}",
        "event_cancelled": "❌ <b>Event cancelled:</b> {title}",
        "event_announce": "📣 <b>New event!</b>\n\n{card}",
        "fb_intro": "✉️ <b>Contact TGT</b>\n\nYou can send a suggestion, a complaint or a question. Choose the type:",
        "fb_ask_anon": "Show your name (your Telegram profile name) to the administrators?\n\n🕶 If you send it anonymously, your name will not be shown to the administrators, but you will still get the reply in this bot.",
        "fb_ask_text": "✍️ Write your message (10–1000 characters). Do not include personal data (passwords, FİN).",
        "fb_done": "✅ Your message has been sent (№{id}). The reply will arrive in this bot.",
        "fb_limit": "You can have at most 3 open messages at a time. Please wait for a reply.",
        "fb_cooldown": "⏳ Please wait a little before sending a new message.",
        "fb_muted": "Sending messages is temporarily restricted.",
        "err_fb_text": "The text must be 10 to 1000 characters.",
        "fb_reply": "💬 <b>TGT reply</b> (message №{id})\n\n{reply}",
        "only_text": "Please send a text message.",
    },
}
for _lang, _extra in _EXTRA3.items():
    T[_lang].update(_extra)


# ---------- Оценка мероприятий и тест «Какой клуб мне подходит?» ----------

_EXTRA4 = {
    "az": {
        "rate_request": "⭐ <b>«{title}» tədbirini necə qiymətləndirirsiniz?</b>\n\nİştirak etdiyiniz üçün təşəkkürlər! 1-dən 5-ə qədər qiymət verin:",
        "rate_thanks": "🙏 Təşəkkürlər! Qiymətiniz: {stars}",
        "rate_already": "Siz bu tədbiri artıq qiymətləndirmisiniz.",
        "rate_invalid": "Bu tədbiri qiymətləndirmək mümkün deyil.",
        "btn_quiz": "🧩 Hansı klub mənə uyğundur?",
        "quiz_question": "🧩 <b>Klub testi · {n}/{total}</b>\n\n{question}",
        "quiz_result": "🧩 <b>Sizə ən uyğun klub</b>\n\n{emoji} <b>{club}</b>\n\n{desc}{others}",
        "quiz_others": "\n\nHəmçinin uyğun ola bilər: {clubs}",
        "btn_quiz_again": "🔁 Yenidən",
        "btn_club_info": "ℹ️ Klub haqqında",
    },
    "ru": {
        "rate_request": "⭐ <b>Как вы оцениваете мероприятие «{title}»?</b>\n\nСпасибо, что пришли! Поставьте оценку от 1 до 5:",
        "rate_thanks": "🙏 Спасибо! Ваша оценка: {stars}",
        "rate_already": "Вы уже оценили это мероприятие.",
        "rate_invalid": "Это мероприятие нельзя оценить.",
        "btn_quiz": "🧩 Какой клуб мне подходит?",
        "quiz_question": "🧩 <b>Тест «Какой клуб» · {n}/{total}</b>\n\n{question}",
        "quiz_result": "🧩 <b>Вам лучше всего подходит клуб</b>\n\n{emoji} <b>{club}</b>\n\n{desc}{others}",
        "quiz_others": "\n\nТакже могут подойти: {clubs}",
        "btn_quiz_again": "🔁 Пройти заново",
        "btn_club_info": "ℹ️ О клубе",
    },
    "en": {
        "rate_request": "⭐ <b>How would you rate the event «{title}»?</b>\n\nThanks for coming! Give a rating from 1 to 5:",
        "rate_thanks": "🙏 Thank you! Your rating: {stars}",
        "rate_already": "You have already rated this event.",
        "rate_invalid": "This event cannot be rated.",
        "btn_quiz": "🧩 Which club suits me?",
        "quiz_question": "🧩 <b>Club quiz · {n}/{total}</b>\n\n{question}",
        "quiz_result": "🧩 <b>The club that suits you best</b>\n\n{emoji} <b>{club}</b>\n\n{desc}{others}",
        "quiz_others": "\n\nAlso might suit you: {clubs}",
        "btn_quiz_again": "🔁 Take it again",
        "btn_club_info": "ℹ️ About the club",
    },
}
for _lang, _extra in _EXTRA4.items():
    T[_lang].update(_extra)


# ---------- Новости TGT ----------

_EXTRA5 = {
    "az": {
        "help": "ℹ️ <b>Kömək</b>\n\n🎭 «Klublar»: TGT klubları, onların sədrləri, əlaqə məlumatları, klub testi və qoşulmaq üçün müraciət.\n📅 «Tədbirlər»: yaxınlaşan tədbirlər və qeydiyyat (bir gün əvvəl xatırlatma göndərilir).\n📰 «Xəbərlər»: TGT xəbərləri; abunə olsanız yeni xəbər çıxanda bildiriş alacaqsınız.\n🏛 «TGT İdarə Heyəti»: İdarə Heyətinin üzvləri.\nℹ️ «TGT haqqında»: təşkilat, rəhbər, otaq və ünvan.\n✉️ «Müraciət»: təklif, şikayət və ya sual göndərin (istəsəniz anonim).\n\n<b>Əmrlər</b>\n/start — başlamaq\n/menu — əsas menyu\n/help — kömək\n/cancel — cari əməliyyatı ləğv etmək",
        "btn_news": "📰 Xəbərlər",
        "news_title": "📰 <b>TGT xəbərləri</b>\n\nOxumaq üçün xəbəri seçin:",
        "news_empty": "📰 Hələlik xəbər yoxdur. Yeniliklər üçün abunə olun!",
        "btn_news_sub_on": "🔔 Yeni xəbərlərə abunə ol",
        "btn_news_sub_off": "🔕 Abunəliyi ləğv et",
        "news_sub_enabled": "✅ Abunə aktivdir: yeni xəbər çıxanda bildiriş alacaqsınız.",
        "news_sub_disabled": "Abunəlik ləğv edildi.",
        "btn_news_link": "🔗 Ətraflı",
        "news_missing": "Bu xəbər artıq mövcud deyil.",
        "news_alert_head": "🔔 <b>TGT xəbəri</b>\n\n",
    },
    "ru": {
        "help": "ℹ️ <b>Помощь</b>\n\n🎭 «Клубы»: клубы TGT, их председатели, контакты, тест «Какой клуб мне подходит?» и заявка на вступление.\n📅 «Мероприятия»: ближайшие события и запись (за сутки приходит напоминание).\n📰 «Новости»: новости TGT; при подписке вы получите уведомление о новой новости.\n🏛 «Правление TGT»: члены Правления.\nℹ️ «О TGT»: организация, руководитель, комната и адрес.\n✉️ «Обращение»: отправьте предложение, жалобу или вопрос (можно анонимно).\n\n<b>Команды</b>\n/start — начать\n/menu — главное меню\n/help — помощь\n/cancel — отменить текущее действие",
        "btn_news": "📰 Новости",
        "news_title": "📰 <b>Новости TGT</b>\n\nВыберите новость, чтобы прочитать:",
        "news_empty": "📰 Пока новостей нет. Подпишитесь, чтобы не пропустить!",
        "btn_news_sub_on": "🔔 Подписаться на новости",
        "btn_news_sub_off": "🔕 Отписаться",
        "news_sub_enabled": "✅ Подписка включена: вы получите уведомление о новой новости.",
        "news_sub_disabled": "Подписка отключена.",
        "btn_news_link": "🔗 Подробнее",
        "news_missing": "Этой новости больше нет.",
        "news_alert_head": "🔔 <b>Новость TGT</b>\n\n",
    },
    "en": {
        "help": "ℹ️ <b>Help</b>\n\n🎭 «Clubs»: TGT clubs, their chairs, contacts, the «Which club suits me?» quiz and an application to join.\n📅 «Events»: upcoming events and registration (a reminder arrives a day before).\n📰 «News»: TGT news; if you subscribe you will be notified about new items.\n🏛 «TGT Board»: members of the Management Board.\nℹ️ «About TGT»: the organization, its head, the room and the address.\n✉️ «Contact us»: send a suggestion, complaint or question (anonymously if you wish).\n\n<b>Commands</b>\n/start — start\n/menu — main menu\n/help — help\n/cancel — cancel the current action",
        "btn_news": "📰 News",
        "news_title": "📰 <b>TGT news</b>\n\nChoose an item to read:",
        "news_empty": "📰 No news yet. Subscribe so you do not miss it!",
        "btn_news_sub_on": "🔔 Subscribe to news",
        "btn_news_sub_off": "🔕 Unsubscribe",
        "news_sub_enabled": "✅ Subscribed: you will be notified about new news.",
        "news_sub_disabled": "Unsubscribed.",
        "btn_news_link": "🔗 Read more",
        "news_missing": "This news item no longer exists.",
        "news_alert_head": "🔔 <b>TGT news</b>\n\n",
    },
}
for _lang, _extra in _EXTRA5.items():
    T[_lang].update(_extra)


# ---------- FAQ ----------

_EXTRA6 = {
    "az": {
        "help": "ℹ️ <b>Kömək</b>\n\n🎭 «Klublar»: TGT klubları, onların sədrləri, əlaqə məlumatları, klub testi və qoşulmaq üçün müraciət.\n📅 «Tədbirlər»: yaxınlaşan tədbirlər və qeydiyyat (bir gün əvvəl xatırlatma göndərilir).\n📰 «Xəbərlər»: TGT xəbərləri; abunə olsanız yeni xəbər çıxanda bildiriş alacaqsınız.\n🏛 «TGT İdarə Heyəti»: İdarə Heyətinin üzvləri.\nℹ️ «TGT haqqında»: təşkilat, rəhbər, otaq və ünvan.\n❓ «Tez-tez verilən suallar»: TGT haqqında ən çox verilən suallara cavablar.\n✉️ «Müraciət»: təklif, şikayət və ya sual göndərin (istəsəniz anonim).\n\n<b>Əmrlər</b>\n/start — başlamaq\n/menu — əsas menyu\n/help — kömək\n/cancel — cari əməliyyatı ləğv etmək",
        "btn_faq": "❓ Tez-tez verilən suallar",
        "faq_title": "❓ <b>Tez-tez verilən suallar</b>\n\nSualı seçin:",
        "faq_empty": "❓ Hələlik sual əlavə olunmayıb.",
        "faq_missing": "Bu sual artıq mövcud deyil.",
    },
    "ru": {
        "help": "ℹ️ <b>Помощь</b>\n\n🎭 «Клубы»: клубы TGT, их председатели, контакты, тест «Какой клуб мне подходит?» и заявка на вступление.\n📅 «Мероприятия»: ближайшие события и запись (за сутки приходит напоминание).\n📰 «Новости»: новости TGT; при подписке вы получите уведомление о новой новости.\n🏛 «Правление TGT»: члены Правления.\nℹ️ «О TGT»: организация, руководитель, комната и адрес.\n❓ «Частые вопросы»: ответы на самые популярные вопросы о TGT.\n✉️ «Обращение»: отправьте предложение, жалобу или вопрос (можно анонимно).\n\n<b>Команды</b>\n/start — начать\n/menu — главное меню\n/help — помощь\n/cancel — отменить текущее действие",
        "btn_faq": "❓ Частые вопросы",
        "faq_title": "❓ <b>Частые вопросы</b>\n\nВыберите вопрос:",
        "faq_empty": "❓ Пока вопросы не добавлены.",
        "faq_missing": "Этого вопроса больше нет.",
    },
    "en": {
        "help": "ℹ️ <b>Help</b>\n\n🎭 «Clubs»: TGT clubs, their chairs, contacts, the «Which club suits me?» quiz and an application to join.\n📅 «Events»: upcoming events and registration (a reminder arrives a day before).\n📰 «News»: TGT news; if you subscribe you will be notified about new items.\n🏛 «TGT Board»: members of the Management Board.\nℹ️ «About TGT»: the organization, its head, the room and the address.\n❓ «FAQ»: answers to the most frequently asked questions about TGT.\n✉️ «Contact us»: send a suggestion, complaint or question (anonymously if you wish).\n\n<b>Commands</b>\n/start — start\n/menu — main menu\n/help — help\n/cancel — cancel the current action",
        "btn_faq": "❓ FAQ",
        "faq_title": "❓ <b>Frequently asked questions</b>\n\nChoose a question:",
        "faq_empty": "❓ No questions have been added yet.",
        "faq_missing": "This question no longer exists.",
    },
}
for _lang, _extra in _EXTRA6.items():
    T[_lang].update(_extra)


# ---------- Подпись разработчика ----------

_EXTRA7 = {
    "az": {"developer_line": "👨‍💻 Developer: {name}"},
    "ru": {"developer_line": "👨‍💻 Разработчик: {name}"},
    "en": {"developer_line": "👨‍💻 Developer: {name}"},
}
for _lang, _extra in _EXTRA7.items():
    T[_lang].update(_extra)


# ---------- Служебные таблицы для статистики и фильтров ----------

SECTION_BUTTONS = ("btn_clubs", "btn_events", "btn_news", "btn_board", "btn_about", "btn_faq", "btn_feedback", "btn_lang")
# текст кнопки (на любом языке) -> имя раздела, например "clubs"
BUTTON_TO_SECTION: dict[str, str] = {
    T[lang][key]: key[len("btn_"):] for key in SECTION_BUTTONS for lang in T
}
# все кнопки нижней клавиатуры (чтобы не принимать их за обычный ввод)
ALL_REPLY_BUTTONS: set[str] = set(BUTTON_TO_SECTION)
