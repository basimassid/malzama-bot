# -*- coding: utf-8 -*-
"""
بوت اختبار «ملزمة اللغة العربية» — إعداد الطالب باسم عصيد كمر
==============================================================
يعتمد «استفتاء الكويز» المدمج في تلجرام:
  • ⏱️ عدّاد زمني حقيقي يظهره تلجرام لكل سؤال (افتراضيًّا ٣٠ ثانية).
  • ✅ تصحيح فوري داخل الاستفتاء + 💡 شرح لكل إجابة.
  • 🏆 نقاط ولوحة صدارة لأفضل النتائج بين الزملاء (تُحفظ في ملف).
  • بنك أسئلة (٥٠ سؤالًا): القرآن، الأدب، القواعد، الإملاء.

المتطلبات:  pip install "python-telegram-bot>=20"
التشغيل  :  ضع BOT_TOKEN في متغيّر البيئة ثم: python telegram_quiz_bot.py
"""

import os
import json
import random
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    PollAnswerHandler,
    ContextTypes,
)

# ====== الإعدادات ======
BOT_TOKEN = os.environ.get("BOT_TOKEN", "ضع_توكن_البوت_هنا")
TIME_LIMIT = int(os.environ.get("TIME_LIMIT", "30"))     # ثوانٍ لكل سؤال (5..600)
TIME_LIMIT = max(5, min(TIME_LIMIT, 600))
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()     # معرّف المدير لاستقبال الإشعارات (اختياري)
LEADERBOARD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "leaderboard.json")
TOP_N = 10


async def notify_admin(context, text: str) -> None:
    """يرسل إشعارًا للمدير إن كان ADMIN_ID مضبوطًا (مع تجاهل أي خطأ)."""
    if not ADMIN_ID:
        return
    try:
        chat = int(ADMIN_ID) if ADMIN_ID.lstrip("-").isdigit() else ADMIN_ID
        await context.bot.send_message(chat_id=chat, text=text)
    except Exception as e:
        logging.warning("تعذّر إرسال إشعار المدير: %s", e)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# ============================================================
