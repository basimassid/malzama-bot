# -*- coding: utf-8 -*-
"""
بوت اختبارات «ملزمة الطالب باسم عصيد كمر»  (متعدّد المواد)
==========================================================
المواد:
  • اللغة العربية: القرآن، الأدب، القواعد، الإملاء.
  • البرمجة C++: شامل لكل النماذج (A–F) — نسخة عربية ونسخة إنجليزية.

المزايا:
  • ⏱️ استفتاء كويز بعدّاد زمني حقيقي لكل سؤال (افتراضيًّا ٣٠ ثانية).
  • ✅ تصحيح فوري + 💡 شرح لكل إجابة.
  • 🏆 لوحة صدارة لأفضل النتائج (تُحفظ في ملف).
  • 🔔 إشعارات للمدير عند بدء/إنهاء الطالب (عبر ADMIN_ID).

المتطلبات:  pip install "python-telegram-bot>=20"
"""

import os
import json
import random
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, PollAnswerHandler, ContextTypes)

# ====== الإعدادات ======
BOT_TOKEN = os.environ.get("BOT_TOKEN", "ضع_توكن_البوت_هنا")
TIME_LIMIT = max(5, min(int(os.environ.get("TIME_LIMIT", "30")), 600))
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()
CPP_SAMPLE = int(os.getenv("CPP_SAMPLE", "0"))   # 0 = كل الأسئلة، أو عدد للاختيار العشوائي
LEADERBOARD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leaderboard.json")
TOP_N = 10
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)


async def notify_admin(context, text: str) -> None:
    if not ADMIN_ID:
        return
    try:
        chat = int(ADMIN_ID) if ADMIN_ID.lstrip("-").isdigit() else ADMIN_ID
        await context.bot.send_message(chat_id=chat, text=text)
    except Exception as e:
        logging.warning("تعذّر إرسال إشعار المدير: %s", e)


