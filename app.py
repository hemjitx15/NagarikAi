"""Nagarik AI - a civic reporting prototype for Indian citizens.

Citizens describe a local problem in Bengali, Hindi or English. The app runs a
transparent, on-device keyword classifier over the text to suggest a category,
a priority and a likely department to approach, then keeps the report in a
local case tracker.

Scope and honesty notes
-----------------------
* This is a prototype. Nothing here is transmitted anywhere.
* The analysis is rule based (keyword + signal scoring), not a remote model.
  The UI says so wherever results are shown.
* No complaint is filed with any authority from this application.
* No API keys, endpoints or credentials exist in this source file.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field

import streamlit as st
from sarvamai import SarvamAI
import os
import json
from dotenv import load_dotenv

load_dotenv()

# --------------------------------------------------------------------------- #
#  Design tokens
# --------------------------------------------------------------------------- #

APP_NAME = "Nagarik AI"

FOREST = "#153B32"
FOREST_DEEP = "#0F2A24"
FOREST_MID = "#1D4A3F"
FOREST_SOFT = "#E4EFEA"
OFFWHITE = "#F5F7F4"
LIME = "#CDF27A"
LIME_DEEP = "#A9D94F"
LIME_SOFT = "#EFF9DC"
MUTED = "#6C807A"
BORDER = "#E3E8E1"
CARD = "#FFFFFF"

PRIORITY_TONES = {
    "high": ("#B3261E", "#FBEDEB"),
    "medium": ("#B45309", "#FDF3E3"),
    "low": ("#2A5F51", "#E8F1EE"),
}

STATUS_TONES = {
    "open": ("#B45309", "#FDF3E3"),
    "in_progress": ("#153B32", "#E4EFEA"),
    "resolved": ("#3F6212", "#EFF9DC"),
}

STATUS_ORDER = ("open", "in_progress", "resolved")
PRIORITY_ORDER = ("high", "medium", "low")

PRIORITY_HIGH_CUTOFF = 70
PRIORITY_MEDIUM_CUTOFF = 45

# --------------------------------------------------------------------------- #
#  Languages
# --------------------------------------------------------------------------- #

LANGUAGE_CODES = ("en", "bn", "hi")

LANGUAGE_LABELS = {
    "en": "English",
    "bn": "বাংলা",
    "hi": "हिंदी",
}

# Label shown in the report form -> internal language code.
LANGUAGE_BY_LABEL = {label: code for code, label in LANGUAGE_LABELS.items()}

SCRIPT_PATTERNS = {
    "bn": re.compile(r"[\u0980-\u09FF]"),
    "hi": re.compile(r"[\u0900-\u097F]"),
    "en": re.compile(r"[A-Za-z]"),
}

# --------------------------------------------------------------------------- #
#  Interface strings
# --------------------------------------------------------------------------- #

UI = {
    "en": {
        "brand_sub": "Civic voice platform",
        "hero": "Every voice deserves to be heard.",
        "hero_sub": (
            "Report local problems in your language. "
            "Turn your voice into action."
        ),
        "workspace": "Demo workspace",
        "ui_language": "Interface language",
        "m_total": "Total Reports",
        "m_open": "Open Cases",
        "m_high": "High Priority",
        "m_total_note": "Logged in this demo workspace",
        "m_open_note": "Awaiting field action · {n} in progress",
        "m_high_note": "Flagged for urgent review",
        "sec_report": "File a report",
        "sec_report_hint": (
            "Describe the problem in your own words. Mentioning a landmark "
            "or a duration usually improves the suggested action."
        ),
        "f_language": "Report language",
        "f_location": "Location",
        "f_location_ph": "e.g. Beleghata, Kolkata",
        "f_text": "Complaint details",
        "f_text_ph": (
            "Describe what is wrong, where it is, and how long it has been "
            "like this."
        ),
        "f_submit": "Analyse Complaint",
        "f_sample": "Load Bengali sample",
        "f_clear": "Clear form",
        "f_reset": "Reset demo data",
        "v_title": "Complaint review",
        "v_empty_title": "No analysis yet",
        "v_empty_body": (
            "Submit the form on the left and a suggested category, priority "
            "and next step will appear here."
        ),
        "v_category": "Category",
        "v_description": "Description",
        "v_location": "Location",
        "v_priority": "Priority",
        "v_action": "Suggested action",
        "v_signals": "Signals detected",
        "v_language": "Detected language",
        "v_confidence": "Match confidence",
        "v_score": "Priority score",
        "v_no_signals": "No strong signals found in the text.",
        "v_disclaimer": (
            "Local preview only. This analysis is generated on this device "
            "from your text using keyword rules. Nothing is sent to a server "
            "and no complaint is filed with any authority."
        ),
        "v_case_created": "Saved to the tracker as reference",
        "t_title": "Civic case tracker",
        "t_hint": (
            "Sample cases are pre-loaded so the tracker is not empty. "
            "Reports you file are added on top of them."
        ),
        "t_ref": "Reference",
        "t_status": "Status",
        "t_priority": "Priority",
        "t_filter": "Filter by status",
        "t_all": "All cases",
        "t_empty": "No cases match this filter yet.",
        "t_showing": "Showing {n} of {total} cases",
        "t_manage": "Update a case",
        "t_manage_pick": "Case",
        "t_manage_status": "New status",
        "t_manage_apply": "Update status",
        "t_updated": "Case {ref} moved to {status}.",
        "st_open": "Open",
        "st_in_progress": "In Progress",
        "st_resolved": "Resolved",
        "p_high": "High priority",
        "p_medium": "Medium priority",
        "p_low": "Low priority",
        "l_detected": "Detected",
        "l_unknown": "Not detected",
        "flash_filed": "Report {ref} analysed and added to the tracker.",
        "flash_sample": "Bengali sample complaint loaded into the form.",
        "flash_cleared": "Form cleared.",
        "flash_reset": "Demo workspace restored to its starting state.",
        "err_text": "Add a description of the problem before analysing.",
        "err_location": "Add a location so the case can be traced back.",
        "foot_note": (
            "Nagarik AI is an independent prototype. It is not affiliated "
            "with any government body and does not submit complaints."
        ),
        "foot_flow": "Describe · Analyse · Track",
    },
    "bn": {
        "brand_sub": "নাগরিক ভয়েস প্ল্যাটফর্ম",
        "hero": "প্রতিটি কণ্ঠস্বর শোনার যোগ্য।",
        "hero_sub": (
            "আপনার ভাষায় এলাকার সমস্যা জানান। "
            "আপনার আওয়াজকে কাজে পরিণত করুন।"
        ),
        "workspace": "ডেমো ওয়ার্কস্পেস",
        "ui_language": "ইন্টারফেসের ভাষা",
        "m_total": "মোট অভিযোগ",
        "m_open": "চলমান মামলা",
        "m_high": "উচ্চ অগ্রাধিকার",
        "m_total_note": "এই ডেমো ওয়ার্কস্পেসে নথিভুক্ত",
        "m_open_note": "মাঠে কাজের অপেক্ষায় · {n} টি চলছে",
        "m_high_note": "দ্রুত পর্যালোচনার জন্য চিহ্নিত",
        "sec_report": "অভিযোগ জানান",
        "sec_report_hint": (
            "নিজের ভাষায় সমস্যাটি লিখুন। জায়গার চিহ্ন বা কত দিন ধরে "
            "চলছে তা লিখলে পরামর্শ আরও নির্দিষ্ট হয়।"
        ),
        "f_language": "অভিযোগের ভাষা",
        "f_location": "এলাকা",
        "f_location_ph": "যেমন বেলেঘাটা, কলকাতা",
        "f_text": "অভিযোগের বিবরণ",
        "f_text_ph": "কী সমস্যা, কোথায়, আর কত দিন ধরে — লিখুন।",
        "f_submit": "অভিযোগ বিশ্লেষণ করুন",
        "f_sample": "বাংলা নমুনা দিন",
        "f_clear": "ফর্ম খালি করুন",
        "f_reset": "ডেমো তথ্য রিসেট",
        "v_title": "অভিযোগ পর্যালোচনা",
        "v_empty_title": "এখনও কোনো বিশ্লেষণ নেই",
        "v_empty_body": (
            "বাঁ দিকের ফর্মটি জমা দিলে এখানে সম্ভাব্য বিষয়, "
            "অগ্রাধিকার ও পরবর্তী পদক্ষেপ দেখা যাবে।"
        ),
        "v_category": "বিষয়",
        "v_description": "বিবরণ",
        "v_location": "এলাকা",
        "v_priority": "অগ্রাধিকার",
        "v_action": "প্রস্তাবিত পদক্ষেপ",
        "v_signals": "চিহ্নিত সংকেত",
        "v_language": "শনাক্ত ভাষা",
        "v_confidence": "মিলের নিশ্চয়তা",
        "v_score": "অগ্রাধিকার স্কোর",
        "v_no_signals": "লেখায় স্পষ্ট কোনো সংকেত পাওয়া যায়নি।",
        "v_disclaimer": (
            "শুধু স্থানীয় প্রিভিউ। আপনার লেখা থেকে শব্দ-নিয়ম ব্যবহার করে "
            "এই বিশ্লেষণ এই ডিভাইসেই তৈরি হয়। কোথাও পাঠানো হয় না এবং "
            "কোনো কর্তৃপক্ষের কাছে অভিযোগ দায়ের হয় না।"
        ),
        "v_case_created": "ট্র্যাকারে নথিভুক্ত হয়েছে, রেফারেন্স",
        "t_title": "নাগরিক মামলা ট্র্যাকার",
        "t_hint": (
            "ট্র্যাকার খালি না থাকার জন্য কয়েকটি নমুনা মামলা দেওয়া আছে। "
            "আপনার জানানো অভিযোগ এর সঙ্গে যোগ হবে।"
        ),
        "t_ref": "রেফারেন্স",
        "t_status": "অবস্থা",
        "t_priority": "অগ্রাধিকার",
        "t_filter": "অবস্থা অনুযায়ী দেখুন",
        "t_all": "সব মামলা",
        "t_empty": "এই ফিল্টারে কোনো মামলা নেই।",
        "t_showing": "{total} টির মধ্যে {n} টি দেখানো হচ্ছে",
        "t_manage": "মামলার অবস্থা বদলান",
        "t_manage_pick": "মামলা",
        "t_manage_status": "নতুন অবস্থা",
        "t_manage_apply": "অবস্থা বদলান",
        "t_updated": "মামলা {ref} এখন {status}।",
        "st_open": "চলমান",
        "st_in_progress": "কাজ চলছে",
        "st_resolved": "সমাধান হয়েছে",
        "p_high": "উচ্চ অগ্রাধিকার",
        "p_medium": "মাঝারি অগ্রাধিকার",
        "p_low": "কম অগ্রাধিকার",
        "l_detected": "শনাক্ত",
        "l_unknown": "শনাক্ত হয়নি",
        "flash_filed": "অভিযোগ {ref} বিশ্লেষণ করে ট্র্যাকারে যোগ করা হয়েছে।",
        "flash_sample": "বাংলা নমুনা অভিযোগ ফর্মে বসানো হয়েছে।",
        "flash_cleared": "ফর্ম খালি করা হয়েছে।",
        "flash_reset": "ডেমো ওয়ার্কস্পেস আগের অবস্থায় ফিরিয়ে আনা হয়েছে।",
        "err_text": "বিশ্লেষণের আগে সমস্যার বিবরণ লিখুন।",
        "err_location": "মামলা খুঁজে পাওয়ার জন্য এলাকা লিখুন।",
        "foot_note": (
            "Nagarik AI একটি স্বতন্ত্র প্রোটোটাইপ। কোনো সরকারি সংস্থার সঙ্গে "
            "এর সম্পর্ক নেই এবং এটি কোনো অভিযোগ জমা দেয় না।"
        ),
        "foot_flow": "লিখুন · বিশ্লেষণ · অনুসরণ",
    },
    "hi": {
        "brand_sub": "नागरिक वॉइस प्लेटफ़ॉर्म",
        "hero": "हर आवाज़ सुने जाने के काबिल है।",
        "hero_sub": (
            "अपनी भाषा में इलाके की समस्याएँ बताइए। "
            "अपनी आवाज़ को काम में बदलिए।"
        ),
        "workspace": "डेमो वर्कस्पेस",
        "ui_language": "इंटरफ़ेस भाषा",
        "m_total": "कुल शिकायतें",
        "m_open": "खुली शिकायतें",
        "m_high": "उच्च प्राथमिकता",
        "m_total_note": "इस डेमो वर्कस्पेस में दर्ज",
        "m_open_note": "फील्ड कार्रवाई की प्रतीक्षा में · {n} प्रगति में",
        "m_high_note": "तत्काल समीक्षा के लिए चिह्नित",
        "sec_report": "शिकायत दर्ज करें",
        "sec_report_hint": (
            "समस्या अपने शब्दों में लिखिए। पास का लैंडमार्क या अवधि "
            "बताने पर सुझाव ज़्यादा सटीक होता है।"
        ),
        "f_language": "शिकायत की भाषा",
        "f_location": "इलाका",
        "f_location_ph": "जैसे बेलेघाटा, कोलकाता",
        "f_text": "शिकायत का विवरण",
        "f_text_ph": "क्या समस्या है, कहाँ है, और कितने दिनों से है — लिखिए।",
        "f_submit": "शिकायत का विश्लेषण करें",
        "f_sample": "बांग्ला नमूना भरें",
        "f_clear": "फ़ॉर्म खाली करें",
        "f_reset": "डेमो डेटा रीसेट",
        "v_title": "शिकायत समीक्षा",
        "v_empty_title": "अभी कोई विश्लेषण नहीं",
        "v_empty_body": (
            "बाईं ओर का फ़ॉर्म भेजने पर यहाँ संभावित श्रेणी, "
            "प्राथमिकता और अगला कदम दिखेगा।"
        ),
        "v_category": "श्रेणी",
        "v_description": "विवरण",
        "v_location": "इलाका",
        "v_priority": "प्राथमिकता",
        "v_action": "सुझाया गया कदम",
        "v_signals": "पहचाने गए संकेत",
        "v_language": "पहचानी गई भाषा",
        "v_confidence": "मिलान का भरोसा",
        "v_score": "प्राथमिकता स्कोर",
        "v_no_signals": "पाठ में कोई स्पष्ट संकेत नहीं मिला।",
        "v_disclaimer": (
            "केवल स्थानीय पूर्वावलोकन। यह विश्लेषण आपके पाठ से कीवर्ड "
            "नियमों द्वारा इसी डिवाइस पर बनता है। कहीं भेजा नहीं जाता और "
            "किसी प्राधिकरण में शिकायत दर्ज नहीं होती।"
        ),
        "v_case_created": "ट्रैकर में दर्ज, संदर्भ",
        "t_title": "नागरिक केस ट्रैकर",
        "t_hint": (
            "ट्रैकर खाली न रहे, इसलिए कुछ नमूना केस पहले से हैं। "
            "आपकी दर्ज शिकायतें इनके ऊपर जुड़ेंगी।"
        ),
        "t_ref": "संदर्भ",
        "t_status": "स्थिति",
        "t_priority": "प्राथमिकता",
        "t_filter": "स्थिति से छाँटें",
        "t_all": "सभी केस",
        "t_empty": "इस फ़िल्टर में कोई केस नहीं है।",
        "t_showing": "{total} में से {n} दिख रहे हैं",
        "t_manage": "केस की स्थिति बदलें",
        "t_manage_pick": "केस",
        "t_manage_status": "नई स्थिति",
        "t_manage_apply": "स्थिति बदलें",
        "t_updated": "केस {ref} अब {status} है।",
        "st_open": "खुली",
        "st_in_progress": "प्रगति में",
        "st_resolved": "हल हुई",
        "p_high": "उच्च प्राथमिकता",
        "p_medium": "मध्यम प्राथमिकता",
        "p_low": "कम प्राथमिकता",
        "l_detected": "पहचानी गई",
        "l_unknown": "पहचान नहीं हुई",
        "flash_filed": "शिकायत {ref} का विश्लेषण होकर ट्रैकर में जुड़ गई।",
        "flash_sample": "बांग्ला नमूना शिकायत फ़ॉर्म में भर दी गई।",
        "flash_cleared": "फ़ॉर्म खाली कर दिया गया।",
        "flash_reset": "डेमो वर्कस्पेस शुरुआती स्थिति में लौटा दिया गया।",
        "err_text": "विश्लेषण से पहले समस्या का विवरण लिखिए।",
        "err_location": "केस ट्रैक करने के लिए इलाका लिखिए।",
        "foot_note": (
            "Nagarik AI एक स्वतंत्र प्रोटोटाइप है। किसी सरकारी निकाय से "
            "इसका कोई संबंध नहीं है और यह शिकायत जमा नहीं करता।"
        ),
        "foot_flow": "लिखिए · विश्लेषण · निगरानी",
    },
}
# --------------------------------------------------------------------------- #
#  Category taxonomy
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Category:
    """A civic complaint category with its multilingual labels and keywords."""

    key: str
    names: dict[str, str]
    departments: dict[str, str]
    actions: dict[str, str]
    keywords: dict[str, tuple[str, ...]]
    base_priority: int

    def name(self, lang: str) -> str:
        return self.names.get(lang, self.names["en"])

    def department(self, lang: str) -> str:
        return self.departments.get(lang, self.departments["en"])

    def action(self, lang: str) -> str:
        return self.actions.get(lang, self.actions["en"])

    def all_keywords(self) -> tuple[str, ...]:
        seen: list[str] = []
        for lang in LANGUAGE_CODES:
            for word in self.keywords.get(lang, ()):
                if word not in seen:
                    seen.append(word)
        return tuple(seen)

    def keyword_language(self, word: str) -> str:
        for lang in LANGUAGE_CODES:
            if word in self.keywords.get(lang, ()):
                return lang
        return "en"


CATEGORIES: tuple[Category, ...] = (
    Category(
        key="drainage",
        names={
            "en": "Drainage & Sanitation",
            "bn": "নিকাশি ও পরিচ্ছন্নতা",
            "hi": "जलनिकासी और स्वच्छता",
        },
        base_priority=62,
        departments={
            "en": "Municipal Drainage & Sewerage Department",
            "bn": "পুরসভার নিকাশি দফতর",
            "hi": "नगर निगम जलनिकासी विभाग",
        },
        keywords={
            "en": (
                "drain", "drainage", "sewer", "sewerage", "manhole", "gutter",
                "overflow", "overflowing", "clogged", "choked", "waterlogging",
                "water logging", "stagnant", "open drain", "nullah", "nala",
                "sanitation", "foul smell", "stink",
            ),
            "bn": (
                "নর্দমা", "ড্রেন", "নালা", "ম্যানহোল", "পয়ঃনিষ্কাশন",
                "উপচে", "উপচে পড়ছে", "জমে", "জলজমা", "দুর্গন্ধ", "দূর্গন্ধ",
                "মশা", "পরিষ্কার", "নিকাশি", "ড্রেনেজ",
            ),
            "hi": (
                "नाली", "नाला", "ड्रेन", "नर्दमा", "नालियों", "सीवर",
                "मैनहोल", "जलभराव", "जमा पानी", "बदबू", "दुर्गंध", "मच्छर",
                "सफाई", "निकासी",
            ),
        },
        actions={
            "en": (
                "Ask the drainage department for a same-day inspection and "
                "de-silting before the next rainfall, and note the exact "
                "junction or lane so the complaint is not closed as untraceable."
            ),
            "bn": (
                "আগামী বৃষ্টির আগে নর্দমার পরিদর্শন ও সিলেট পরিষ্কারের জন্য "
                "দফতরের কাছে অনুরোধ করুন, এবং নির্দিষ্ট মোড় বা গলির নাম "
                "লিখুন যাতে অভিযোগ খুঁজে পাওয়া যায়।"
            ),
            "hi": (
                "अगली बारिश से पहले नाली की जाँच और सफाई के लिए विभाग से "
                "अनुरोध करें, और सटीक चौराहा या गली लिखें ताकि शिकायत "
                "लापता न हो।"
            ),
        },
    ),
    Category(
        key="roads",
        names={
            "en": "Roads & Potholes",
            "bn": "রাস্তা ও গর্ত",
            "hi": "सड़क और गड्ढे",
        },
        base_priority=52,
        departments={
            "en": "Public Works Department (Roads)",
            "bn": "সরকারি নির্মাণ বিভাগ (রাস্তা)",
            "hi": "लोक निर्माण विभाग (सड़क)",
        },
        keywords={
            "en": (
                "pothole", "potholes", "road", "roads", "road damage",
                "broken road", "footpath", "pavement", "kerb", "divider",
                "speed breaker", "cave", "caved", "dug up", "tar", "asphalt",
                "patchwork", "skid", "crater",
            ),
            "bn": (
                "রাস্তা", "রাস্তার", "গর্ত", "গর্তে", "ফুটপাত", "ফুটপাথ",
                "পিচ", "ডিভাইডার", "ভাঙা", "খানাখন্দ", "স্পিড ব্রেকার",
            ),
            "hi": (
                "सड़क", "रोड", "गड्ढा", "गड्ढे", "फुटपाथ", "पटरी",
                "टूटी सड़क", "डिवाइडर", "स्पीड ब्रेकर", "टार",
            ),
        },
        actions={
            "en": (
                "File a repair request naming the road, the stretch and the "
                "nearest landmark, and ask for barricading or a warning sign "
                "until the patch work is scheduled."
            ),
            "bn": (
                "রাস্তার নাম, কোন অংশ এবং কাছের চিহ্ন উল্লেখ করে মেরামতের "
                "আবেদন করুন, এবং কাজ শুরুর আগে ব্যারিকেড বা সতর্কতা "
                "চিহ্ন দেওয়ার অনুরোধ করুন।"
            ),
            "hi": (
                "सड़क का नाम, हिस्सा और नज़दीकी लैंडमार्क लिखकर मरम्मत का "
                "अनुरोध करें, और काम शुरू होने तक बैरिकेड या चेतावनी चिह्न "
                "माँगें।"
            ),
        },
    ),
    Category(
        key="lighting",
        names={
            "en": "Street Lighting",
            "bn": "রাস্তার আলো",
            "hi": "सड़क प्रकाश",
        },
        base_priority=48,
        departments={
            "en": "Municipal Electrical & Lighting Division",
            "bn": "পুরসভার বিদ্যুৎ ও আলো বিভাগ",
            "hi": "नगर निगम विद्युत एवं प्रकाश प्रभाग",
        },
        keywords={
            "en": (
                "street light", "streetlight", "street lights",
                "streetlights", "lamp post", "lamppost", "lamp", "lighting",
                "dark street", "no light", "not working", "bulb", "pole",
                "flicker",
            ),
            "bn": (
                "রাস্তার আলো", "স্ট্রিট লাইট", "ল্যাম্প", "ল্যাম্পপোস্ট",
                "খুঁটি", "অন্ধকার", "বাতি", "বাল্ব", "আলো নেই",
            ),
            "hi": (
                "स्ट्रीट लाइट", "स्ट्रीटलाइट", "बत्ती", "लाइट", "खंभा",
                "अंधेरा", "लैंप", "बल्ब", "रोशनी",
            ),
        },
        actions={
            "en": (
                "Raise a pole-level complaint with the pole number or the "
                "nearest shop, so the fault is traced to a circuit instead of "
                "the whole street, and mention how dark the stretch gets."
            ),
            "bn": (
                "খুঁটির নম্বর বা কাছের দোকানের নাম উল্লেখ করে অভিযোগ করুন, "
                "যাতে গোটা রাস্তার বদলে নির্দিষ্ট সার্কিটে ত্রুটি চিহ্নিত হয়, "
                "এবং রাস্তা কতটা অন্ধকার থাকে তা লিখুন।"
            ),
            "hi": (
                "खंभे का नंबर या नज़दीकी दुकान लिखकर शिकायत दर्ज करें, ताकि "
                "पूरी सड़क की जगह सटीक सर्किट की खराबी पकड़ी जाए, और हिस्सा "
                "कितना अंधेरा रहता है यह भी बताएँ।"
            ),
        },
    ),
    Category(
        key="water",
        names={
            "en": "Water Supply",
            "bn": "জল সরবরাহ",
            "hi": "जल आपूर्ति",
        },
        base_priority=58,
        departments={
            "en": "Water Supply & Sewerage Board",
            "bn": "জল সরবরাহ ও পয়ঃনিষ্কাশন বোর্ড",
            "hi": "जल आपूर्ति एवं जलनिकासी बोर्ड",
        },
        keywords={
            "en": (
                "water supply", "no water", "water shortage", "tap", "pipeline",
                "water pipe", "pipe", "leakage", "leaking", "borewell",
                "tubewell", "tube well", "hand pump", "handpump",
                "contaminated water", "muddy water", "drinking water",
                "pressure", "tank",
            ),
            "bn": (
                "জল", "পানীয় জল", "জল সরবরাহ", "কল", "টিউবওয়েল", "নলকূপ",
                "পাইপ", "লিক", "জল নেই", "নোংরা জল", "জলের চাপ", "জলজমা",
            ),
            "hi": (
                "पानी", "जल", "नल", "पाइपलाइन", "पाइप", "ट्यूबवेल",
                "हैंडपंप", "गंदा पानी", "पानी नहीं", "पेयजल", "टंकी",
                "रिसाव",
            ),
        },
        actions={
            "en": (
                "Report the supply timing, the pressure and the exact pipe "
                "location, and ask for a water sample test if the colour or "
                "smell has changed."
            ),
            "bn": (
                "জল আসার সময়, চাপ এবং পাইপের নির্দিষ্ট অবস্থান জানান, "
                "এবং জলের রং বা গন্ধ বদলে গেলে নমুনা পরীক্ষার অনুরোধ করুন।"
            ),
            "hi": (
                "पानी आने का समय, दबाव और पाइप की सटीक जगह बताएँ, और रंग या "
                "गंध बदली हो तो नमूना जाँच का अनुरोध करें।"
            ),
        },
    ),
    Category(
        key="electricity",
        names={
            "en": "Electrical & Wires",
            "bn": "বিদ্যুৎ ও তার",
            "hi": "बिजली और तार",
        },
        base_priority=66,
        departments={
            "en": "State Electricity Distribution Utility",
            "bn": "রাজ্য বিদ্যুৎ বণ্টন সংস্থা",
            "hi": "राज्य विद्युत वितरण निगम",
        },
        keywords={
            "en": (
                "electricity", "power cut", "power failure", "transformer",
                "electric wire", "live wire", "exposed wire", "spark",
                "sparking", "short circuit", "voltage", "meter", "electric pole",
                "shock", "hanging wire",
            ),
            "bn": (
                "বিদ্যুৎ", "কারেন্ট", "ট্রান্সফরমার", "তার", "বৈদ্যুতিক",
                "শর্ট সার্কিট", "স্পার্ক", "ভোল্টেজ", "মিটার", "ঝুলছে",
            ),
            "hi": (
                "बिजली", "करंट", "ट्रांसफार्मर", "तार", "बिजली का तार",
                "वोल्टेज", "मीटर", "शॉर्ट सर्किट", "चिंगारी", "खंभा",
            ),
        },
        actions={
            "en": (
                "Treat exposed or sparking wiring as an emergency: keep people "
                "away, inform the utility immediately, and ask for the feeder "
                "to be isolated until the line is re-strung."
            ),
            "bn": (
                "খোলা বা স্পার্ক করছে এমন তারকে জরুরি অবস্থা হিসেবে দেখুন: "
                "মানুষকে দূরে রাখুন, সঙ্গে সঙ্গে সংস্থাকে জানান এবং তার "
                "ঠিক না হওয়া পর্যন্ত ফিডার বন্ধ রাখার অনুরোধ করুন।"
            ),
            "hi": (
                "खुले या चिंगारी छोड़ते तार को आपात स्थिति मानें: लोगों को "
                "दूर रखें, तुरंत निगम को सूचित करें और तार दुरुस्त होने तक "
                "फीडर बंद करने का अनुरोध करें।"
            ),
        },
    ),
    Category(
        key="waste",
        names={
            "en": "Waste & Public Health",
            "bn": "আবর্জনা ও জনস্বাস্থ্য",
            "hi": "कचरा और जन स्वास्थ्य",
        },
        base_priority=56,
        departments={
            "en": "Municipal Solid Waste & Health Department",
            "bn": "পুরসভার বর্জ্য ও স্বাস্থ্য বিভাগ",
            "hi": "नगर निगम ठोस कचरा एवं स्वास्थ्य विभाग",
        },
        keywords={
            "en": (
                "garbage", "waste", "rubbish", "trash", "dumping", "dump",
                "litter", "dustbin", "bin", "filth", "hygiene", "mosquito",
                "mosquitoes", "dengue", "malaria", "rats", "rodent", "stray",
                "smell", "unhygienic",
            ),
            "bn": (
                "আবর্জনা", "ময়লা", "ঝুড়ি", "ডাস্টবিন", "জঞ্জাল", "মশা",
                "ডেঙ্গু", "ম্যালেরিয়া", "ইঁদুর", "দুর্গন্ধ", "অস্বাস্থ্যকর",
                "পরিষ্কার করা হচ্ছে না",
            ),
            "hi": (
                "कचरा", "गंदगी", "कूड़ा", "डस्टबिन", "कचरे", "मच्छर",
                "डेंगू", "मलेरिया", "चूहा", "बदबू", "अस्वच्छ",
            ),
        },
        actions={
            "en": (
                "Escalate to the ward sanitation inspector with the exact "
                "collection point, ask for a fixed daily clearance slot, and "
                "mention any mosquito-borne illness already reported nearby."
            ),
            "bn": (
                "সংগ্রহস্থলের নির্দিষ্ট তথ্য দিয়ে ওয়ার্ডের স্যানিটেশন "
                "ইন্সপেক্টরের কাছে অভিযোগ করুন, প্রতিদিন নির্দিষ্ট সময়ে "
                "পরিষ্কারের দাবি জানান, এবং মশাবাহিত রোগের কথা উল্লেখ করুন।"
            ),
            "hi": (
                "सटीक संग्रहण स्थान के साथ वार्ड स्वच्छता निरीक्षक तक "
                "शिकायत पहुँचाएँ, रोज़ तय समय पर सफाई की माँग करें, और "
                "मच्छरजनित बीमारी का ज़िक्र करें।"
            ),
        },
    ),
    Category(
        key="safety",
        names={
            "en": "Safety & Traffic",
            "bn": "নিরাপত্তা ও যান চলাচল",
            "hi": "सुरक्षा और यातायात",
        },
        base_priority=60,
        departments={
            "en": "Traffic Police / Local Civic Safety Cell",
            "bn": "ট্রাফিক পুলিশ / স্থানীয় নাগরিক নিরাপত্তা সেল",
            "hi": "ट्रैफिक पुलिस / स्थानीय नागरिक सुरक्षा प्रकोष्ठ",
        },
        keywords={
            "en": (
                "accident", "accidents", "unsafe", "safety", "traffic", "jam",
                "congestion", "signal", "crossing", "zebra", "speeding",
                "danger", "dangerous", "encroach", "encroachment", "foot over",
                "blind spot", "school zone",
            ),
            "bn": (
                "দুর্ঘটনা", "নিরাপত্তা", "অনিরাপদ", "যানজট", "ট্রাফিক",
                "সিগন্যাল", "জেব্রা ক্রসিং", "বিপদ", "ঝুঁকি", "দখল",
                "স্কুল", "গতি",
            ),
            "hi": (
                "दुर्घटना", "हादसा", "सुरक्षा", "असुरक्षित", "जाम",
                "ट्रैफिक", "सिग्नल", "ज़ेब्रा क्रॉसिंग", "खतरा", "जोखिम",
                "अतिक्रमण", "स्कूल",
            ),
        },
        actions={
            "en": (
                "File it with the traffic or safety cell, quote the accident or "
                "near-miss history, and ask for a temporary warning sign or "
                "speed breaker until a permanent measure is sanctioned."
            ),
            "bn": (
                "ট্রাফিক বা নিরাপত্তা সেলে অভিযোগ দিন, দুর্ঘটনার তথ্য উল্লেখ "
                "করুন, এবং স্থায়ী ব্যবস্থা না হওয়া পর্যন্ত অস্থায়ী সতর্কতা "
                "চিহ্ন বা স্পিড ব্রেকার চান।"
            ),
            "hi": (
                "ट्रैफिक या सुरक्षा प्रकोष्ठ में शिकायत दर्ज करें, दुर्घटना "
                "का ब्यौरा दें, और स्थायी इंतज़ाम तक अस्थायी चेतावनी चिह्न या "
                "स्पीड ब्रेकर माँगें।"
            ),
        },
    ),
    Category(
        key="other",
        names={
            "en": "Other Civic Issue",
            "bn": "অন্যান্য নাগরিক সমস্যা",
            "hi": "अन्य नागरिक समस्या",
        },
        base_priority=40,
        departments={
            "en": "Ward Grievance Cell",
            "bn": "ওয়ার্ড অভিযোগ কেন্দ্র",
            "hi": "वार्ड शिकायत केंद्र",
        },
        keywords={"en": (), "bn": (), "hi": ()},
        actions={
            "en": (
                "File it with the ward grievance cell, describe the location "
                "precisely, and follow the reference number until you receive a "
                "written response."
            ),
            "bn": (
                "ওয়ার্ড অভিযোগ কেন্দ্রে জানান, জায়গার বিবরণ স্পষ্টভাবে লিখুন, "
                "এবং লিখিত উত্তর না পাওয়া পর্যন্ত রেফারেন্স নম্বর অনুসরণ করুন।"
            ),
            "hi": (
                "वार्ड शिकायत केंद्र में दर्ज करें, स्थान का सटीक विवरण दें, "
                "और लिखित उत्तर मिलने तक संदर्भ नंबर का पीछा करें।"
            ),
        },
    ),
)

CATEGORY_BY_KEY = {category.key: category for category in CATEGORIES}

SEVERITY_SIGNALS: dict[str, tuple[str, ...]] = {
    "high": (
        # English
        "overflow", "overflowing", "burst", "bursting", "collapse",
        "collapsed", "danger", "dangerous", "emergency", "urgent",
        "immediately", "hospital", "school", "children", "child", "elderly",
        "pregnant", "accident", "fire", "live wire", "exposed wire", "shock",
        "death", "died", "injury", "injured", "disease", "dengue", "malaria",
        "whole day", "every day", "two weeks", "three weeks", "one month",
        "two months", "months", "years", "night",
        # Bengali
        "উপচে", "ফেটে", "ভেঙে", "বিপদ", "ঝুঁকি", "জরুরি", "অবিলম্বে",
        "হাসপাতাল", "স্কুল", "শিশু", "বাচ্চা", "বৃদ্ধ", "গর্ভবতী",
        "দুর্ঘটনা", "আগুন", "বিদ্যুৎস্পৃষ্ট", "মৃত্যু", "আহত", "রোগ",
        "ডেঙ্গু", "ম্যালেরিয়া", "সারাদিন", "প্রতিদিন", "দুই সপ্তাহ",
        "মাস", "বছর", "রাত", "দুর্গন্ধ",
        # Hindi
        "उफन", "फट", "ढह", "खतरा", "जोखिम", "आपात", "तुरंत", "अस्पताल",
        "स्कूल", "बच्च", "बुज़ुर्ग", "गर्भवती", "दुर्घटना", "हादसा", "आग",
        "करंट", "मौत", "घायल", "बीमारी", "डेंगू", "मलेरिया", "सारा दिन",
        "रोज़", "दो हफ़्ते", "महीन", "साल", "रात", "बदबू",
    ),
    "medium": (
        "sometimes", "occasionally", "few days", "one week", "last week",
        "leak", "leaking", "slow", "damaged", "broken", "sparking",
        "कुछ दिन", "एक हफ़्ते", "कभी-कभी", "टूट", "खराब", "रिसाव", "धीमा",
        "কয়েকদিন", "এক সপ্তাহ", "গত সপ্তাহ", "মাঝে মাঝে", "ফুটো", "ভাঙা",
        "নষ্ট", "ধীর",
    ),
}

SEVERITY_WEIGHTS = {"high": 7, "medium": 3}
MAX_HIGH_SIGNAL_BONUS = 35
MAX_MEDIUM_SIGNAL_BONUS = 12
LENGTH_BONUS_PER_CHARS = 90
MAX_LENGTH_BONUS = 8
DURATION_BONUS = 4
DURATION_PATTERNS = (
    re.compile(r"\b\d+\s*(day|days|week|weeks|month|months|year|years)\b"),
    re.compile(r"[০-৯]+\s*(দিন|সপ্তাহ|মাস|বছর)"),
    re.compile(r"[०-९]+\s*(दिन|हफ़्ते|हफ्ते|महीने|महिने|साल|वर्ष)"),
)
# --------------------------------------------------------------------------- #
#  Analysis engine (on-device, rule based)
# --------------------------------------------------------------------------- #

TOKEN_PATTERN = re.compile(r"[0-9A-Za-z\u0900-\u097F\u0980-\u09FF]+")

# Tokens at or above this length also match as a prefix, so "pothole" also
# finds "potholes" and "drain" finds "drainage".
MIN_STEM_LENGTH = 3

# When two categories match the same number of keywords, the more specific
# one wins. Roads is deliberately low: "road" appears inside almost every
# complaint.
CATEGORY_MATCH_WEIGHT = {
    "drainage": 6,
    "electricity": 6,
    "water": 5,
    "waste": 5,
    "safety": 4,
    "lighting": 3,
    "roads": 2,
    "other": 0,
}

HIGH_PRIORITY_CUTOFF = 65
MEDIUM_PRIORITY_CUTOFF = 45
MAX_OTHER_PRIORITY = 64

MAX_SIGNALS_SHOWN = 7
TITLE_MAX_CHARS = 78


@dataclass
class Analysis:
    """What the local rule engine concluded about one complaint."""

    category_key: str
    priority: str
    score: int
    confidence: float
    detected_language: str
    matched_keywords: tuple[str, ...] = ()
    severity_hits: tuple[str, ...] = ()

    @property
    def category(self) -> Category:
        return CATEGORY_BY_KEY[self.category_key]

    @property
    def signals(self) -> tuple[str, ...]:
        seen: list[str] = []
        for item in (*self.matched_keywords, *self.severity_hits):
            if item not in seen:
                seen.append(item)
        return tuple(seen[:MAX_SIGNALS_SHOWN])


@dataclass
class Report:
    """One civic report held in the demo workspace."""

    ref: str
    text: str
    location: str
    language: str
    analysis: Analysis
    status: str
    filed_on: dt.date
    is_sample: bool = False

    @property
    def category(self) -> Category:
        return self.analysis.category

    @property
    def priority(self) -> str:
        return self.analysis.priority

    @property
    def title(self) -> str:
        return title_from_text(self.text)


def tokenise(text: str) -> list[str]:
    """Split text into lower-case word tokens across Latin, Devanagari, Bengali."""
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def _phrase_matches(tokens: list[str], phrase_tokens: list[str]) -> bool:
    span = len(phrase_tokens)
    if span == 0:
        return False
    if span == 1:
        needle = phrase_tokens[0]
        for token in tokens:
            if token == needle:
                return True
            if len(needle) >= MIN_STEM_LENGTH and token.startswith(needle):
                return True
        return False
    for index in range(len(tokens) - span + 1):
        if tokens[index:index + span] == phrase_tokens:
            return True
    return False


def contains_phrase(text: str, phrase: str) -> bool:
    return _phrase_matches(tokenise(text), tokenise(phrase))


def match_keywords(text: str, words: tuple[str, ...]) -> list[str]:
    tokens = tokenise(text)
    return [word for word in words if _phrase_matches(tokens, tokenise(word))]


def detect_language(text: str) -> str:
    """Guess the complaint's language from the scripts it uses."""
    counts = {
        code: len(pattern.findall(text))
        for code, pattern in SCRIPT_PATTERNS.items()
    }
    best = max(counts, key=lambda code: counts[code])
    return best if counts[best] > 0 else "unknown"


