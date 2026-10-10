from app.config import parse_origins


def test_parse_origins_strips_spaces_and_trailing_slashes():
    assert parse_origins("https://a.vercel.app/, http://localhost:5173 ,") == [
        "https://a.vercel.app",
        "http://localhost:5173",
    ]