#                       بنك الأسئلة (٥٠)
# ============================================================
QUESTIONS = {
    "quran": [
        {"q": "«وَالْقُرْآنِ الْحَكِيمِ» — في أي سورة وردت؟",
         "opts": ["سورة يوسف", "سورة يس", "سورة النحل", "سورة طه"], "ans": 1,
         "exp": "من مطلع سورة يس (الآية ٢)."},
        {"q": "السورة التي بُدئت آياتها بـ«الر تِلْكَ آيَاتُ الْكِتَابِ الْمُبِينِ»؟",
         "opts": ["يس", "الكهف", "يوسف", "الرعد"], "ans": 2, "exp": "مطلع سورة يوسف."},
        {"q": "أكمل: «إِنَّكَ لَمِنَ الْمُرْسَلِينَ ۝ عَلَىٰ صِرَاطٍ ...»",
         "opts": ["قَوِيمٍ", "مُّسْتَقِيمٍ", "عَظِيمٍ", "كَرِيمٍ"], "ans": 1,
         "exp": "«عَلَىٰ صِرَاطٍ مُّسْتَقِيمٍ» (يس: ٤)."},
        {"q": "كم كوكبًا رأى يوسف عليه السلام في رؤياه؟",
         "opts": ["تسعة", "عشرة", "أحد عشر", "اثنا عشر"], "ans": 2,
         "exp": "«أَحَدَ عَشَرَ كَوْكَبًا وَالشَّمْسَ وَالْقَمَرَ»."},
        {"q": "أكمل: «نَحْنُ نَقُصُّ عَلَيْكَ أَحْسَنَ ...»",
         "opts": ["الْحَدِيثِ", "الْقَصَصِ", "الْكَلَامِ", "الْبَيَانِ"], "ans": 1,
         "exp": "«أَحْسَنَ الْقَصَصِ» (يوسف: ٣)."},
        {"q": "من القائل: «يَا بُنَيَّ لَا تَقْصُصْ رُؤْيَاكَ عَلَىٰ إِخْوَتِكَ»؟",
         "opts": ["يوسف", "يعقوب (والده)", "أحد إخوته", "عزيز مصر"], "ans": 1,
         "exp": "قالها يعقوب عليه السلام لابنه."},
        {"q": "أكمل: «تَنزِيلَ الْعَزِيزِ ...»",
         "opts": ["الْحَكِيمِ", "الرَّحِيمِ", "الْعَلِيمِ", "الْكَرِيمِ"], "ans": 1,
         "exp": "«تَنزِيلَ الْعَزِيزِ الرَّحِيمِ» (يس: ٥)."},
        {"q": "«يس» من أي نوع من فواتح السور؟",
         "opts": ["أسماء", "الحروف المقطّعة", "أفعال", "أدوات"], "ans": 1,
         "exp": "من الحروف المقطّعة في فواتح السور."},
        {"q": "ما رقم سورة يس في المصحف الشريف؟",
         "opts": ["٣٥", "٣٦", "٣٧", "٣٨"], "ans": 1, "exp": "سورة يس رقم ٣٦."},
        {"q": "أكمل: «إِنَّا أَنزَلْنَاهُ قُرْآنًا عَرَبِيًّا لَّعَلَّكُمْ ...»",
         "opts": ["تَذَكَّرُونَ", "تَعْقِلُونَ", "تُفْلِحُونَ", "تَشْكُرُونَ"], "ans": 1,
         "exp": "«لَّعَلَّكُمْ تَعْقِلُونَ» (يوسف: ٢)."},
        {"q": "وُصِف الشيطان في خاتمة آيات يوسف بأنه للإنسان؟",
         "opts": ["عَدُوٌّ مُّبِينٌ", "خَصْمٌ لَدُودٌ", "وَلِيٌّ حَمِيمٌ", "قَرِينٌ"], "ans": 0,
         "exp": "«إِنَّ الشَّيْطَانَ لِلْإِنسَانِ عَدُوٌّ مُّبِينٌ»."},
        {"q": "أكمل: «وَإِن كُنتَ مِن قَبْلِهِ لَمِنَ ...»",
         "opts": ["الْغَافِلِينَ", "الْخَاسِرِينَ", "النَّادِمِينَ", "الْجَاهِلِينَ"], "ans": 0,
         "exp": "«لَمِنَ الْغَافِلِينَ» (يوسف: ٣)."},
    ],
    "adab": [
        {"q": "قصيدة «قارئة الفنجان» لأي شاعر؟",
         "opts": ["أحمد مطر", "نزار قباني", "بدر شاكر السياب", "عبد الرزاق عبد الواحد"],
         "ans": 1, "exp": "للشاعر السوري نزار قباني."},
        {"q": "«الزائر الأخير» من شعر؟",
         "opts": ["عبد الرزاق عبد الواحد", "نزار قباني", "السياب", "أحمد مطر"], "ans": 0,
         "exp": "للشاعر العراقي عبد الرزاق عبد الواحد."},
        {"q": "«رسالة إلى يزيد» لأي شاعر؟",
         "opts": ["نزار قباني", "بدر شاكر السياب", "أحمد مطر", "عبد الرزاق عبد الواحد"],
         "ans": 1, "exp": "للشاعر العراقي بدر شاكر السياب."},
        {"q": "«اعتذار (فوق نعلي)» لأي شاعر؟",
         "opts": ["أحمد مطر", "نزار قباني", "السياب", "المتنبي"], "ans": 0,
         "exp": "للشاعر العراقي أحمد مطر."},
        {"q": "أي شاعر له قصيدتان ضمن الملزمة؟",
         "opts": ["السياب", "أحمد مطر", "نزار قباني", "عبد الرزاق عبد الواحد"], "ans": 2,
         "exp": "نزار قباني: «أين أذهب» و«قارئة الفنجان»."},
        {"q": "بدر شاكر السياب يُعدّ من رواد؟",
         "opts": ["الشعر العمودي", "الشعر الحر (التفعيلة)", "الموشحات", "شعر المعلقات"],
         "ans": 1, "exp": "من رواد الشعر الحر (شعر التفعيلة)."},
        {"q": "أيّ قصيدة في الملزمة غنّاها الفنان عبد الحليم حافظ؟",
         "opts": ["أين أذهب", "الزائر الأخير", "قارئة الفنجان", "رسالة إلى يزيد"], "ans": 2,
         "exp": "«قارئة الفنجان» لنزار قباني."},
        {"q": "قصيدة «أين أذهب» لأي شاعر؟",
         "opts": ["نزار قباني", "أحمد مطر", "السياب", "عبد الرزاق عبد الواحد"], "ans": 0,
         "exp": "للشاعر نزار قباني."},
        {"q": "ما جنسية الشاعر نزار قباني؟",
         "opts": ["عراقي", "سوري", "مصري", "لبناني"], "ans": 1, "exp": "شاعر سوري."},
        {"q": "الشاعر المعروف بقصائده الساخرة القصيرة «اللافتات»؟",
         "opts": ["السياب", "أحمد مطر", "نزار قباني", "عبد الرزاق عبد الواحد"], "ans": 1,
         "exp": "أحمد مطر صاحب «اللافتات»."},
        {"q": "عبد الرزاق عبد الواحد شاعر؟",
         "opts": ["مصري", "سوري", "عراقي", "سعودي"], "ans": 2, "exp": "شاعر عراقي بارز."},
        {"q": "في أي عام تُوفّي بدر شاكر السياب؟",
         "opts": ["١٩٥٤", "١٩٦٤", "١٩٧٤", "١٩٨٤"], "ans": 1, "exp": "تُوفّي عام ١٩٦٤."},
    ],
    "qawaid": [
        {"q": "«نجحَ الطالبُ» — ما إعراب «الطالبُ»؟",
         "opts": ["مفعول به", "فاعل مرفوع", "حال", "مبتدأ"], "ans": 1,
         "exp": "فاعل مرفوع وعلامة رفعه الضمة."},
        {"q": "«قرأَ محمدٌ الكتابَ» — ما إعراب «الكتابَ»؟",
         "opts": ["فاعل", "مفعول مطلق", "مفعول به منصوب", "حال"], "ans": 2,
         "exp": "مفعول به منصوب وعلامة نصبه الفتحة."},
        {"q": "مصدرٌ منصوب يُذكر بعد فعلٍ من لفظه لتوكيده، هو؟",
         "opts": ["الحال", "المفعول المطلق", "المفعول به", "الفاعل"], "ans": 1,
         "exp": "المفعول المطلق، مثل: فرحَ فرحًا."},
        {"q": "«عادَ الجنديُّ منتصرًا» — ما إعراب «منتصرًا»؟",
         "opts": ["مفعول به", "حال منصوب", "فاعل", "مفعول مطلق"], "ans": 1,
         "exp": "حال منصوب يبيّن هيئة الفاعل."},
        {"q": "«فرِحَ الطفلُ فرحًا» — ما إعراب «فرحًا»؟",
         "opts": ["مفعول مطلق", "حال", "مفعول به", "تمييز"], "ans": 0,
         "exp": "مفعول مطلق (للتوكيد) منصوب."},
        {"q": "الفعل «اُكْتُبْ» نوعه؟",
         "opts": ["ماضٍ", "مضارع", "أمر", "مصدر"], "ans": 2, "exp": "فعل أمر مبنيٌّ على السكون."},
        {"q": "علامة نصب المفعول به في «شربتُ الماءَ»؟",
         "opts": ["الضمة", "الكسرة", "الفتحة", "السكون"], "ans": 2, "exp": "ينصب بالفتحة."},
        {"q": "الحال يأتي غالبًا...؟",
         "opts": ["معرفة وصاحبه نكرة", "نكرة وصاحبه معرفة",
                  "معرفة وصاحبه معرفة", "نكرة وصاحبه نكرة"], "ans": 1,
         "exp": "الحال نكرة وصاحبه معرفة غالبًا."},
        {"q": "الفعل كلمةٌ تدلُّ على؟",
         "opts": ["ذاتٍ فقط", "حدثٍ مقترنٍ بزمن", "صفةٍ ثابتة", "مكان"], "ans": 1,
         "exp": "حدثٌ مقترنٌ بزمن (ماضٍ/مضارع/أمر)."},
        {"q": "أيٌّ مما يلي ليس من أنواع الفعل الثلاثة؟",
         "opts": ["الماضي", "المضارع", "الأمر", "المصدر"], "ans": 3,
         "exp": "المصدر اسمٌ وليس فعلًا."},
        {"q": "«دُرتُ دورتين» — المفعول المطلق «دورتين» جاء لبيان؟",
         "opts": ["التوكيد", "النوع", "العدد", "الزمان"], "ans": 2, "exp": "لبيان العدد."},
        {"q": "«سارَ سيرًا حثيثًا» — المفعول المطلق جاء لبيان؟",
         "opts": ["العدد", "النوع", "التوكيد", "المكان"], "ans": 1, "exp": "لبيان النوع."},
        {"q": "الفعل «يكتبُ» نوعه؟",
         "opts": ["ماضٍ", "مضارع", "أمر", "مصدر"], "ans": 1, "exp": "فعل مضارع مرفوع."},
    ],
    "imla": [
        {"q": "أي علامة تُوضع بين جملتين الثانية سببٌ/نتيجة للأولى؟",
         "opts": ["الفاصلة (،)", "الفاصلة المنقوطة (؛)", "النقطتان (:)", "الشرطة (—)"],
         "ans": 1, "exp": "الفاصلة المنقوطة، مثل: اجتهدَ؛ فنجحَ."},
        {"q": "النقطتان (:) تُستعملان قبل؟",
         "opts": ["نهاية الجملة", "القول المنقول والتعداد", "السؤال", "التعجّب"], "ans": 1,
         "exp": "قبل القول المنقول والتعداد والتفسير."},
        {"q": "أيّهما الصواب في المكاتبات الرسمية؟",
         "opts": ["إلحاقًا بكتابكم", "لاحقًا لكتابكم", "الاثنان صواب", "لا شيء"], "ans": 1,
         "exp": "«لاحقًا» تعني تابعًا، وهو المقصود."},
        {"q": "أيّهما الصواب؟",
         "opts": ["على ضوء المذكرة", "في ضوء المذكرة", "الاثنان", "حول ضوء المذكرة"],
         "ans": 1, "exp": "«في ضوء» أنسب للسياق المجازي."},
        {"q": "«المذكور أعلاه» يُستبدل بالأصحّ بـ؟",
         "opts": ["المذكور آنفًا", "المذكور تحته", "المذكور خلفه", "لا تغيير"], "ans": 0,
         "exp": "«آنفًا» تعني ما سبق ذكره."},
        {"q": "ما علامة الترقيم المناسبة بعد «ما أجملَ السماءَ»؟",
         "opts": ["نقطة (.)", "علامة استفهام (؟)", "علامة تعجّب (!)", "فاصلة (،)"], "ans": 2,
         "exp": "علامة التأثّر/التعجّب (!)."},
        {"q": "الأقواس المزخرفة ﴿ ﴾ تُستعمل لحصر؟",
         "opts": ["الحوار", "الآيات القرآنية", "الكلام المعترض", "العناوين"], "ans": 1,
         "exp": "تُحصر بها الآيات القرآنية."},
        {"q": "النقطة (.) تُوضع في؟",
         "opts": ["وسط الجملة", "نهاية الجملة التامّة المعنى", "بعد السؤال", "قبل التعداد"],
         "ans": 1, "exp": "في نهاية الجملة التامّة."},
        {"q": "علامة الاستفهام (؟) تُوضع بعد؟",
         "opts": ["الجملة الخبرية", "الجملة الاستفهامية", "التعجّب", "القول المنقول"],
         "ans": 1, "exp": "بعد الجملة الاستفهامية."},
        {"q": "علامتا التنصيص « » تُستعملان لـ؟",
         "opts": ["حصر الكلام المنقول بنصّه", "التعجّب", "التعداد", "الحذف"], "ans": 0,
         "exp": "لحصر الكلام المنقول بنصّه دون تغيير."},
        {"q": "القوسان المعقوفان [ ] يُستعملان لـ؟",
         "opts": ["الآيات", "ما يضيفه الناقل إلى النص الأصلي", "الحوار", "السؤال"], "ans": 1,
         "exp": "لما يضيفه الناقل من عنده إلى النص."},
        {"q": "سبب خطأ بدء الخطاب بـ«كتابكم...» مباشرةً؟",
         "opts": ["مبتدأ لا خبر له", "فعل ناقص", "حال غير منصوب", "لا خطأ فيه"], "ans": 0,
         "exp": "يصبح مبتدأ بلا خبر؛ والصواب: «إشارةً إلى كتابكم»."},
        {"q": "الشرطة (—) في الحوار تدلُّ على؟",
         "opts": ["نهاية الكلام", "المتكلّم", "السؤال", "التعجّب"], "ans": 1,
         "exp": "تدلُّ على المتكلّم في الحوار، وبين العدد والمعدود."},
    ],
}