# ============================================================
#            بنك أسئلة اللغة العربية (٤ أقسام)
# ============================================================
ARABIC = {
    "quran": [
        {"q": "«وَالْقُرْآنِ الْحَكِيمِ» — في أي سورة وردت؟",
         "opts": ["سورة يوسف", "سورة يس", "سورة النحل", "سورة طه"], "ans": 1, "exp": "من مطلع سورة يس (الآية ٢)."},
        {"q": "السورة التي بُدئت آياتها بـ«الر تِلْكَ آيَاتُ الْكِتَابِ الْمُبِينِ»؟",
         "opts": ["يس", "الكهف", "يوسف", "الرعد"], "ans": 2, "exp": "مطلع سورة يوسف."},
        {"q": "أكمل: «إِنَّكَ لَمِنَ الْمُرْسَلِينَ ۝ عَلَىٰ صِرَاطٍ ...»",
         "opts": ["قَوِيمٍ", "مُّسْتَقِيمٍ", "عَظِيمٍ", "كَرِيمٍ"], "ans": 1, "exp": "«عَلَىٰ صِرَاطٍ مُّسْتَقِيمٍ» (يس: ٤)."},
        {"q": "كم كوكبًا رأى يوسف عليه السلام في رؤياه؟",
         "opts": ["تسعة", "عشرة", "أحد عشر", "اثنا عشر"], "ans": 2, "exp": "«أَحَدَ عَشَرَ كَوْكَبًا...»."},
        {"q": "أكمل: «نَحْنُ نَقُصُّ عَلَيْكَ أَحْسَنَ ...»",
         "opts": ["الْحَدِيثِ", "الْقَصَصِ", "الْكَلَامِ", "الْبَيَانِ"], "ans": 1, "exp": "«أَحْسَنَ الْقَصَصِ» (يوسف: ٣)."},
        {"q": "من القائل: «يَا بُنَيَّ لَا تَقْصُصْ رُؤْيَاكَ عَلَىٰ إِخْوَتِكَ»؟",
         "opts": ["يوسف", "يعقوب (والده)", "أحد إخوته", "عزيز مصر"], "ans": 1, "exp": "قالها يعقوب عليه السلام."},
        {"q": "أكمل: «تَنزِيلَ الْعَزِيزِ ...»",
         "opts": ["الْحَكِيمِ", "الرَّحِيمِ", "الْعَلِيمِ", "الْكَرِيمِ"], "ans": 1, "exp": "(يس: ٥)."},
        {"q": "«يس» من أي نوع من فواتح السور؟",
         "opts": ["أسماء", "الحروف المقطّعة", "أفعال", "أدوات"], "ans": 1, "exp": "من الحروف المقطّعة."},
        {"q": "ما رقم سورة يس في المصحف؟", "opts": ["٣٥", "٣٦", "٣٧", "٣٨"], "ans": 1, "exp": "رقم ٣٦."},
        {"q": "أكمل: «إِنَّا أَنزَلْنَاهُ قُرْآنًا عَرَبِيًّا لَّعَلَّكُمْ ...»",
         "opts": ["تَذَكَّرُونَ", "تَعْقِلُونَ", "تُفْلِحُونَ", "تَشْكُرُونَ"], "ans": 1, "exp": "(يوسف: ٢)."},
        {"q": "وُصِف الشيطان في خاتمة آيات يوسف بأنه للإنسان؟",
         "opts": ["عَدُوٌّ مُّبِينٌ", "خَصْمٌ لَدُودٌ", "وَلِيٌّ حَمِيمٌ", "قَرِينٌ"], "ans": 0, "exp": "«عَدُوٌّ مُّبِينٌ»."},
        {"q": "أكمل: «وَإِن كُنتَ مِن قَبْلِهِ لَمِنَ ...»",
         "opts": ["الْغَافِلِينَ", "الْخَاسِرِينَ", "النَّادِمِينَ", "الْجَاهِلِينَ"], "ans": 0, "exp": "(يوسف: ٣)."},
    ],
    "adab": [
        {"q": "قصيدة «قارئة الفنجان» لأي شاعر؟",
         "opts": ["أحمد مطر", "نزار قباني", "بدر شاكر السياب", "عبد الرزاق عبد الواحد"], "ans": 1, "exp": "نزار قباني."},
        {"q": "«الزائر الأخير» من شعر؟",
         "opts": ["عبد الرزاق عبد الواحد", "نزار قباني", "السياب", "أحمد مطر"], "ans": 0, "exp": "عبد الرزاق عبد الواحد."},
        {"q": "«رسالة إلى يزيد» لأي شاعر؟",
         "opts": ["نزار قباني", "بدر شاكر السياب", "أحمد مطر", "عبد الرزاق عبد الواحد"], "ans": 1, "exp": "السياب."},
        {"q": "«اعتذار (فوق نعلي)» لأي شاعر؟",
         "opts": ["أحمد مطر", "نزار قباني", "السياب", "المتنبي"], "ans": 0, "exp": "أحمد مطر."},
        {"q": "أي شاعر له قصيدتان ضمن الملزمة؟",
         "opts": ["السياب", "أحمد مطر", "نزار قباني", "عبد الرزاق عبد الواحد"], "ans": 2, "exp": "نزار قباني."},
        {"q": "بدر شاكر السياب من رواد؟",
         "opts": ["الشعر العمودي", "الشعر الحر (التفعيلة)", "الموشحات", "المعلقات"], "ans": 1, "exp": "الشعر الحر."},
        {"q": "أيّ قصيدة غنّاها عبد الحليم حافظ؟",
         "opts": ["أين أذهب", "الزائر الأخير", "قارئة الفنجان", "رسالة إلى يزيد"], "ans": 2, "exp": "قارئة الفنجان."},
        {"q": "قصيدة «أين أذهب» لأي شاعر؟",
         "opts": ["نزار قباني", "أحمد مطر", "السياب", "عبد الرزاق عبد الواحد"], "ans": 0, "exp": "نزار قباني."},
        {"q": "ما جنسية نزار قباني؟", "opts": ["عراقي", "سوري", "مصري", "لبناني"], "ans": 1, "exp": "سوري."},
        {"q": "الشاعر صاحب «اللافتات» الساخرة؟",
         "opts": ["السياب", "أحمد مطر", "نزار قباني", "عبد الرزاق عبد الواحد"], "ans": 1, "exp": "أحمد مطر."},
        {"q": "عبد الرزاق عبد الواحد شاعر؟", "opts": ["مصري", "سوري", "عراقي", "سعودي"], "ans": 2, "exp": "عراقي."},
        {"q": "في أي عام تُوفّي السياب؟", "opts": ["١٩٥٤", "١٩٦٤", "١٩٧٤", "١٩٨٤"], "ans": 1, "exp": "١٩٦٤."},
    ],
    "qawaid": [
        {"q": "«نجحَ الطالبُ» — إعراب «الطالبُ»؟",
         "opts": ["مفعول به", "فاعل مرفوع", "حال", "مبتدأ"], "ans": 1, "exp": "فاعل مرفوع بالضمة."},
        {"q": "«قرأَ محمدٌ الكتابَ» — «الكتابَ»؟",
         "opts": ["فاعل", "مفعول مطلق", "مفعول به منصوب", "حال"], "ans": 2, "exp": "مفعول به منصوب بالفتحة."},
        {"q": "مصدرٌ منصوب يُذكر بعد فعلٍ من لفظه لتوكيده؟",
         "opts": ["الحال", "المفعول المطلق", "المفعول به", "الفاعل"], "ans": 1, "exp": "المفعول المطلق."},
        {"q": "«عادَ الجنديُّ منتصرًا» — «منتصرًا»؟",
         "opts": ["مفعول به", "حال منصوب", "فاعل", "مفعول مطلق"], "ans": 1, "exp": "حال منصوب."},
        {"q": "«فرِحَ الطفلُ فرحًا» — «فرحًا»؟",
         "opts": ["مفعول مطلق", "حال", "مفعول به", "تمييز"], "ans": 0, "exp": "مفعول مطلق للتوكيد."},
        {"q": "الفعل «اُكْتُبْ» نوعه؟", "opts": ["ماضٍ", "مضارع", "أمر", "مصدر"], "ans": 2, "exp": "أمر."},
        {"q": "علامة نصب المفعول به في «شربتُ الماءَ»؟",
         "opts": ["الضمة", "الكسرة", "الفتحة", "السكون"], "ans": 2, "exp": "الفتحة."},
        {"q": "الحال يأتي غالبًا...؟",
         "opts": ["معرفة وصاحبه نكرة", "نكرة وصاحبه معرفة", "معرفة وصاحبه معرفة", "نكرة وصاحبه نكرة"], "ans": 1, "exp": "نكرة وصاحبه معرفة."},
        {"q": "الفعل كلمةٌ تدلُّ على؟",
         "opts": ["ذاتٍ فقط", "حدثٍ مقترنٍ بزمن", "صفةٍ ثابتة", "مكان"], "ans": 1, "exp": "حدثٌ مقترنٌ بزمن."},
        {"q": "أيٌّ ليس من أنواع الفعل؟",
         "opts": ["الماضي", "المضارع", "الأمر", "المصدر"], "ans": 3, "exp": "المصدر اسمٌ لا فعل."},
        {"q": "«دُرتُ دورتين» — «دورتين» لبيان؟",
         "opts": ["التوكيد", "النوع", "العدد", "الزمان"], "ans": 2, "exp": "العدد."},
        {"q": "«سارَ سيرًا حثيثًا» — لبيان؟",
         "opts": ["العدد", "النوع", "التوكيد", "المكان"], "ans": 1, "exp": "النوع."},
        {"q": "الفعل «يكتبُ» نوعه؟", "opts": ["ماضٍ", "مضارع", "أمر", "مصدر"], "ans": 1, "exp": "مضارع."},
    ],
    "imla": [
        {"q": "علامة بين جملتين الثانية سببٌ/نتيجة للأولى؟",
         "opts": ["الفاصلة (،)", "الفاصلة المنقوطة (؛)", "النقطتان (:)", "الشرطة (—)"], "ans": 1, "exp": "الفاصلة المنقوطة."},
        {"q": "النقطتان (:) تُستعملان قبل؟",
         "opts": ["نهاية الجملة", "القول المنقول والتعداد", "السؤال", "التعجّب"], "ans": 1, "exp": "القول المنقول والتعداد."},
        {"q": "الصواب في المكاتبات؟",
         "opts": ["إلحاقًا بكتابكم", "لاحقًا لكتابكم", "الاثنان", "لا شيء"], "ans": 1, "exp": "«لاحقًا» تعني تابعًا."},
        {"q": "الصواب؟", "opts": ["على ضوء المذكرة", "في ضوء المذكرة", "الاثنان", "حول المذكرة"], "ans": 1, "exp": "«في ضوء»."},
        {"q": "«المذكور أعلاه» يُستبدل بـ؟",
         "opts": ["المذكور آنفًا", "المذكور تحته", "المذكور خلفه", "لا تغيير"], "ans": 0, "exp": "«آنفًا»."},
        {"q": "علامة الترقيم بعد «ما أجملَ السماءَ»؟",
         "opts": ["نقطة (.)", "استفهام (؟)", "تعجّب (!)", "فاصلة (،)"], "ans": 2, "exp": "علامة التعجّب."},
        {"q": "الأقواس المزخرفة ﴿ ﴾ لحصر؟",
         "opts": ["الحوار", "الآيات القرآنية", "الكلام المعترض", "العناوين"], "ans": 1, "exp": "الآيات القرآنية."},
        {"q": "النقطة (.) تُوضع في؟",
         "opts": ["وسط الجملة", "نهاية الجملة التامّة", "بعد السؤال", "قبل التعداد"], "ans": 1, "exp": "نهاية الجملة التامّة."},
        {"q": "علامة الاستفهام (؟) بعد؟",
         "opts": ["الخبرية", "الاستفهامية", "التعجّب", "القول المنقول"], "ans": 1, "exp": "الجملة الاستفهامية."},
        {"q": "علامتا التنصيص « » لـ؟",
         "opts": ["حصر الكلام المنقول", "التعجّب", "التعداد", "الحذف"], "ans": 0, "exp": "حصر الكلام المنقول بنصّه."},
        {"q": "القوسان المعقوفان [ ] لـ؟",
         "opts": ["الآيات", "ما يضيفه الناقل للنص", "الحوار", "السؤال"], "ans": 1, "exp": "ما يضيفه الناقل."},
        {"q": "سبب خطأ بدء الخطاب بـ«كتابكم...»؟",
         "opts": ["مبتدأ لا خبر له", "فعل ناقص", "حال غير منصوب", "لا خطأ"], "ans": 0, "exp": "مبتدأ بلا خبر."},
        {"q": "الشرطة (—) في الحوار تدلُّ على؟",
         "opts": ["نهاية الكلام", "المتكلّم", "السؤال", "التعجّب"], "ans": 1, "exp": "المتكلّم في الحوار."},
    ],
}
ARABIC_NAMES = {"quran": "القرآن الكريم", "adab": "الأدب", "qawaid": "القواعد", "imla": "الإملاء"}


