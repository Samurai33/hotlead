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
