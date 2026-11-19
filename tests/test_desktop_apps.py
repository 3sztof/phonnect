from phonnect.desktop_apps import App, apps_from, parse_app_labels, parse_display_tasks, parse_launcher_activities

QUERY = """com.android.calculator2/.Calculator
com.android.chrome/com.google.android.apps.chrome.Main
com.android.chrome/.SecondEntry
"""

LIST_APPS = """[server] INFO: List of apps:
 * Calculator                     com.android.calculator2
 - Chrome                         com.android.chrome
 * Files by Google                com.google.android.apps.nbu.files
"""

DUMPSYS = """Display #0 (activities from top to bottom):
  * Task{a1 #10 type=standard A=10001:com.android.chrome U=0 visible=true mode=fullscreen translucent=false sz=1}
Display #17 (activities from top to bottom):
  * Task{b2 #3287 type=standard A=10095:com.android.calculator2 minWidth=230 U=0 visible=true mode=freeform x}
    * Task{c3 #3287 type=standard A=10095:com.android.calculator2 U=0 mode=freeform x}
  * Task{d4 #3290 type=home A=10112:com.android.launcher3 U=0 mode=fullscreen x}
  * Task{e5 #3291 type=standard A=10050:com.android.documentsui U=0 visible=true mode=fullscreen x}
"""


def test_launcher_activities_one_per_app():
    assert parse_launcher_activities(QUERY) == {
        "com.android.calculator2": "com.android.calculator2/.Calculator",
        "com.android.chrome": "com.android.chrome/com.google.android.apps.chrome.Main",
    }


def test_app_names_from_scrcpy():
    labels = parse_app_labels(LIST_APPS)
    assert labels["com.android.chrome"] == "Chrome"
    assert labels["com.google.android.apps.nbu.files"] == "Files by Google"


def test_apps_are_sorted_by_name_and_fall_back_to_the_package():
    apps = apps_from(parse_launcher_activities(QUERY), {"com.android.chrome": "Chrome"})
    assert [a.label for a in apps] == ["calculator2", "Chrome"]
    assert apps[1] == App("Chrome", "com.android.chrome", "com.android.chrome/com.google.android.apps.chrome.Main")


def test_only_apps_on_the_desktop_display_count():
    assert parse_display_tasks(DUMPSYS, 17) == [
        (3287, "com.android.calculator2", "freeform"),
        (3291, "com.android.documentsui", "fullscreen"),
    ]
    assert parse_display_tasks(DUMPSYS, 5) == []