# ============================================================
#        بنك أسئلة البرمجة C++ (من النماذج A–F)
#   MCQ: (نص، خيارات، رقم الصحيح، شرح) | TF: (نص، صحيح؟، شرح)
# ============================================================
EN_MODELS = {
    "A": {"mcq": [
        ("Which language was developed in 1983?", ["Java", "Pascal", "C++", "COBOL"], 2, "C++ was named in 1983 (Stroustrup)."),
        ("Which phase combines object code with library functions?", ["Loading", "Linking", "Editing", "CPU Execution"], 1, "The linker builds the executable."),
        ("Which symbol is used for decision making in flowcharts?", ["Rectangle", "Diamond", "Circle", "Oval"], 1, "Diamond = condition (Yes/No)."),
        ("Which file extension is used for C++ source files?", [".exe", ".cpp", ".txt", ".com"], 1, "C++ sources use .cpp."),
        ("Which of the following is software?", ["Mouse", "Keyboard", "Operating System", "Printer"], 2, "The OS is software."),
    ], "tf": [
        ("Algorithms must have finite steps.", True, "Finiteness is a core property."),
        ("Flowcharts are graphical representations of algorithms.", True, "Standard symbols depict an algorithm."),
        ("C++ supports object-oriented programming.", True, "Classes, inheritance, polymorphism."),
        ("Compilation occurs after linking.", False, "Compilation comes before linking."),
        ("Hardware means computer programs.", False, "Hardware = physical; software = programs."),
    ]},
    "B": {"mcq": [
        ("Who developed C++?", ["Dennis Ritchie", "Bjarne Stroustrup", "Bill Gates", "Charles Babbage"], 1, "Stroustrup at Bell Labs."),
        ("Which phase loads the program into memory?", ["Loader", "Compiler", "Editor", "Linker"], 0, "The loader transfers it into memory."),
        ("Which symbol represents input/output in a flowchart?", ["Diamond", "Oval", "Parallelogram", "Rectangle"], 2, "Parallelogram = I/O."),
        ("Which language appeared before C language?", ["Java", "Python", "Pascal", "Algol"], 3, "Algol (1958) predates C."),
        ("Which one is hardware?", ["Windows", "MS Word", "Monitor", "Compiler"], 2, "A monitor is hardware."),
    ], "tf": [
        ("Programming is writing instructions for a computer.", True, "That is the definition."),
        ("Flowcharts use symbols to represent steps.", True, "Geometric symbols per step."),
        ("C++ is only a structured programming language.", False, "C++ is multi-paradigm."),
        ("Algorithms should be clear and unambiguous.", True, "Definiteness is key."),
        ("The CPU executes programs in memory.", True, "Fetch & execute from memory."),
    ]},
    "C": {"mcq": [
        ("Which stage comes before compilation?", ["Linking", "Loading", "Pre-processing", "Execution"], 2, "Pre-processing handles directives first."),
        ("Which symbol represents processing in a flowchart?", ["Rectangle", "Diamond", "Oval", "Circle"], 0, "Rectangle = process."),
        ("Which language is the base for C++?", ["Java", "C", "Python", "BASIC"], 1, "C++ built on C."),
        ("Which of the following is an example of software?", ["Scanner", "Speaker", "Compiler", "Keyboard"], 2, "A compiler is software."),
        ("Which property means every algorithm step must be clear?", ["Effectiveness", "Speed", "Non-ambiguity", "Complexity"], 2, "Non-ambiguity = each step clear."),
    ], "tf": [
        ("Flowcharts help in understanding algorithms.", True, "Visuals ease the logic."),
        ("Linking converts source code to object code.", False, "Compilation does; linking merges libraries."),
        ("C++ supports templates.", True, "Templates enable generic programming."),
        ("Hardware refers to physical computer components.", True, "Tangible machinery."),
        ("Algorithms may continue forever without stopping.", False, "They must terminate."),
    ]},
    "D": {"mcq": [
        ("Which of the following is a programming language?", ["RAM", "CPU", "C++", "Hard Disk"], 2, "C++ is a language."),
        ("Which symbol is used for start and stop in flowcharts?", ["Oval", "Rectangle", "Diamond", "Arrow"], 0, "Oval = terminator."),
        ("Which stage produces executable code?", ["Editing", "Linking", "Reading", "Printing"], 1, "Linking builds the executable."),
        ("Which language was developed in 1991?", ["Java", "C", "Pascal", "BASIC"], 0, "Java began in 1991 (Oak)."),
        ("Which one is an algorithm property?", ["Decoration", "Finiteness", "Animation", "Compilation"], 1, "Finiteness."),
    ], "tf": [
        ("C++ is widely used in programming applications.", True, "Systems, games, embedded."),
        ("Flowcharts cannot represent decisions.", False, "The diamond represents decisions."),
        ("Software means computer programs.", True, "Programs and instructions."),
        ("Algorithms solve problems step by step.", True, "Ordered procedure."),
        ("Editing is the final stage of PDP.", False, "Editing is first; execution is last."),
    ]},
    "E": {"mcq": [
        ("Which stage checks and corrects source code?", ["Editing", "Loading", "Execution", "Linking"], 0, "Editing = write & correct."),
        ("Which symbol is used for mathematical processing?", ["Rectangle", "Oval", "Diamond", "Circle"], 0, "Rectangle = processing."),
        ("Which of the following is not hardware?", ["Mouse", "Printer", "Monitor", "Compiler"], 3, "A compiler is software."),
        ("Which language came after C?", ["Pascal", "C++", "BASIC", "COBOL"], 1, "C++ came after C."),
        ("Which phase executes the program?", ["CPU", "Compiler", "Linker", "Editor"], 0, "The CPU executes instructions."),
    ], "tf": [
        ("Algorithms should solve problems effectively.", True, "Effectiveness is required."),
        ("C++ was derived from C language.", True, "C++ extends C."),
        ("Input/output symbols are used in flowcharts.", True, "Parallelogram = I/O."),
        ("The linker loads programs into memory.", False, "The loader does; linker merges libraries."),
        ("Programs are stored with .cpp extension.", True, "C++ sources use .cpp."),
    ]},
    "F": {"mcq": [
        ("Which phase comes after compilation?", ["Editing", "Linking", "Input", "Output"], 1, "Linking follows compilation."),
        ("Which symbol is used for input/output operations?", ["Rectangle", "Oval", "Parallelogram", "Diamond"], 2, "Parallelogram = I/O."),
        ("Which one is considered hardware?", ["Compiler", "Keyboard", "Windows", "Antivirus"], 1, "A keyboard is hardware."),
        ("Which language is object-oriented?", ["C++", "Assembly", "Machine Language", "HTML"], 0, "C++ supports OOP."),
        ("Which property means the algorithm should finish?", ["Complexity", "Non-ambiguity", "Finiteness", "Flexibility"], 2, "Finiteness = it must terminate."),
    ], "tf": [
        ("C++ supports structured programming.", True, "Structured and OOP."),
        ("Flowcharts are difficult to understand visually.", False, "They are designed to be easy."),
        ("Algorithms are step-by-step procedures.", True, "Ordered sequence of steps."),
        ("Loading places the program into memory.", True, "The loader transfers the executable."),
        ("Hardware refers to physical devices.", True, "The tangible part."),
    ]},
}