SECTION_NAMES = {"quran": "القرآن الكريم", "adab": "الأدب",
                 "qawaid": "القواعد", "imla": "الإملاء"}


# ============================================================
#                       لوحة الصدارة
# ============================================================
def load_board() -> dict:
    try:
        with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_board(board: dict) -> None:
    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(board, f, ensure_ascii=False, indent=2)


def update_board(board: dict, user_id, name: str, score: int, total: int) -> bool:
    pct = round(score / total * 100)
    uid = str(user_id)
    prev = board.get(uid)
    if prev is None or pct > prev["pct"] or (pct == prev["pct"] and score > prev["score"]):
        board[uid] = {"name": name, "score": score, "total": total, "pct": pct}
        return True
    board[uid]["name"] = name
    return False


def board_ranking(board: dict):
    return sorted(board.items(),
                  key=lambda kv: (kv[1]["pct"], kv[1]["score"]), reverse=True)


def board_text(board: dict, highlight_uid: str = None) -> str:
    ranking = board_ranking(board)
    if not ranking:
        return ("🏆 <b>لوحة الصدارة</b>\n\n"
                "لا توجد نتائج بعد — كن أول المتصدّرين بإكمال «الاختبار الشامل»!")
    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 <b>لوحة الصدارة — أفضل النتائج</b>\n"]
    shown = [u for u, _ in ranking[:TOP_N]]
    for i, (uid, e) in enumerate(ranking[:TOP_N]):
        rank = medals[i] if i < 3 else f"{i + 1}."
        star = " 👈" if uid == highlight_uid else ""
        lines.append(f"{rank} {e['name']} — {e['pct']}% ({e['score']}/{e['total']}){star}")
    if highlight_uid and highlight_uid not in shown:
        for i, (uid, e) in enumerate(ranking):
            if uid == highlight_uid:
                lines.append(f"\nترتيبك: {i + 1}. {e['name']} — "
                             f"{e['pct']}% ({e['score']}/{e['total']})")
                break
    return "\n".join(lines)


