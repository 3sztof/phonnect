import pytest

from phonnect import theme


def test_palettes_differ():
    assert theme.LIGHT != theme.DARK


def test_apply_never_raises_and_returns_palette():
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    try:
        root.withdraw()
        assert theme.apply(root) in (theme.LIGHT, theme.DARK)
        root.update()
    finally:
        root.destroy()


def test_tray_menu_theme_is_safe_to_call():
    theme.match_tray_menu_theme()