AR_MODELS = {
    "A": {"mcq": [
        ("أي لغة طُوّرت عام 1983؟", ["Java", "Pascal", "C++", "COBOL"], 2, "اعتُمد اسم C++ عام 1983."),
        ("أي مرحلة تدمج الشيفرة الكائنية مع دوال المكتبات؟", ["Loading", "Linking", "Editing", "CPU Execution"], 1, "الرابط يُنتج الملف التنفيذي."),
        ("أي رمز يُستخدم لاتخاذ القرار في المخططات؟", ["Rectangle", "Diamond", "Circle", "Oval"], 1, "المعيّن = شرط بفرعين."),
        ("أي امتداد يُستخدم لملفات C++ المصدرية؟", [".exe", ".cpp", ".txt", ".com"], 1, "الامتداد .cpp."),
        ("أي مما يلي يُعدّ برمجية؟", ["Mouse", "Keyboard", "Operating System", "Printer"], 2, "نظام التشغيل برمجية."),
    ], "tf": [
        ("يجب أن تتكوّن الخوارزمية من خطوات محدودة.", True, "المحدودية خاصية أساسية."),
        ("المخططات الانسيابية تمثيل رسومي للخوارزميات.", True, "ترموز قياسية تمثّل الخوارزمية."),
        ("لغة C++ تدعم البرمجة الكائنية.", True, "أصناف ووراثة وتعدد أشكال."),
        ("الترجمة تحدث بعد الربط.", False, "الترجمة تسبق الربط."),
        ("العتاد يعني برامج الحاسوب.", False, "العتاد مادي، والبرامج برمجيات."),
    ]},
    "B": {"mcq": [
        ("من طوّر لغة C++؟", ["Dennis Ritchie", "Bjarne Stroustrup", "Bill Gates", "Charles Babbage"], 1, "بيارن ستروستروب."),
        ("أي مرحلة تحمّل البرنامج إلى الذاكرة؟", ["Loader", "Compiler", "Editor", "Linker"], 0, "المُحمِّل ينقل الملف التنفيذي."),
        ("أي رمز يمثّل الإدخال/الإخراج؟", ["Diamond", "Oval", "Parallelogram", "Rectangle"], 2, "متوازي الأضلاع = إدخال/إخراج."),
        ("أي لغة ظهرت قبل لغة C؟", ["Java", "Python", "Pascal", "Algol"], 3, "Algol (1958) تسبق C."),
        ("أي مما يلي يُعدّ عتادًا؟", ["Windows", "MS Word", "Monitor", "Compiler"], 2, "الشاشة جهاز مادي."),
    ], "tf": [
        ("البرمجة هي كتابة تعليمات للحاسوب.", True, "هذا تعريف البرمجة."),
        ("تستخدم المخططات رموزًا لتمثيل الخطوات.", True, "رموز هندسية لكل خطوة."),
        ("C++ لغة هيكلية فقط.", False, "C++ متعددة الأنماط."),
        ("يجب أن تكون الخوارزمية واضحة وغير غامضة.", True, "الوضوح خاصية أساسية."),
        ("المعالج ينفّذ البرامج في الذاكرة.", True, "يجلب التعليمات وينفّذها."),
    ]},
    "C": {"mcq": [
        ("أي مرحلة تسبق الترجمة؟", ["Linking", "Loading", "Pre-processing", "Execution"], 2, "المعالجة المسبقة تسبق الترجمة."),
        ("أي رمز يمثّل المعالجة؟", ["Rectangle", "Diamond", "Oval", "Circle"], 0, "المستطيل = معالجة."),
        ("ما اللغة الأساس للغة C++؟", ["Java", "C", "Python", "BASIC"], 1, "بُنيت على C."),
        ("أي مما يلي مثال على برمجية؟", ["Scanner", "Speaker", "Compiler", "Keyboard"], 2, "المترجم برمجية."),
        ("أي خاصية تعني وضوح كل خطوة؟", ["Effectiveness", "Speed", "Non-ambiguity", "Complexity"], 2, "عدم الغموض."),
    ], "tf": [
        ("المخططات تساعد على فهم الخوارزميات.", True, "التمثيل الرسومي يسهّل المنطق."),
        ("الربط يحوّل الشيفرة المصدرية إلى كائنية.", False, "الترجمة تفعل ذلك؛ الربط يدمج المكتبات."),
        ("C++ تدعم القوالب.", True, "القوالب تتيح البرمجة العامة."),
        ("العتاد يشير إلى المكونات المادية.", True, "الجزء الملموس."),
        ("قد تستمر الخوارزمية للأبد دون توقّف.", False, "يجب أن تكون محدودة."),
    ]},
    "D": {"mcq": [
        ("أي مما يلي لغة برمجة؟", ["RAM", "CPU", "C++", "Hard Disk"], 2, "C++ لغة برمجة."),
        ("أي رمز يُستخدم للبداية والنهاية؟", ["Oval", "Rectangle", "Diamond", "Arrow"], 0, "البيضوي = بداية/نهاية."),
        ("أي مرحلة تنتج الشيفرة التنفيذية؟", ["Editing", "Linking", "Reading", "Printing"], 1, "الربط يُنتج التنفيذي."),
        ("أي لغة طُوّرت عام 1991؟", ["Java", "C", "Pascal", "BASIC"], 0, "Java بدأت 1991."),
        ("أي مما يلي خاصية من خصائص الخوارزمية؟", ["Decoration", "Finiteness", "Animation", "Compilation"], 1, "المحدودية."),
    ], "tf": [
        ("تُستخدم C++ على نطاق واسع.", True, "أنظمة وألعاب وأنظمة مضمّنة."),
        ("لا تستطيع المخططات تمثيل القرارات.", False, "المعيّن يمثّل القرارات."),
        ("البرمجيات تعني برامج الحاسوب.", True, "البرامج والتعليمات."),
        ("تحلّ الخوارزميات المشكلات خطوة بخطوة.", True, "إجراء مرتّب."),
        ("التحرير هو المرحلة الأخيرة في PDP.", False, "التحرير أول، والتنفيذ آخر."),
    ]},
    "E": {"mcq": [
        ("أي مرحلة تفحص الشيفرة المصدرية وتصحّحها؟", ["Editing", "Loading", "Execution", "Linking"], 0, "التحرير = كتابة وتصحيح."),
        ("أي رمز يُستخدم للمعالجة الرياضية؟", ["Rectangle", "Oval", "Diamond", "Circle"], 0, "المستطيل = معالجة."),
        ("أي مما يلي ليس عتادًا؟", ["Mouse", "Printer", "Monitor", "Compiler"], 3, "المترجم برمجية."),
        ("أي لغة جاءت بعد C؟", ["Pascal", "C++", "BASIC", "COBOL"], 1, "C++ بعد C."),
        ("أي مرحلة تنفّذ البرنامج؟", ["CPU", "Compiler", "Linker", "Editor"], 0, "المعالج ينفّذ."),
    ], "tf": [
        ("يجب أن تحلّ الخوارزميات المشكلات بفعّالية.", True, "الفعّالية مطلوبة."),
        ("اشتُقّت C++ من لغة C.", True, "C++ امتداد لـ C."),
        ("تُستخدم رموز الإدخال/الإخراج في المخططات.", True, "متوازي الأضلاع."),
        ("الرابط يحمّل البرامج إلى الذاكرة.", False, "المُحمِّل يفعل؛ الرابط يدمج المكتبات."),
        ("تُخزّن البرامج بالامتداد .cpp.", True, "ملفات C++ المصدرية."),
    ]},
    "F": {"mcq": [
        ("أي مرحلة تأتي بعد الترجمة؟", ["Editing", "Linking", "Input", "Output"], 1, "الربط بعد الترجمة."),
        ("أي رمز يُستخدم لعمليات الإدخال/الإخراج؟", ["Rectangle", "Oval", "Parallelogram", "Diamond"], 2, "متوازي الأضلاع."),
        ("أي مما يلي يُعدّ عتادًا؟", ["Compiler", "Keyboard", "Windows", "Antivirus"], 1, "لوحة المفاتيح جهاز مادي."),
        ("أي لغة كائنية التوجّه؟", ["C++", "Assembly", "Machine Language", "HTML"], 0, "C++ تدعم الكائنية."),
        ("أي خاصية تعني وجوب انتهاء الخوارزمية؟", ["Complexity", "Non-ambiguity", "Finiteness", "Flexibility"], 2, "المحدودية."),
    ], "tf": [
        ("C++ تدعم البرمجة الهيكلية.", True, "الهيكلية والكائنية."),
        ("يصعب فهم المخططات بصريًا.", False, "صُمّمت لتكون سهلة الفهم."),
        ("الخوارزميات إجراءات خطوة بخطوة.", True, "سلسلة مرتّبة."),
        ("التحميل يضع البرنامج في الذاكرة.", True, "المُحمِّل ينقل الملف التنفيذي."),
        ("العتاد يشير إلى الأجهزة المادية.", True, "الجزء الملموس."),
    ]},
}


