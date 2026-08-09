from app.scraper.extractor import extract_email, extract_phone, extract_website


def test_extract_email_basic():
    assert extract_email("contact: hello@example.com") == "hello@example.com"


def test_extract_email_from_real_bio():
    bio = "blogueira de pele & beauty creator\n📌 São Paulo\n✉️: nahrivellicontato@gmail.com"
    assert extract_email(bio) == "nahrivellicontato@gmail.com"


def test_extract_email_none():
    assert extract_email("no email here") is None
    assert extract_email("") is None
    assert extract_email(None) is None


def test_extract_email_lowercase():
    assert extract_email("EMAIL: User@EXAMPLE.COM") == "user@example.com"


def test_extract_email_obfuscated_brackets():
    """audit H5: 'name [at] domain [dot] com' is documented scraper evasion,
    not an edge case -- exactly the profiles most likely to have
    intentionally-placed contact info."""
    assert extract_email("hello [at] example [dot] com") == "hello@example.com"


def test_extract_email_obfuscated_parens():
    assert extract_email("hello(at)example(dot)com") == "hello@example.com"


def test_extract_email_obfuscated_word_at():
    assert extract_email("reach me at hello [at] example [dot] com please") == "hello@example.com"


def test_extract_email_obfuscated_multi_dot_domain():
    assert extract_email("hello [at] sub [dot] example [dot] com") == "hello@sub.example.com"


def test_extract_email_prose_at_and_dot_not_matched():
    """The obfuscation fallback must not fire on ordinary prose that happens
    to contain the words 'at'/'dot' with no email-shaped shape around them."""
    assert extract_email("Chief at Nike, this dot com era is wild") is None
    assert extract_email("meet me at the beach today") is None


def test_extract_phone_br_9digit():
    assert extract_phone("WhatsApp: 11 98765-4321") is not None


def test_extract_phone_with_ddd():
    bio = "📞 (48) 99845 37246"
    result = extract_phone(bio)
    assert result is not None
    assert len(result) >= 10


def test_extract_phone_none():
    assert extract_phone("no phone here") is None
    assert extract_phone("") is None


def test_extract_phone_none_short_numbers_in_prose():
    assert extract_phone("since 2010, visited 45 countries") is None


def test_extract_phone_us_format():
    """audit H5: the old regex was BR-only, silently failing on every other
    country despite no stated BR-only scope."""
    result = extract_phone("call +1 (555) 123-4567 anytime")
    assert result == "15551234567"


def test_extract_phone_uk_format():
    result = extract_phone("+44 20 7946 0958")
    assert result == "442079460958"


def test_extract_phone_keycap_emoji_digits():
    """audit H5: keycap number emoji (0️⃣-9️⃣) are a documented digit-obfuscation
    evasion -- look like digits to a human, don't match a naive \\d regex."""
    result = extract_phone("\U0001f4de 1️⃣1️⃣9️⃣9️⃣9️⃣9️⃣8️⃣8️⃣8️⃣8️⃣8️⃣")
    assert result == "11999988888"


def test_extract_website_from_external_url():
    result = extract_website("any bio", "https://mystore.com.br/shop")
    assert result == "https://mystore.com.br/shop"


def test_extract_website_skips_linktree():
    result = extract_website("any bio", "https://linktr.ee/myprofile")
    assert result is None


def test_extract_website_from_bio():
    bio = "check out https://mybrand.com for more"
    result = extract_website(bio)
    assert result == "https://mybrand.com"


def test_extract_website_skips_wa_me():
    bio = "contact http://wa.me/5511999999"
    result = extract_website(bio)
    assert result is None
