import pytest

from backend.normalize import normalize, normalize_words, remove_small


def test_strips_harakat():
    assert normalize("بِسْمِ") == "بسم"
    assert normalize("ٱلرَّحِيمِ") == "الرحيم"
    assert normalize("نَعْبُدُ") == "نعبد"


def test_strips_quranic_marks():
    assert normalize("ٱلرَّحْمَٰنِ") == "الرحمان"
    assert normalize("ٱلضَّآلِّينَ") == "الضالين"


def test_unifies_alef_variants():
    assert normalize("إِيَّاكَ") == "اياك"
    assert normalize("آمَنَ") == "امن"
    assert normalize("أَرْضٌ") == "ارض"
    assert normalize("ٱهْدِنَا") == "اهدنا"


def test_ta_marbuta_to_ha():
    assert normalize("رَحْمَةٍ") == "رحمه"


def test_alif_maqsura_to_ya():
    assert normalize("مُصْطَفَى") == "مصطفي"


def test_hamza_removed_or_unified():
    assert normalize("شَيْءٍ") == "شي"
    assert normalize("مِائَتَيْنِ") == "مايتين"


def test_tatweel_removed():
    assert normalize("سَمِــــيع") == "سميع"


def test_superscript_alif_to_full_alef():
    assert normalize("مَٰلِكِ") == "مالك"
    assert normalize("ٱلسَّمَٰوَٰتِ") == "السماوات"


def test_whitespace_collapsed():
    assert normalize("بِسْمِ  ٱللَّهِ   ٱلرَّحِيمِ") == "بسم الله الرحيم"


def test_full_ayat():
    assert normalize("بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ") == "بسم الله الرحمان الرحيم"


def test_normalize_words_list():
    assert normalize_words(["بِسْمِ", "ٱللَّهِ"]) == ["بسم", "الله"]


def test_remove_small_strips_digits():
    assert remove_small("١") == ""
    assert remove_small("بِسْمِ") == "بِسْمِ"