# أسئلة محوّلة من السؤالين الثالث (المخطط/الكود) والرابع (المقالي) لكل نموذج
EN_EXTRA = {
    "A": [
        ("In the 'greater of two numbers' flowchart, which symbol holds 'A > B ?'", ["Rectangle", "Diamond", "Parallelogram", "Oval"], 1, "A decision uses the diamond."),
        ("What is the correct order of the Program Development Process (PDP)?",
         ["Compilation → Editing → Linking → Execution", "Editing → Pre-processing → Compilation → Linking → Loading → Execution",
          "Loading → Linking → Compilation → Editing", "Editing → Linking → Compilation → Loading"], 1, "Edit → Pre-process → Compile → Link → Load → Execute."),
        ("Which PDP stage places the executable into RAM?", ["Editing", "Compilation", "Loading", "Linking"], 2, "Loading places it into memory."),
    ],
    "B": [
        ("Correct formula for the area of a triangle?", ["base * height", "0.5 * base * height", "2 * (base + height)", "base * base"], 1, "Area = ½ · base · height."),
        ("How many inputs may an algorithm accept?", ["exactly one", "zero or more", "at least two", "none"], 1, "Zero or more inputs."),
        ("An algorithm is best defined as...?", ["a random list of steps", "a finite sequence of well-defined ordered steps", "a hardware device", "a type of compiler"], 1, "Finite, well-defined, ordered steps."),
    ],
    "C": [
        ("Which condition tests whether a number is even?", ["number / 2 == 0", "number % 2 == 0", "number * 2 == 0", "number % 2 == 1"], 1, "Remainder by 2 equals zero."),
        ("Which set is entirely hardware?", ["OS, compilers, apps", "CPU, RAM, keyboard, monitor", "Word, Excel, Windows", "compiler, loader, linker"], 1, "All are physical components."),
        ("Software is best described as...?", ["physical, tangible parts", "programs and instructions (intangible)", "the power supply", "the monitor"], 1, "Programs/instructions, intangible."),
    ],
    "D": [
        ("Which expression computes the square of a number?", ["number + number", "number * number", "number / 2", "2 * number"], 1, "n × n."),
        ("Which is a benefit of flowcharts?", ["increases code size", "clear visualization of the logic", "replaces the CPU", "compiles the program"], 1, "They clarify the logic & aid design."),
        ("Flowcharts are ___ of the programming language.", ["dependent on one language", "independent (language-independent)", "only for C++", "only for Java"], 1, "Language-independent."),
    ],
    "E": [
        ("Correct formula for the perimeter of a rectangle?", ["length * width", "2 * (length + width)", "0.5 * length * width", "length + width"], 1, "P = 2(length + width)."),
        ("Which symbol marks Start and End?", ["Rectangle", "Diamond", "Oval", "Parallelogram"], 2, "The oval (terminator)."),
        ("The flow line (arrow) in a flowchart shows...?", ["a decision", "the direction of flow", "input/output", "a process"], 1, "Direction of flow."),
    ],
    "F": [
        ("When averaging three numbers, why divide by 3.0 (not 3)?", ["to round the result", "to force floating-point division", "to make it faster", "no reason"], 1, "3.0 ensures floating-point division."),
        ("Which is a reason C++ became popular?", ["it has no libraries", "high performance and multi-paradigm", "it cannot reuse C code", "it runs only on Windows"], 1, "Performance, multi-paradigm, portability, STL."),
        ("In C++, the STL refers to...?", ["Simple Text Language", "Standard Template Library", "System Transfer Layer", "Static Type Linker"], 1, "The rich Standard Template Library."),
    ],
}
AR_EXTRA = {
    "A": [
        ("في مخطط «العدد الأكبر»، أي رمز يحوي الشرط «A > B ؟»", ["Rectangle", "Diamond", "Parallelogram", "Oval"], 1, "القرار يُمثَّل بالمعيّن."),
        ("ما الترتيب الصحيح لمراحل تطوير البرنامج (PDP)؟",
         ["الترجمة ← التحرير ← الربط ← التنفيذ", "التحرير ← المعالجة المسبقة ← الترجمة ← الربط ← التحميل ← التنفيذ",
          "التحميل ← الربط ← الترجمة ← التحرير", "التحرير ← الربط ← الترجمة ← التحميل"], 1, "تحرير ← معالجة ← ترجمة ← ربط ← تحميل ← تنفيذ."),
        ("أي مرحلة تضع الملف التنفيذي في الذاكرة (RAM)؟", ["التحرير", "الترجمة", "التحميل", "الربط"], 2, "التحميل ينقله للذاكرة."),
    ],
    "B": [
        ("ما الصيغة الصحيحة لمساحة المثلث؟", ["base * height", "0.5 * base * height", "2 * (base + height)", "base * base"], 1, "المساحة = ½ × القاعدة × الارتفاع."),
        ("كم مدخلًا قد تستقبل الخوارزمية؟", ["مدخلًا واحدًا فقط", "صفرًا أو أكثر", "مدخلين على الأقل", "لا شيء"], 1, "صفر أو أكثر."),
        ("أفضل تعريف للخوارزمية؟", ["قائمة عشوائية من الخطوات", "سلسلة محدودة من الخطوات المرتّبة المحدّدة", "جهاز مادي", "نوع من المترجمات"], 1, "خطوات محدودة ومرتّبة ومحدّدة."),
    ],
    "C": [
        ("أي شرط يفحص أن العدد زوجي؟", ["number / 2 == 0", "number % 2 == 0", "number * 2 == 0", "number % 2 == 1"], 1, "باقي القسمة على 2 يساوي صفرًا."),
        ("أي مجموعة كلّها عتاد؟", ["نظام التشغيل، المترجمات، التطبيقات", "CPU، RAM، لوحة المفاتيح، الشاشة", "Word، Excel، Windows", "المترجم، المُحمِّل، الرابط"], 1, "كلها مكوّنات مادية."),
        ("أفضل وصف للبرمجيات؟", ["مكوّنات مادية ملموسة", "برامج وتعليمات (غير ملموسة)", "مزوّد الطاقة", "الشاشة"], 1, "برامج وتعليمات غير ملموسة."),
    ],
    "D": [
        ("أي تعبير يحسب مربّع العدد؟", ["number + number", "number * number", "number / 2", "2 * number"], 1, "العدد × العدد."),
        ("أي مما يلي فائدة للمخططات الانسيابية؟", ["زيادة حجم الكود", "تمثيل واضح للمنطق", "تستبدل المعالج", "تترجم البرنامج"], 1, "توضّح المنطق وتعين على التصميم."),
        ("المخططات الانسيابية ___ عن لغة البرمجة.", ["معتمدة على لغة واحدة", "مستقلّة (غير معتمدة على لغة)", "خاصة بـ C++ فقط", "خاصة بـ Java فقط"], 1, "مستقلّة عن اللغة."),
    ],
    "E": [
        ("ما الصيغة الصحيحة لمحيط المستطيل؟", ["length * width", "2 * (length + width)", "0.5 * length * width", "length + width"], 1, "المحيط = 2 × (الطول + العرض)."),
        ("أي رمز يحدّد البداية والنهاية؟", ["Rectangle", "Diamond", "Oval", "Parallelogram"], 2, "البيضوي (Terminator)."),
        ("خط التدفّق (السهم) في المخطط يدلّ على...؟", ["قرار", "اتجاه الانسياب", "إدخال/إخراج", "معالجة"], 1, "اتجاه الانسياب."),
    ],
    "F": [
        ("عند حساب معدّل ثلاثة أعداد، لماذا نقسم على 3.0 لا 3؟", ["لتقريب الناتج", "لضمان القسمة العشرية (floating-point)", "لجعلها أسرع", "لا سبب"], 1, "3.0 تضمن القسمة العشرية."),
        ("أي مما يلي سبب لشيوع C++؟", ["لا تملك مكتبات", "أداء عالٍ وتعدد أنماط", "لا يمكنها إعادة استخدام كود C", "تعمل على Windows فقط"], 1, "أداء، تعدد أنماط، قابلية نقل، STL."),
        ("في C++ تشير STL إلى...؟", ["Simple Text Language", "Standard Template Library", "System Transfer Layer", "Static Type Linker"], 1, "المكتبة القياسية الغنية (STL)."),
    ],
}