# ============================================================
#                       الواجهة
# ============================================================
def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 اختبار شامل (كل الملزمة)", callback_data="m|all")],
        [InlineKeyboardButton("🕌 القرآن", callback_data="m|quran"),
         InlineKeyboardButton("📜 الأدب", callback_data="m|adab")],
        [InlineKeyboardButton("📝 القواعد", callback_data="m|qawaid"),
         InlineKeyboardButton("✒️ الإملاء", callback_data="m|imla")],
        [InlineKeyboardButton("🏆 لوحة الصدارة", callback_data="board")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🌿 <b>مرحبًا بك في اختبار ملزمة اللغة العربية</b>\n"
        "<i>إعداد الطالب: باسم عصيد كمر</i>\n\n"
        f"كل سؤال على شكل استفتاء فيه ⏱️ <b>عدّاد {TIME_LIMIT} ثانية</b>، "
        "وتصحيحٌ فوري وشرحٌ للإجابة، ولوحة صدارةٍ بين الزملاء.\n\n"
        "اختر نوع الاختبار للبدء 👇"
    )
    target = update.message or update.callback_query.message
    await target.reply_text(text, reply_markup=main_menu(), parse_mode=ParseMode.HTML)

    # إشعار المدير ببدء الطالب (فقط عند أمر /start أو /quiz الفعلي)
    if update.message:
        u = update.effective_user
        who = u.first_name or "طالب"
        if u.username:
            who += f" (@{u.username})"
        await notify_admin(context, f"🔔 بدأ الطالب {who} الاختبار الآن.")