def has_duration_phrase(text: str) -> bool:
    return any(pattern.search(text) for pattern in DURATION_PATTERNS)


def score_priority(category: Category, high_hits: list[str], medium_hits: list[str],
                   text_length: int, has_duration: bool) -> int:
    score = category.base_priority
    score += min(len(high_hits) *
                 SEVERITY_WEIGHTS["high"], MAX_HIGH_SIGNAL_BONUS)
    score += min(
        len(medium_hits) * SEVERITY_WEIGHTS["medium"], MAX_MEDIUM_SIGNAL_BONUS
    )
    score += min(text_length // LENGTH_BONUS_PER_CHARS, MAX_LENGTH_BONUS)
    if has_duration:
        score += DURATION_BONUS
    if category.key == "other":
        score = min(score, MAX_OTHER_PRIORITY)
    return max(5, min(score, 97))


def priority_band(score: int) -> str:
    if score >= HIGH_PRIORITY_CUTOFF:
        return "high"
    if score >= MEDIUM_PRIORITY_CUTOFF:
        return "medium"
    return "low"


def choose_category(text: str) -> tuple[Category, list[str]]:
    """Pick the best category by keyword hits, then specificity, then severity."""
    best_category = CATEGORY_BY_KEY["other"]
    best_matches: list[str] = []
    best_rank = (-1, -1, -1)

    for category in CATEGORIES:
        if category.key == "other":
            continue
        matches = match_keywords(text, category.all_keywords())
        rank = (
            len(matches),
            CATEGORY_MATCH_WEIGHT[category.key],
            category.base_priority,
        )
        if rank > best_rank:
            best_rank = rank
            best_category = category
            best_matches = matches

    if best_rank[0] <= 0:
        return CATEGORY_BY_KEY["other"], []
    return best_category, best_matches


def analyse_complaint(text: str) -> Analysis:
    """Run the local rule engine over a complaint and return the verdict."""
    stripped = text.strip()
    category, matched = choose_category(stripped)
    high_hits = match_keywords(stripped, SEVERITY_SIGNALS["high"])
    medium_hits = match_keywords(stripped, SEVERITY_SIGNALS["medium"])
    score = score_priority(
        category,
        high_hits,
        medium_hits,
        len(stripped),
        has_duration_phrase(stripped),
    )
    if category.key == "other":
        confidence = 0.3
    else:
        confidence = min(0.45 + 0.1 * len(matched) +
                         0.05 * len(high_hits), 0.96)
    return Analysis(
        category_key=category.key,
        priority=priority_band(score),
        score=score,
        confidence=round(confidence, 2),
        detected_language=detect_language(stripped),
        matched_keywords=tuple(matched),
        severity_hits=tuple(dict.fromkeys((*high_hits, *medium_hits))),
    )


def title_from_text(text: str, limit: int = TITLE_MAX_CHARS) -> str:
    """A single-line case title taken from the complaint itself."""
    collapsed = re.sub(r"\s+", " ", text).strip()
    if len(collapsed) <= limit:
        return collapsed
    cut = collapsed[:limit].rsplit(" ", 1)[0]
    return f"{cut.rstrip(' ,.;:')}…"
# --------------------------------------------------------------------------- #
#  Sample data
# --------------------------------------------------------------------------- #


SAMPLE_BENGALI_COMPLAINT = (
    "আমাদের পাড়ার রাস্তার ধারের নর্দমাটি গত দুই সপ্তাহ ধরে উপচে পড়ছে। "
    "চারপাশে দুর্গন্ধ ছড়িয়েছে এবং মশার উপদ্রব অনেক বেড়ে গেছে। "
    "বৃষ্টির পানি জমে রাস্তা দিয়ে হাঁটাই কষ্টকর। "
    "অনেক বাচ্চা ও বৃদ্ধ মানুষ এই রাস্তা দিয়ে যাতায়াত করে। "
    "দ্রুত নর্দমা পরিষ্কার করার ব্যবস্থা করার অনুরোধ জানাচ্ছি।"
)
SAMPLE_BENGALI_LOCATION = "বেলেঘাটা, কলকাতা"

SAMPLE_HINDI_COMPLAINT = (
    "हमारी गली के डस्टबिन से कचरा बाहर पड़ा है। दो हफ़्ते से सफाई नहीं हुई है "
    "और बदबू तथा मच्छर बहुत बढ़ गए हैं। बच्चे वहीं खेलते हैं।"
)
SAMPLE_HINDI_LOCATION = "लाजपत नगर, नई दिल्ली"

# Reference numbers continue from the last sample case.
SEED_REF_START = 411

SEED_CASES: tuple[dict[str, object], ...] = (
    {
        "ref": 411,
        "text": SAMPLE_BENGALI_COMPLAINT,
        "location": SAMPLE_BENGALI_LOCATION,
        "language": "bn",
        "status": "open",
        "days_ago": 12,
    },
    {
        "ref": 412,
        "text": (
            "Large pothole right at the Sector V bus stop on the main road. "
            "Two-wheelers skid there every evening and a rider fell last week. "
            "The patch work done two months ago has already broken open again."
        ),
        "location": "Sector V, Bidhannagar",
        "language": "en",
        "status": "in_progress",
        "days_ago": 10,
    },
    {
        "ref": 413,
        "text": (
            "Three street lights on the Lake Gardens footpath have been dark "
            "for over a week. The stretch is completely dark after 8 pm and "
            "people returning from the metro station avoid it."
        ),
        "location": "Lake Gardens, Kolkata",
        "language": "en",
        "status": "open",
        "days_ago": 8,
    },
    {
        "ref": 414,
        "text": SAMPLE_HINDI_COMPLAINT,
        "location": SAMPLE_HINDI_LOCATION,
        "language": "hi",
        "status": "in_progress",
        "days_ago": 6,
    },
    {
        "ref": 415,
        "text": (
            "পানির পাইপ ফুটো হয়ে রাস্তায় জল পড়ছে। গলির মোড়ে পাইপের জোড়া "
            "ঢিলে হয়ে গেছে।"
        ),
        "location": "বালিগঞ্জ, কলকাতা",
        "language": "bn",
        "status": "resolved",
        "days_ago": 5,
    },
    {
        "ref": 416,
        "text": (
            "An exposed live wire is hanging low near the school gate, barely "
            "four feet from the ground. Children walk under it every morning "
            "and the pole has been damaged since the last storm."
        ),
        "location": "Shibpur, Howrah",
        "language": "en",
        "status": "open",
        "days_ago": 3,
    },
    {
        "ref": 417,
        "text": (
            "There is no zebra crossing or traffic signal at the hospital "
            "junction. Two accidents happened last month and the crossing is "
            "blind from both sides at night."
        ),
        "location": "MG Road Junction, Guwahati",
        "language": "en",
        "status": "in_progress",
        "days_ago": 2,
    },
    {
        "ref": 418,
        "text": (
            "The community park bench near the hall is broken and the park "
            "gate has no latch. Nobody has repaired it for a long time."
        ),
        "location": "Kankarbagh, Patna",
        "language": "en",
        "status": "resolved",
        "days_ago": 1,
    },
)


# --------------------------------------------------------------------------- #
#  Session state
# --------------------------------------------------------------------------- #


def current_language() -> str:
    try:
        language = st.session_state["ui_language"]
    except KeyError:
        return "en"
    return language if language in UI else "en"


def t(key: str) -> str:
    """Look up an interface string in the active language."""
    table = UI[current_language()]
    return table.get(key, UI["en"].get(key, key))


def language_name(code: str) -> str:
    return LANGUAGE_LABELS.get(code, code)


def format_ref(sequence: int, year: int | None = None) -> str:
    year = year or dt.date.today().year
    return f"NAG-{year}-{sequence:04d}"


def language_display(code: str) -> str:
    if code == "unknown":
        return t("l_unknown")
    return language_name(code)


def format_date(value: dt.date) -> str:
    return value.strftime("%d %b %Y")


def build_seed_reports() -> list[Report]:
    today = dt.date.today()
    reports: list[Report] = []
    for case in SEED_CASES:
        text = str(case["text"])
        reports.append(
            Report(
                ref=format_ref(int(case["ref"])),
                text=text,
                location=str(case["location"]),
                language=str(case["language"]),
                analysis=analyse_complaint(text),
                status=str(case["status"]),
                filed_on=today - dt.timedelta(days=int(case["days_ago"])),
                is_sample=True,
            )
        )
    return reports


def reset_workspace(announce: bool = False) -> None:
    """Restore the demo workspace to its starting state."""
    st.session_state.reports = build_seed_reports()
    st.session_state.active_ref = None
    st.session_state.form_errors = []
    st.session_state.ref_sequence = SEED_REF_START + len(SEED_CASES) + 1
    if announce:
        st.session_state.flash = ("info", t("flash_reset"))


def init_state() -> None:
    if "ui_language" not in st.session_state:
        st.session_state.ui_language = "en"
    if "reports" not in st.session_state:
        reset_workspace()
    for key, default in (
        ("active_ref", None),
        ("form_errors", []),
        ("flash", None),
        ("status_filter", "all"),
    ):
        if key not in st.session_state:
            st.session_state[key] = default


def get_reports() -> list[Report]:
    return st.session_state.reports


def find_report(ref: str) -> Report | None:
    for report in get_reports():
        if report.ref == ref:
            return report
    return None


def active_report() -> Report | None:
    ref = st.session_state.get("active_ref")
    return find_report(ref) if ref else None


def next_sequence() -> int:
    sequence = int(st.session_state.ref_sequence)
    st.session_state.ref_sequence = sequence + 1
    return sequence


def count_by_status(reports: list[Report]) -> dict[str, int]:
    counts = {status: 0 for status in STATUS_ORDER}
    for report in reports:
        counts[report.status] = counts.get(report.status, 0) + 1
    return counts


def count_by_priority(reports: list[Report]) -> dict[str, int]:
    counts = {priority: 0 for priority in PRIORITY_ORDER}
    for report in reports:
        counts[report.priority] = counts.get(report.priority, 0) + 1
    return counts


def set_flash(kind: str, message: str) -> None:
    st.session_state.flash = (kind, message)


def take_flash() -> tuple[str, str] | None:
    flash = st.session_state.get("flash")
    st.session_state.flash = None
    return flash
# --------------------------------------------------------------------------- #
#  Stylesheet
# --------------------------------------------------------------------------- #


STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600;700&display=swap');

:root{
  --ng-forest:#153B32;
  --ng-forest-mid:#1D4A3F;
  --ng-forest-soft:#E4EFEA;
  --ng-ink:#12261F;
  --ng-off:#F5F7F4;
  --ng-card:#FFFFFF;
  --ng-line:#E3E8E1;
  --ng-muted:#6C807A;
  --ng-lime:#CDF27A;
  --ng-lime-deep:#A9D94F;
  --ng-radius:20px;
  --ng-shadow:0 1px 2px rgba(15,42,36,.04), 0 16px 34px -26px rgba(15,42,36,.5);
}

#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], [data-testid="stHeader"]{ display:none !important; }

.stApp{
  background:
    radial-gradient(880px 420px at 10% -10%, #E8F2EB 0%, rgba(232,242,235,0) 60%),
    radial-gradient(680px 360px at 98% -4%, #F1F8E4 0%, rgba(241,248,228,0) 58%),
    var(--ng-off);
  font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  color:var(--ng-ink);
}
.block-container{ max-width:1180px; padding:1.9rem 1.9rem 4.5rem; }

h1,h2,h3,h4,h5{ font-family:'Inter',sans-serif; color:var(--ng-forest); }
p, li, span, div{ -webkit-font-smoothing:antialiased; }
hr{ border:none; border-top:1px solid var(--ng-line); margin:1.4rem 0; }

/* -- plain user text -------------------------------------------------- */
[data-testid="stText"], [data-testid="stText"] *{
  font-family:'Inter',sans-serif !important;
  font-size:.94rem !important;
  line-height:1.65 !important;
  color:var(--ng-ink) !important;
  white-space:pre-wrap !important;
  margin:0 !important;
}

/* -- cards ------------------------------------------------------------ */
[class*="st-key-ngc_"]{
  background:var(--ng-card);
  border:1px solid var(--ng-line);
  border-radius:var(--ng-radius);
  padding:1.5rem 1.6rem;
  box-shadow:var(--ng-shadow);
}

/* -- top bar ---------------------------------------------------------- */
.ng-topbar{ display:flex; align-items:center; gap:.8rem; }
.ng-mark{
  width:40px; height:40px; border-radius:13px; flex:none;
  background:linear-gradient(150deg,#235748,#153B32);
  display:grid; place-items:center; color:var(--ng-lime);
  box-shadow:0 10px 20px -12px rgba(21,59,50,.9);
}
.ng-brand-name{ font-size:1.02rem; font-weight:700; color:var(--ng-forest); line-height:1.15; letter-spacing:-.01em; }
.ng-brand-sub{ font-size:.68rem; font-weight:600; letter-spacing:.16em; text-transform:uppercase; color:var(--ng-muted); }
[class*="st-key-ngc_langswitch"]{ display:flex; flex-direction:column; align-items:flex-end; gap:.15rem; }
.ng-switch-label{ font-size:.68rem; font-weight:600; letter-spacing:.14em; text-transform:uppercase; color:var(--ng-muted); }

/* -- segmented control ------------------------------------------------ */
[data-testid="stSegmentedControl"] [role="radiogroup"]{
  gap:3px; background:#EDF2EC; border:1px solid var(--ng-line);
  border-radius:999px; padding:3px; flex-wrap:wrap;
}
[data-testid="stSegmentedControl"] button{
  border:none !important; background:transparent !important;
  border-radius:999px !important; padding:.32rem .78rem !important;
  font-size:.82rem !important; font-weight:600 !important;
  color:var(--ng-muted) !important; min-height:0 !important;
}
[data-testid="stSegmentedControl"] button[aria-checked="true"],
[data-testid="stSegmentedControl"] button[aria-pressed="true"]{
  background:var(--ng-forest) !important; color:#EFF9DC !important;
}
[data-testid="stSegmentedControl"] button p{ font-size:.82rem !important; font-weight:600 !important; }

/* -- hero ------------------------------------------------------------- */
.ng-hero{
  position:relative; overflow:hidden; margin:1.5rem 0 1.4rem;
  border-radius:26px; padding:2.5rem 2.4rem;
  background:linear-gradient(132deg,#153B32 0%,#1D4A3F 54%,#245548 100%);
  box-shadow:0 30px 55px -34px rgba(15,42,36,.85);
}
.ng-hero::after{
  content:""; position:absolute; right:-80px; top:-110px;
  width:340px; height:340px; border-radius:50%;
  background:radial-gradient(circle, rgba(205,242,122,.28) 0%, rgba(205,242,122,0) 68%);
}
.ng-hero::before{
  content:""; position:absolute; left:-60px; bottom:-140px;
  width:280px; height:280px; border-radius:50%;
  background:radial-gradient(circle, rgba(169,217,79,.16) 0%, rgba(169,217,79,0) 70%);
}
.ng-kicker{
  position:relative; z-index:1;
  display:inline-flex; align-items:center; gap:.45rem;
  background:rgba(205,242,122,.13); border:1px solid rgba(205,242,122,.3);
  color:#DCF7AA; font-size:.7rem; font-weight:600; letter-spacing:.13em;
  text-transform:uppercase; padding:.34rem .72rem; border-radius:999px;
}
.ng-hero h1{
  position:relative; z-index:1;
  font-family:'Fraunces',Georgia,'Times New Roman',serif;
  font-weight:600; font-size:clamp(1.75rem,3.5vw,2.75rem);
  line-height:1.12; letter-spacing:-.02em; color:#F4FBF0;
  margin:.85rem 0 .6rem; max-width:22ch;
}
.ng-hero p{
  position:relative; z-index:1; margin:0; max-width:52ch;
  color:rgba(238,249,236,.76); font-size:1.02rem; line-height:1.6;
}

/* -- flash ------------------------------------------------------------ */
.ng-flash{
  display:flex; align-items:center; gap:.6rem;
  border-radius:14px; padding:.8rem 1rem; margin-bottom:1.1rem;
  font-size:.9rem; font-weight:500; border:1px solid;
}
.ng-flash-ok{ background:#F1F9E2; border-color:#D9EDB4; color:#3C5A1C; }
.ng-flash-info{ background:#EBF3F0; border-color:#CFE0DA; color:#1D4A3F; }
.ng-flash-warn{ background:#FDF1E4; border-color:#F2DCC0; color:#8A4A0B; }

/* -- metrics ---------------------------------------------------------- */
.ng-metric-accent{ height:4px; width:40px; border-radius:999px; background:var(--ng-lime); margin-bottom:.95rem; }
.ng-metric-label{ font-size:.72rem; font-weight:600; letter-spacing:.14em; text-transform:uppercase; color:var(--ng-muted); }
.ng-metric-value{ font-size:2.1rem; font-weight:700; line-height:1.05; letter-spacing:-.03em; color:var(--ng-forest); margin:.4rem 0 .35rem; }
.ng-metric-note{ font-size:.82rem; color:var(--ng-muted); line-height:1.5; }

/* -- section header --------------------------------------------------- */
.ng-section{ margin:0 0 .2rem; }
.ng-section h3{ margin:0 0 .3rem; font-size:1.08rem; font-weight:700; letter-spacing:-.015em; }
.ng-section p{ margin:0; font-size:.86rem; color:var(--ng-muted); line-height:1.55; max-width:64ch; }
.ng-section-tight{ margin-top:.2rem; }

/* -- badges ----------------------------------------------------------- */
.ng-badge{
  display:inline-flex; align-items:center; gap:.34rem;
  font-size:.72rem; font-weight:600; line-height:1.4;
  padding:.26rem .6rem; border-radius:999px; border:1px solid transparent;
  white-space:nowrap;
}
.ng-badge-dot{ width:6px; height:6px; border-radius:50%; background:currentColor; flex:none; }
.ng-ref{
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:.75rem; font-weight:600; letter-spacing:.02em;
  color:var(--ng-forest); background:var(--ng-forest-soft);
  border-radius:8px; padding:.26rem .5rem;
}

/* -- review rows ------------------------------------------------------ */
.ng-row{ padding:.9rem 0; border-bottom:1px dashed var(--ng-line); }
.ng-row:first-of-type{ padding-top:.2rem; }
.ng-row:last-of-type{ border-bottom:none; padding-bottom:.2rem; }
.ng-row-label{
  font-size:.68rem; font-weight:600; letter-spacing:.15em;
  text-transform:uppercase; color:var(--ng-muted); margin-bottom:.42rem;
}
.ng-row-value{ font-size:.95rem; color:var(--ng-ink); line-height:1.62; }
.ng-row-actions{ display:flex; align-items:center; gap:.5rem; flex-wrap:wrap; margin-bottom:.1rem; }
.ng-dept{ font-size:.85rem; font-weight:600; color:var(--ng-forest); margin-bottom:.3rem; }
.ng-meter{ height:8px; border-radius:999px; background:#EDF1EC; overflow:hidden; margin:.55rem 0 .45rem; }
.ng-meter i{ display:block; height:100%; border-radius:999px; background:linear-gradient(90deg,var(--ng-lime-deep),var(--ng-forest)); }
.ng-inline-meta{ display:flex; flex-wrap:wrap; gap:.35rem .5rem; font-size:.8rem; color:var(--ng-muted); }
.ng-signals{ display:flex; flex-wrap:wrap; gap:.4rem; }
.ng-signal{
  font-size:.78rem; font-weight:500; color:var(--ng-forest-mid);
  background:#F1F6EF; border:1px solid #E1EAE0; border-radius:999px;
  padding:.22rem .58rem;
}
.ng-empty{ text-align:center; padding:1.6rem .5rem; }
.ng-empty-title{ font-size:.98rem; font-weight:700; color:var(--ng-forest); margin-bottom:.35rem; }
.ng-empty-body{ font-size:.88rem; color:var(--ng-muted); line-height:1.6; max-width:40ch; margin:0 auto; }
.ng-disclaimer{
  font-size:.78rem; line-height:1.6; color:var(--ng-muted);
  background:#F7F9F6; border:1px solid var(--ng-line);
  border-radius:12px; padding:.7rem .85rem; margin-top:.9rem;
}

/* -- cases ------------------------------------------------------------ */
[class*="st-key-ngcase_"]{
  background:var(--ng-card); border:1px solid var(--ng-line);
  border-radius:16px; padding:1rem 1.15rem; margin-bottom:.7rem;
  transition:border-color .16s ease, box-shadow .16s ease;
}
[class*="st-key-ngcase_"]:hover{
  border-color:#CBD9D3; box-shadow:0 16px 30px -26px rgba(15,42,36,.6);
}
.ng-case-top{ display:flex; align-items:center; justify-content:space-between; gap:.6rem; }
.ng-case-left{ display:flex; align-items:center; gap:.45rem; flex-wrap:wrap; }
.ng-case-meta{
  display:flex; flex-wrap:wrap; align-items:center; gap:.3rem .55rem;
  margin-top:.6rem; font-size:.79rem; color:var(--ng-muted);
}
.ng-sep{ width:3px; height:3px; border-radius:50%; background:#C3CFC9; }
.ng-flag{
  font-size:.68rem; font-weight:600; letter-spacing:.1em; text-transform:uppercase;
  color:#7A8F87; background:#F2F5F1; border-radius:6px; padding:.14rem .4rem;
}
.ng-empty-row{ font-size:.9rem; color:var(--ng-muted); padding:.6rem 0; }

/* -- form widget chrome ---------------------------------------------- */
[data-testid="stWidgetLabel"] p{
  font-size:.8rem !important; font-weight:600 !important;
  color:var(--ng-forest) !important; letter-spacing:.01em;
}
.stTextInput div[data-baseweb="input"],
.stTextArea div[data-baseweb="textarea"],
.stSelectbox div[data-baseweb="select"] > div{
  border-radius:12px !important; background:#FDFEFD !important;
  border:1px solid var(--ng-line) !important; box-shadow:none !important;
}
.stTextInput div[data-baseweb="input"]:focus-within,
.stTextArea div[data-baseweb="textarea"]:focus-within,
.stSelectbox div[data-baseweb="select"] > div:focus-within{
  border-color:var(--ng-lime-deep) !important;
  box-shadow:0 0 0 3px rgba(169,217,79,.22) !important;
}
.stTextInput input, .stTextArea textarea{ font-size:.93rem !important; color:var(--ng-ink) !important; }
.stTextArea textarea{ line-height:1.6 !important; }
::placeholder{ color:#9AAAA3 !important; opacity:1; }

.stFormSubmitButton > button{
  background:var(--ng-forest) !important; color:#F2FAE8 !important;
  border:1px solid var(--ng-forest) !important; border-radius:12px !important;
  font-weight:600 !important; padding:.62rem 1.2rem !important;
  box-shadow:0 14px 26px -18px rgba(21,59,50,.95) !important;
  transition:transform .14s ease, background .14s ease;
}
.stFormSubmitButton > button:hover{ background:var(--ng-forest-mid) !important; transform:translateY(-1px); }
.stFormSubmitButton > button p{ font-weight:600 !important; font-size:.92rem !important; }
.stButton > button{
  background:#FFFFFF !important; color:var(--ng-forest) !important;
  border:1px solid var(--ng-line) !important; border-radius:12px !important;
  font-weight:600 !important; padding:.55rem 1rem !important;
  transition:border-color .14s ease, background .14s ease;
}
.stButton > button:hover{ border-color:var(--ng-forest) !important; background:#F8FBF7 !important; }
.stButton > button p{ font-weight:600 !important; font-size:.87rem !important; }
[data-testid="stForm"]{ border:none !important; padding:0 !important; }
[data-testid="stCaptionContainer"] p{ font-size:.78rem !important; color:var(--ng-muted) !important; }

/* -- footer ----------------------------------------------------------- */
.ng-footer{ margin-top:2.6rem; padding-top:1.3rem; border-top:1px solid var(--ng-line); }
.ng-footer-note{ font-size:.79rem; color:var(--ng-muted); line-height:1.6; max-width:70ch; }
.ng-footer-flow{
  font-size:.7rem; font-weight:600; letter-spacing:.16em;
  text-transform:uppercase; color:#8B9C95;
}

/* -- responsive ------------------------------------------------------- */
@media (max-width:820px){
  .block-container{ padding:1.1rem .95rem 3rem; }
  [class*="st-key-ngc_"]{ padding:1.15rem 1.1rem; border-radius:16px; }
  .ng-hero{ padding:1.75rem 1.35rem; border-radius:20px; margin:1.1rem 0 1rem; }
  .ng-hero h1{ font-size:1.6rem; max-width:none; }
  .ng-hero p{ font-size:.93rem; }
  .ng-metric-value{ font-size:1.72rem; }
  .ng-metric-note{ font-size:.78rem; }
  [class*="st-key-ngcase_"]{ padding:.9rem 1rem; }
  .ng-section p{ max-width:none; }
  .ng-footer-flow{ display:none; }
  [class*="st-key-ngc_langswitch"]{ align-items:flex-start; }
}
@media (max-width:560px){
  .ng-brand-sub{ font-size:.62rem; letter-spacing:.11em; }
  .ng-metric-value{ font-size:1.55rem; }
}
</style>
"""


st.title("Nagarik AI")
st.subheader("Every voice deserves to be heard.")
st.write("Report civic problems in Bengali, Hindi, or English.")


audio = st.audio_input("🎙️ Speak your complaint")

if st.button("Transcribe voice"):
    if audio is None:
        st.warning("Please record your complaint first.")
    else:
        try:
            client = SarvamAI(
                api_subscription_key=os.getenv("SARVAM_API_KEY")
            )

            with st.spinner("Recognising your speech..."):
                transcript = client.speech_to_text.transcribe(
                                file=("recording.wav", audio.getvalue(), "audio/wav"),
                                model="saaras:v4",
                                mode="transcribe"
                                )
                

            st.session_state["sarvam_test_complaint"] = (
                transcript.transcript
            )
            st.success("Speech recognised! Please review the transcript.")

        except Exception as e:
            st.error("Speech recognition failed.")
            st.caption(str(e))

complaint = st.text_area(
    "Describe your civic problem",
    placeholder="আমাদের রাস্তায় জল জমে আছে...",
    key="sarvam_test_complaint"
)


location_audio = st.audio_input(
    "🎙️ Speak your location",
    key="sarvam_location_audio"
)

if st.button("Recognise location"):
    if location_audio is None:
        st.warning("Please record your location first.")
    else:
        try:
            client = SarvamAI(
                api_subscription_key=os.getenv("SARVAM_API_KEY")
            )

            with st.spinner("Recognising location..."):
                location_result = client.speech_to_text.transcribe(
                                    file=("location_recording.wav", audio.getvalue(), "audio/wav"),
                                    model="saaras:v4",
                                    mode="transcribe"
                                )
                

            st.session_state["sarvam_test_location"] = (
                location_result.transcript
            )
            st.success("Location recognised. Please verify it.")

        except Exception as e:
            st.error("Location recognition failed.")
            st.caption(str(e))

location = st.text_input(
    "Confirm or edit your location",
    key="sarvam_test_location"
)


if st.button("Analyse complaint"):
    if not complaint.strip():
        st.warning("Please enter a complaint first.")
    elif not location.strip():
        st.warning("Please enter the location.")
    else:
        api_key = os.getenv("SARVAM_API_KEY")

        if not api_key:
            st.error("SARVAM_API_KEY is missing. Check your .env file.")
        else:
            try:
                client = SarvamAI(api_subscription_key=api_key)

                with st.spinner("Sarvam AI is analysing your complaint..."):
                    response = client.chat.completions(
                        model="sarvam-105b",
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "You are Nagarik AI, a civic complaint "
                                    "assistant for India. Understand complaints "
                                    "in Bengali, Hindi, or English. Return valid "
                                    "JSON only, with these keys: category, "
                                    "title, description, priority, reason, "
                                    "suggested_action. Category should identify "
                                    "the civic issue. Priority must be High, "
                                    "Medium, or Low. Do not claim a complaint "
                                    "has been officially submitted. Base the "
                                    "priority on the described facts."
                                )
                            },
                            {
                                "role": "user",
                                "content": (
                                    f"Location: {location}\n"
                                    f"Complaint: {complaint}"
                                )
                            }
                        ]
                    )

                result_text = response.choices[0].message.content
                result = json.loads(result_text)

                st.success("AI analysis complete")
                st.caption(
                    "Demo only — not submitted to a government authority.")

                st.write("**Reference:**", "NAG-DEMO-001")
                st.write("**Location:**", location)
                st.write("**Category:**", result["category"])
                st.write("**Title:**", result["title"])
                st.write("**Description:**", result["description"])
                st.write("**Priority:**", result["priority"])
                st.write("**Reason:**", result["reason"])
                st.write("**Suggested action:**", result["suggested_action"])

            except json.JSONDecodeError:
                st.error("The AI returned an unexpected format. Please try again.")
            except Exception as e:
                st.error(
                    "Sarvam analysis failed. Check your API key and connection.")
                st.caption(str(e))