def _expand(models, label, tf_opts, extra=None):
    out = []
    extra = extra or {}
    for mk in ("A", "B", "C", "D", "E", "F"):
        m = models[mk]
        for stem, opts, ans, exp in m["mcq"]:
            out.append({"q": f"[نموذج {mk}] {stem}", "opts": opts, "ans": ans, "exp": exp, "_label": label})
        for stem, is_true, exp in m["tf"]:
            out.append({"q": f"[نموذج {mk}] {stem}", "opts": list(tf_opts),
                        "ans": 0 if is_true else 1, "exp": exp, "_label": label})
        for stem, opts, ans, exp in extra.get(mk, []):
            out.append({"q": f"[نموذج {mk}] {stem}", "opts": opts, "ans": ans, "exp": exp, "_label": label})
    return out


CPP_EN = _expand(EN_MODELS, "C++ (English)", ("True", "False"), EN_EXTRA)
CPP_AR = _expand(AR_MODELS, "C++ (عربي)", ("صح", "خطأ"), AR_EXTRA)


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


def update_board(board, user_id, name, score, total, label) -> bool:
    pct = round(score / total * 100)
    uid = str(user_id)
    prev = board.get(uid)
    if prev is None or pct > prev["pct"] or (pct == prev["pct"] and score > prev["score"]):
        board[uid] = {"name": name, "score": score, "total": total, "pct": pct, "label": label}
        return True
    board[uid]["name"] = name
    return False