def build_quiz(section: str):
    if section == "all":
        items = [dict(q, _sec=sec) for sec, qs in QUESTIONS.items() for q in qs]
    else:
        items = [dict(q, _sec=section) for q in QUESTIONS[section]]
    random.shuffle(items)
    return items


async def send_question(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    ud = context.user_data
    quiz, idx = ud["quiz"], ud["idx"]
    q = quiz[idx]
    qtext = f"({idx + 1}/{len(quiz)}) [{SECTION_NAMES[q['_sec']]}]\n{q['q']}"
    msg = await context.bot.send_poll(
        chat_id=chat_id,
        question=qtext,
        options=q["opts"],
        type="quiz",
        correct_option_id=q["ans"],
        explanation=q["exp"],
        open_period=TIME_LIMIT,
        is_anonymous=False,
    )
    ud["poll_id"] = msg.poll.id
    ud["cur_idx"] = idx
    ud["cur_done"] = False
    ud["timer_task"] = asyncio.create_task(poll_timer(context, chat_id, idx))


async def poll_timer(context: ContextTypes.DEFAULT_TYPE, chat_id: int, idx: int) -> None:
    """احتياط: ينتقل للسؤال التالي إذا لم يُجب الطالب حتى انتهاء العدّاد."""
    try:
        await asyncio.sleep(TIME_LIMIT + 2)
    except asyncio.CancelledError:
        return
    ud = context.user_data
    if ud.get("cur_done") or ud.get("idx") != idx:
        return
    ud["cur_done"] = True            # فات الوقت دون إجابة (لا نقطة)؛ تلجرام كشف الصواب
    await advance(context, chat_id)


async def on_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pa = update.poll_answer
    ud = context.user_data
    if ud.get("poll_id") != pa.poll_id or ud.get("cur_done"):
        return
    ud["cur_done"] = True
    task = ud.get("timer_task")
    if task:
        task.cancel()
    chosen = pa.option_ids[0] if pa.option_ids else -1
    if chosen == ud["quiz"][ud["cur_idx"]]["ans"]:
        ud["score"] += 1
    await advance(context, ud["chat_id"])


async def on_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    section = query.data.split("|", 1)[1]
    u = update.effective_user
    context.user_data.update(
        quiz=build_quiz(section), idx=0, score=0, section=section,
        uid=u.id, name=(u.full_name or u.username or "طالب"),
        chat_id=query.message.chat_id,
    )
    title = "الاختبار الشامل" if section == "all" else SECTION_NAMES[section]
    await query.edit_message_text(
        f"✅ بدأنا: <b>{title}</b>\nأجب قبل انتهاء العدّاد ⏱️ — بالتوفيق! 🍀",
        parse_mode=ParseMode.HTML)
    await send_question(context, query.message.chat_id)


async def advance(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    ud = context.user_data
    if "quiz" not in ud:
        return
    ud["idx"] += 1
    if ud["idx"] < len(ud["quiz"]):
        await send_question(context, chat_id)
    else:
        await finish(context, chat_id)


async def finish(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    ud = context.user_data
    score, total = ud["score"], len(ud["quiz"])
    pct = round(score / total * 100)
    if pct == 100:
        note, emoji = "ممتاز! علامة كاملة 🏆", "🌟"
    elif pct >= 75:
        note, emoji = "جيد جدًّا، استمر!", "👏"
    elif pct >= 50:
        note, emoji = "جيد، وتحتاج مراجعةً بسيطة.", "📖"
    else:
        note, emoji = "راجع الملزمة جيدًا ثم أعد المحاولة.", "💪"

    record_line = ""
    if ud.get("section") == "all":
        board = context.bot_data.setdefault("board", load_board())
        is_pb = update_board(board, ud.get("uid", chat_id),
                             ud.get("name", "طالب"), score, total)
        save_board(board)
        record_line = ("\n🎉 رقم قياسي جديد لك في الصدارة!" if is_pb
                       else "\nسُجّلت محاولتك (لم تتجاوز أفضل نتيجة سابقة لك).")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 اختبار جديد", callback_data="restart")],
        [InlineKeyboardButton("🏆 لوحة الصدارة", callback_data="board")],
    ])
    await context.bot.send_message(
        chat_id,
        f"{emoji} <b>انتهى الاختبار</b>\n\n"
        f"نتيجتك: <b>{score} / {total}</b>  ({pct}%)\n{note}{record_line}",
        reply_markup=kb, parse_mode=ParseMode.HTML)

    # إشعار المدير بانتهاء الطالب ونتيجته
    await notify_admin(
        context,
        f"✅ أنهى الطالب {ud.get('name', 'طالب')} الاختبار. "
        f"النتيجة: {score} من {total}.")

    for k in ("quiz", "idx", "score", "cur_done", "timer_task",
              "poll_id", "cur_idx", "section"):
        ud.pop(k, None)


async def show_board(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    board = context.bot_data.setdefault("board", load_board())
    uid = str(update.effective_user.id)
    text = board_text(board, highlight_uid=uid)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ القائمة", callback_data="home")]])
    if update.callback_query:
   