def board_text(board, highlight_uid=None) -> str:
    ranking = sorted(board.items(), key=lambda kv: (kv[1]["pct"], kv[1]["score"]), reverse=True)
    if not ranking:
        return "🏆 <b>لوحة الصدارة</b>\n\nلا توجد نتائج بعد — كن أول المتصدّرين!"
    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 <b>لوحة الصدارة — أفضل النتائج</b>\n"]
    shown = [u for u, _ in ranking[:TOP_N]]
    for i, (uid, e) in enumerate(ranking[:TOP_N]):
        rank = medals[i] if i < 3 else f"{i + 1}."
        star = " 👈" if uid == highlight_uid else ""
        lab = f" · {e.get('label', '')}" if e.get("label") else ""
        lines.append(f"{rank} {e['name']} — {e['pct']}% ({e['score']}/{e['total']}){lab}{star}")
    if highlight_uid and highlight_uid not in shown:
        for i, (uid, e) in enumerate(ranking):
            if uid == highlight_uid:
                lines.append(f"\nترتيبك: {i + 1}. {e['name']} — {e['pct']}% ({e['score']}/{e['total']})")
                break
    return "\n".join(lines)


# ============================================================
#                       القوائم
# ============================================================
def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📗 اللغة العربية", callback_data="s|arabic")],
        [InlineKeyboardButton("💻 البرمجة C++", callback_data="s|cpp")],
        [InlineKeyboardButton("🏆 لوحة الصدارة", callback_data="board")],
    ])


def sub_menu(subject) -> InlineKeyboardMarkup:
    if subject == "arabic":
        rows = [
            [InlineKeyboardButton("📚 اختبار شامل", callback_data="q|arabic|all")],
            [InlineKeyboardButton("🕌 القرآن", callback_data="q|arabic|quran"),
             InlineKeyboardButton("📜 الأدب", callback_data="q|arabic|adab")],
            [InlineKeyboardButton("📝 القواعد", callback_data="q|arabic|qawaid"),
             InlineKeyboardButton("✒️ الإملاء", callback_data="q|arabic|imla")],
        ]
    else:
        rows = [
            [InlineKeyboardButton("📘 شامل — عربي", callback_data="q|cpp|ar")],
            [InlineKeyboardButton("📗 Comprehensive — English", callback_data="q|cpp|en")],
        ]
    rows.append([InlineKeyboardButton("⬅️ رجوع", callback_data="home")])
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🌿 <b>بوت اختبارات الطالب باسم عصيد كمر</b>\n\n"
        f"كل سؤال استفتاء فيه ⏱️ <b>عدّاد {TIME_LIMIT} ثانية</b>، مع تصحيحٍ فوري وشرح، "
        "ولوحة صدارةٍ بين الزملاء.\n\nاختر المادة 👇"
    )
    target = update.message or update.callback_query.message
    await target.reply_text(text, reply_markup=main_menu(), parse_mode=ParseMode.HTML)
    if update.message:
        u = update.effective_user
        who = u.first_name or "طالب"
        if u.username:
            who += f" (@{u.username})"
        await notify_admin(context, f"🔔 بدأ الطالب {who} الاختبار الآن.")


async def on_subject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    subject = query.data.split("|", 1)[1]
    title = "اللغة العربية" if subject == "arabic" else "البرمجة C++"
    await query.edit_message_text(f"اختر نوع اختبار <b>{title}</b> 👇",
                                  reply_markup=sub_menu(subject), parse_mode=ParseMode.HTML)


def build_quiz(subject, mode):
    if subject == "arabic":
        if mode == "all":
            items = [dict(q, _label=ARABIC_NAMES[sec]) for sec, qs in ARABIC.items() for q in qs]
        else:
            items = [dict(q, _label=ARABIC_NAMES[mode]) for q in ARABIC[mode]]
    else:
        pool = CPP_AR if mode == "ar" else CPP_EN
        items = [dict(q) for q in pool]
        if CPP_SAMPLE and 0 < CPP_SAMPLE < len(items):
            items = random.sample(items, CPP_SAMPLE)
    random.shuffle(items)
    return items


def run_meta(subject, mode):
    """يحدّد هل النتيجة تُسجَّل في الصدارة وما عنوانها."""
    if subject == "arabic":
        return (mode == "all", "اللغة العربية (شامل)")
    return (True, "C++ عربي" if mode == "ar" else "C++ English")


async def on_start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, subject, mode = query.data.split("|")
    u = update.effective_user
    ranked, label = run_meta(subject, mode)
    context.user_data.update(
        quiz=build_quiz(subject, mode), idx=0, score=0, ranked=ranked, board_label=label,
        uid=u.id, name=(u.full_name or u.username or "طالب"), chat_id=query.message.chat_id)
    n = len(context.user_data["quiz"])
    await query.edit_message_text(
        f"✅ بدأنا: <b>{label}</b> ({n} سؤالًا)\nأجب قبل انتهاء العدّاد ⏱️ — بالتوفيق! 🍀",
        parse_mode=ParseMode.HTML)
    await send_question(context, query.message.chat_id)


async def send_question(context, chat_id) -> None:
    ud = context.user_data
    quiz, idx = ud["quiz"], ud["idx"]
    q = quiz[idx]
    qtext = f"({idx + 1}/{len(quiz)}) [{q['_label']}]\n{q['q']}"
    msg = await context.bot.send_poll(
        chat_id=chat_id, question=qtext, options=q["opts"], type="quiz",
        correct_option_id=q["ans"], explanation=q["exp"], open_period=TIME_LIMIT, is_anonymous=False)
    ud["poll_id"] = msg.poll.id
    ud["cur_idx"] = idx
    ud["cur_done"] = False
    ud["timer_task"] = asyncio.create_task(poll_timer(context, chat_id, idx))


async def poll_timer(context, chat_id, idx) -> None:
    try:
        await asyncio.sleep(TIME_LIMIT + 2)
    except asyncio.CancelledError:
        return
    ud = context.user_data
    if ud.get("cur_done") or ud.get("idx") != idx:
        return
    ud["cur_done"] = True
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


async def advance(context, chat_id) -> None:
    ud = context.user_data
    if "quiz" not in ud:
        return
    ud["idx"] += 1
    if ud["idx"] < len(ud["quiz"]):
        await send_question(context, chat_id)
    else:
        await finish(context, chat_id)


async def finish(context, chat_id) -> None:
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
    if ud.get("ranked"):
        board = context.bot_data.setdefault("board", load_board())
        is_pb = update_board(board, ud.get("uid", chat_id), ud.get("name", "طالب"),
                             score, total, ud.get("board_label", ""))
        save_board(board)
        record_line = ("\n🎉 رقم قياسي جديد لك في الصدارة!" if is_pb
                       else "\nسُجّلت محاولتك (لم تتجاوز أفضل نتيجة سابقة لك).")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 القائمة الرئيسية", callback_data="home")],
        [InlineKeyboardButton("🏆 لوحة الصدارة", callback_data="board")],
    ])
    await context.bot.send_message(
        chat_id, f"{emoji} <b>انتهى الاختبار</b> — {ud.get('board_label', '')}\n\n"
        f"نتيجتك: <b>{score} / {total}</b>  ({pct}%)\n{note}{record_line}",
        reply_markup=kb, parse_mode=ParseMode.HTML)
    await notify_admin(context, f"✅ أنهى الطالب {ud.get('name', 'طالب')} اختبار "
                                f"{ud.get('board_label', '')}. النتيجة: {score} من {total}.")
    for k in ("quiz", "idx", "score", "cur_done", "timer_task", "poll_id", "cur_idx", "ranked", "board_label"):
        ud.pop(k, None)


async def show_board(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    board = context.bot_data.setdefault("board", load_board())
    uid = str(update.effective_user.id)
    text = board_text(board, highlight_uid=uid)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ القائمة", callback_data="home")]])
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)


async def on_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await start(update, context)


def main() -> None:
    if BOT_TOKEN == "ضع_توكن_البوت_هنا":
        raise SystemExit("⚠️ ضع توكن البوت في BOT_TOKEN قبل التشغيل.")
    app = Application.builder().token(BOT_TOKEN).build()
    app.bot_data["board"] = load_board()
    app.add_handler(CommandHandler(["start", "quiz"], start))
    app.add_handler(CommandHandler("leaderboard", show_board))
    app.add_handler(CallbackQueryHandler(on_subject, pattern=r"^s\|"))
    app.add_handler(CallbackQueryHandler(on_start_quiz, pattern=r"^q\|"))
    app.add_handler(CallbackQueryHandler(show_board, pattern=r"^board$"))
    app.add_handler(CallbackQueryHandler(on_home, pattern=r"^(home|restart)$"))
    app.add_handler(PollAnswerHandler(on_poll_answer))
    print(f"✅ البوت يعمل (مواد متعددة، ⏱️ {TIME_LIMIT}ث/سؤال)... Ctrl+C للإيقاف.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
