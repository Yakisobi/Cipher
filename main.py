import itertools
import json
import math
import os
import secrets
import string
import sys
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from tkinter import messagebox


SETTINGS_PATH = Path.home() / ".cipher_password_generator.json"
SETTINGS_VERSION = 2

THEMES = {
    "Neon Dark": dict(
        bg="#080b14", panel="#0f1424", panel2="#151b30", border="#1f2845",
        text="#d7e0ff", muted="#6b7aa8", cyan="#00e5ff", magenta="#ff2bd6",
        green="#2dff8f", yellow="#ffd23f", red="#ff4d6d",
        btn_fg="#080b14", hover="#d7e0ff"),
    "Midnight": dict(
        bg="#0d1117", panel="#161b22", panel2="#1f2630", border="#30363d",
        text="#e6edf3", muted="#8b949e", cyan="#58a6ff", magenta="#bc8cff",
        green="#3fb950", yellow="#d29922", red="#f85149",
        btn_fg="#0d1117", hover="#e6edf3"),
    "Light": dict(
        bg="#f4f6fb", panel="#ffffff", panel2="#e8ecf6", border="#c9d1e8",
        text="#1b2340", muted="#5b678f", cyan="#0069b4", magenta="#b0127f",
        green="#0b7a42", yellow="#a56a00", red="#c62839",
        btn_fg="#ffffff", hover="#1b2340"),
}
C = dict(THEMES["Neon Dark"])


def set_theme(name):
    C.update(THEMES.get(name, THEMES["Neon Dark"]))


if sys.platform.startswith("win"):
    UI_FAMILY, MONO_FAMILY = "Segoe UI", "Consolas"
elif sys.platform == "darwin":
    UI_FAMILY, MONO_FAMILY = "Helvetica Neue", "Menlo"
else:
    UI_FAMILY, MONO_FAMILY = "DejaVu Sans", "DejaVu Sans Mono"


def ui(size, bold=False):
    return (UI_FAMILY, size, "bold") if bold else (UI_FAMILY, size)


def mono(size, bold=False):
    return (MONO_FAMILY, size, "bold") if bold else (MONO_FAMILY, size)


AMBIGUOUS = set("Il1O0o|`'\"")
DEFAULT_SYMBOLS = "!@#$%^&*()-_=+[]{};:,.<>?/~"
EASY_SYMBOLS = "!@#$%&?-_."
SCRAMBLE_CHARS = string.ascii_letters + string.digits + "!@#$%^&*?+=~"
MASK_CHAR = "\u2022"
CLIP_CHOICES = [("Off (never clear)", 0), ("15 seconds", 15), ("30 seconds", 30),
                ("60 seconds", 60), ("2 minutes", 120)]

CHAR_KEYS = ["length", "upper", "lower", "digits", "symbols", "symbol_set",
             "no_ambig", "easy", "require_each"]
PHRASE_KEYS = ["words", "separator", "capitalize", "add_number"]

DEFAULTS = {

    "preset": "Strong", "length": 20, "upper": True, "lower": True, "digits": True,
    "symbols": True, "symbol_set": DEFAULT_SYMBOLS, "no_ambig": False, "easy": False,
    "require_each": True,

    "words": 9, "separator": "-", "capitalize": True, "add_number": True,

    "theme": "Neon Dark", "min_len": 8, "max_len": 128, "animate": True,
    "clip_secs": 30, "keep_history": False, "history_size": 5, "hidden": False,

    "settings_version": SETTINGS_VERSION,
}

PRESETS = {
    "Everyday": dict(
        desc="16 characters, letters and numbers. Good for most accounts.",
        fmt="aA9aaAa9aaA9aAaa",
        values=dict(length=16, upper=True, lower=True, digits=True, symbols=False,
                    no_ambig=False, easy=False, require_each=True)),
    "Strong": dict(
        desc="20 characters, all character types. A solid default.",
        fmt="aA9#aaA#a9aA#aa9A#aa",
        values=dict(length=20, upper=True, lower=True, digits=True, symbols=True,
                    no_ambig=False, easy=False, require_each=True)),
    "Maximum": dict(
        desc="32 characters, all character types. For email, banking, password-manager master keys.",
        fmt="aA9#aaA#a9aA#aa9A#aaaA9#aaA#a9aA",
        values=dict(length=32, upper=True, lower=True, digits=True, symbols=True,
                    no_ambig=False, easy=False, require_each=True)),
    "Easy to Type": dict(
        desc="16 characters. No look-alikes (I l 1 O 0 o) and only simple symbols.",
        fmt="aaA9-aaA_aaA9aaA?",
        values=dict(length=16, upper=True, lower=True, digits=True, symbols=True,
                    no_ambig=True, easy=True, require_each=True)),
    "Passphrase": dict(
        desc="9 random words plus an optional two-digit number. Longer but easier to remember and type.",
        fmt="Word-Word-Word-Word-Word-Word-Word-Word-Word-42",
        values=dict(words=9, separator="-", capitalize=True, add_number=True)),
    "Custom": dict(
        desc="Uses your own settings. Change anything on the left.",
        fmt=None, values={}),
}
FORMAT_KEY = "Format key:  a lower  \u00b7  A upper  \u00b7  9 number  \u00b7  # symbol"

TIPS = {
    "length": "Length matters most. Every extra character multiplies the number of possible passwords. "
              "16+ is fine for everyday accounts, 20+ for important ones.",
    "upper": "Uppercase letters A\u2013Z (e.g. K). Adds 26 possibilities per position.",
    "lower": "Lowercase letters a\u2013z (e.g. q). Adds 26 possibilities per position.",
    "digits": "Numbers 0\u20139 (e.g. 7). Adds 10 possibilities per position.",
    "symbols": "Punctuation such as ! @ # $. Adds strength, but a few websites reject some symbols.",
    "symbol_set": "Which symbols may be used. Remove any that a particular website doesn't accept. "
                  "Letters and digits typed here are ignored.",
    "no_ambig": "Leaves out characters that are easy to confuse when read: I (capital i), l (lowercase L), "
                "1, O, 0, o. Slightly reduces the pool.",
    "easy": "Easy-to-type mode: no look-alike characters, and only simple symbols (" + EASY_SYMBOLS + ").",
    "require_each": "Guarantees at least one character from every selected type (needed by some sites). "
                    "Strength estimates account for this rule.",
    "words": "Number of random words. Each word adds about 8.9 bits with the built-in list "
              "(about 12.9 with a large wordlist.txt). Nine words plus the two-digit number provide about 86 bits.",
    "separator": "Text placed between words (up to 3 characters). Leave empty for none.",
    "capitalize": "Capitalise the first letter of each word. Helps with sites that require capitals; "
                  "adds no strength because it's predictable.",
    "add_number": "Adds a random two-digit number (00\u201399) at the end. Adds about 6.6 bits.",
}

GUIDE = [
    ("Character types",
     "Uppercase = capital letters (A\u2013Z).  Lowercase = small letters (a\u2013z).  "
     "Digits = numbers (0\u20139).  Symbols = punctuation such as ! @ # $ %.\n"
     "Turning more types on gives each position more possible characters."),
    ("Password length",
     "Length is the biggest lever. Each extra character multiplies the number of possible passwords "
     "by the size of the character pool, so strength grows exponentially with length."),
    ("Estimated strength",
     "CIPHER shows an estimate in \u201cbits\u201d: every extra bit doubles the guesses needed. "
     "It is computed from the real rules used to generate the password (including \u201crequire one of each type\u201d) "
     "and assumes an attacker knows your settings but not the password.\n"
     "It is an estimate, not a guarantee: no password is ever \u201cunbreakable\u201d, and reusing a password "
     "or typing it into a phishing site defeats any strength."),
    ("Why random and long beats clever",
     "Humans are predictable (names, dates, l33t substitutions). Truly random characters from the "
     "operating system's secure generator have no pattern to exploit, so only length and pool size count."),
    ("Passphrases",
     "Several random words are easier to remember and type than random symbols. Strength depends on the "
     "word-list size: the built-in list gives roughly 9 bits per word. Drop a larger wordlist.txt "
     "(such as the EFF large list, ~12.9 bits/word) next to this script to use it automatically."),
    ("Presets",
     "Everyday: 16 chars, letters+numbers.  Strong: 20 chars, all types.  Maximum: 32 chars, all types.  "
     "Easy to Type: no look-alikes, simple symbols.  Passphrase: random words.  "
     "Custom: whatever you set yourself. Changing any control switches to Custom."),
    ("Privacy and copy safety",
     "Passwords are never saved to disk by CIPHER or sent online. Preferences are stored locally in a JSON settings file. "
     "Recent history is opt-in and stays in memory while the app runs. Batch results also remain in memory until cleared "
     "or the app closes. Clipboard auto-clear tries to remove the copied value after the selected delay, but it only clears "
     "when the clipboard still contains the value CIPHER copied. It cannot remove copies retained by every clipboard manager "
     "or another application."),
    ("Keyboard shortcuts",
     "Ctrl+G  generate again\nCtrl+Shift+C  copy password\nF2  show / hide password\n"
     "Ctrl+,  settings\nF1  this guide\nDouble-click the password to select it all."),
]

WORDS_BUILTIN = """
able acorn actor adobe agent aisle album alder alley alpine amber ankle anvil apple apron arbor arch
arena armor arrow aspen atlas attic aurora autumn avenue award bacon badge bagel baker bamboo banjo
barn basil basin basket beach beacon beam beaver bench berry bicycle birch bison blade blanket blaze
blend bloom blossom bluff boat bolt bonus boots border bottle boulder bounce bowl branch brass bread
breeze brick bridge bright brisk bronze brook broom brush bubble bucket buffalo bundle butter button
cabin cable cactus cadet camel camera campus candle candy canoe canvas canyon cape captain carbon
cargo carpet carrot castle cattle cedar cellar cereal chair chalk champion channel chapel charm
cheese cherry chess chime chimney cider cinder circle citrus clay clever cliff climb clock cloud
clover cobalt cocoa coffee comet compass copper coral cotton couch cougar cove coyote cradle crane
crayon creek crest cricket crimson crisp crown crumb crystal cube cuckoo curtain cycle daisy dancer
dawn deck delta denim desert diamond dinner dolphin dome donkey dragon drift drum dune eagle earth
easel echo eclipse elbow elder elm ember emerald engine envoy fabric falcon fancy farm feather fern
ferry fiddle field figure finch fjord flame flannel flint flute foam forest fossil fox frame frost
fruit galaxy garden garlic gazelle gear ginger glacier glider globe glove goat goblet golden goose
gopher granite grape gravel grove guitar gulf habit hammer harbor harvest hawk hazel heron hill
hollow honey horizon hornet hotel humble icicle igloo inlet iris iron island ivory jacket jaguar
jasmine jelly jewel jigsaw jungle juniper kayak kernel kettle kingdom kitten koala ladder lagoon
lake lamp lantern lark laser lava lemon lentil lever library lilac linen lion lizard lobby lotus
lunar lynx magnet mango maple marble marsh meadow melon mesa meteor mint mirror mist mitten monkey
moon moss motor mountain muffin mulberry nectar needle nest nickel noble north nutmeg oak oasis
ocean olive onion opal orbit orchard orchid otter oval oyster paddle palace palm panda panther
paper parade parrot pasta pearl pebble pelican pencil penguin pepper piano picnic pigeon pillow
pilot pine pioneer planet plaza plum pocket polar pond poplar poppy portal prairie prism pudding
pumpkin puzzle quail quartz quest quiet quill rabbit radar radio raft rain rainbow raven reef
ribbon ridge river robin rocket rose saddle saffron sage sailor salmon sand sapphire satin scarf
school scout season shadow shell shore signal silk silver sketch skiff slate sleet slope snow solar
sparrow spice spider spiral splash spring spruce squirrel stable star steam stone storm stream
summit sunset swan swift table tangerine temple tennis thistle thunder tiger timber toast tomato
topaz tower trail train tulip tundra tunnel turtle twig umber umbrella valley vanilla velvet
village vine violet voyage walnut walrus water wave weasel wheat whale willow window winter wolf
wonder woods yacht yarn yellow zebra zephyr zinc
"""


def load_wordlist(path=None):
    """Load an optional wordlist, or use the built-in list when it is missing/invalid."""
    builtin = list(dict.fromkeys(WORDS_BUILTIN.split()))
    try:
        path = Path(path) if path is not None else Path(__file__).with_name("wordlist.txt")
        if path.is_file():
            words = []
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                parts = line.strip().split()
                if parts:
                    w = parts[-1].lower()
                    if w.isalpha() and 3 <= len(w) <= 12:
                        words.append(w)
            words = list(dict.fromkeys(words))
            if len(words) >= 256:
                return words, "wordlist.txt"
    except OSError:
        pass
    return builtin, "built-in"

def clean_symbols(raw):
    """Keep printable ASCII symbols only. Returns (cleaned, dropped_something)."""
    kept = "".join(dict.fromkeys(
        c for c in raw if c in string.punctuation))
    return kept, len(kept) != len("".join(dict.fromkeys(raw)))


def build_pools(use_upper, use_lower, use_digits, use_symbols, symbols, avoid_ambiguous):
    """Returns [(name, characters)]. Raises ValueError if a selected type ends up empty."""
    wanted = []
    if use_upper:
        wanted.append(("uppercase", string.ascii_uppercase))
    if use_lower:
        wanted.append(("lowercase", string.ascii_lowercase))
    if use_digits:
        wanted.append(("numbers", string.digits))
    if use_symbols:
        wanted.append(("symbols", "".join(dict.fromkeys(symbols))))
    if not wanted:
        raise ValueError("Select at least one character type.")
    pools = []
    for name, chars in wanted:
        if avoid_ambiguous:
            chars = "".join(c for c in chars if c not in AMBIGUOUS)
        if not chars:
            raise ValueError(f"No {name} characters are left after exclusions. "
                             f"Adjust the symbol list or turn off look-alike filtering.")
        pools.append((name, chars))
    return pools


def generate_password(length, pools, require_each=True, max_tries=200_000):
    """Uniformly random password over the allowed characters.

    When `require_each` is on we use rejection sampling: draw uniformly from the
    combined pool and retry until every selected set is present. That keeps the
    result uniform over the valid set, so the entropy figure is exact.
    """
    pools = [p for p in pools if p]
    combined = "".join(dict.fromkeys("".join(pools)))
    if not combined:
        raise ValueError("No characters available.")
    if length < 1:
        raise ValueError("Length must be at least 1.")
    check = require_each and len(pools) > 1
    if check and length < len(pools):
        raise ValueError(f"Length {length} is too short to include all {len(pools)} selected types.")
    sets = [set(p) for p in pools]
    for _ in range(max_tries):
        pw = "".join(secrets.choice(combined) for _ in range(length))
        if not check or all(not s.isdisjoint(pw) for s in sets):
            return pw
    raise ValueError("Couldn't satisfy the rules. Try a longer length or fewer restrictions.")


def entropy_bits(length, pools, require_each=True):
    """Exact log2 of the number of valid passwords (inclusion-exclusion when each
    selected type is required)."""
    sets = [set(p) for p in pools if p]
    if not sets:
        return 0.0
    n = len(set().union(*sets))
    if not require_each or len(sets) == 1:
        count = n ** length
    else:
        count = 0
        for r in range(len(sets) + 1):
            for combo in itertools.combinations(range(len(sets)), r):
                union = set().union(*(sets[i] for i in combo)) if combo else set()
                count += (-1) ** r * (n - len(union)) ** length
    return math.log2(count) if count > 1 else 0.0


def generate_passphrase(words, count, sep="-", capitalize=True, add_number=False):
    parts = [secrets.choice(words) for _ in range(count)]
    if capitalize:
        parts = [w.capitalize() for w in parts]
    if add_number:
        parts.append(f"{secrets.randbelow(100):02d}")
    return sep.join(parts)


def passphrase_bits(n_words_in_list, count, add_number=False):
    bits = count * math.log2(n_words_in_list)
    return bits + (math.log2(100) if add_number else 0.0)


def clipboard_matches(current_value, copied_value):
    """Only clear a clipboard value if it still matches what CIPHER copied."""
    return bool(copied_value) and current_value == copied_value


def rate(bits):
    """Estimate labels. Deliberately never absolute."""
    if bits < 40:
        return "WEAK", "red"
    if bits < 60:
        return "FAIR", "yellow"
    if bits < 80:
        return "STRONG", "green"
    if bits < 112:
        return "VERY STRONG", "cyan"
    return "EXCELLENT", "magenta"


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def sanitize(raw):
    cfg = dict(DEFAULTS)
    if not isinstance(raw, dict):
        return cfg
    raw_version = raw.get("settings_version")
    is_legacy_settings = (not isinstance(raw_version, int) or isinstance(raw_version, bool)
                          or raw_version < SETTINGS_VERSION)
    for k, default in DEFAULTS.items():
        v = raw.get(k, default)
        if isinstance(default, bool):
            cfg[k] = v if isinstance(v, bool) else default
        elif isinstance(default, int):
            cfg[k] = v if isinstance(v, int) and not isinstance(v, bool) else default
        else:
            cfg[k] = v if isinstance(v, str) else default
    if cfg["theme"] not in THEMES:
        cfg["theme"] = DEFAULTS["theme"]
    if cfg["preset"] not in PRESETS:
        cfg["preset"] = DEFAULTS["preset"]
    cfg["min_len"] = _clamp(cfg["min_len"], 1, 64)
    cfg["max_len"] = _clamp(cfg["max_len"], 8, 256)
    if cfg["max_len"] <= cfg["min_len"]:
        cfg["min_len"], cfg["max_len"] = DEFAULTS["min_len"], DEFAULTS["max_len"]
    cfg["length"] = _clamp(cfg["length"], cfg["min_len"], cfg["max_len"])
    cfg["words"] = _clamp(cfg["words"], 4, 10)
    cfg["history_size"] = _clamp(cfg["history_size"], 1, 10)
    if cfg["clip_secs"] not in [s for _, s in CLIP_CHOICES]:
        cfg["clip_secs"] = DEFAULTS["clip_secs"]
    cfg["separator"] = "".join(c for c in cfg["separator"] if c.isprintable())[:3]
    cfg["symbol_set"] = cfg["symbol_set"][:64]

    cfg["settings_version"] = SETTINGS_VERSION
    if is_legacy_settings:
        cfg["keep_history"] = False
    return cfg


def load_settings():
    try:
        return sanitize(json.loads(SETTINGS_PATH.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return dict(DEFAULTS)


def save_settings(cfg):
    try:
        tmp = SETTINGS_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, SETTINGS_PATH)
    except OSError:
        pass



class Tooltip:
    def __init__(self, widget, text, delay=450):
        self.widget, self.text, self.delay = widget, text, delay
        self.tip, self._job = None, None
        widget.bind("<Enter>", self._enter, add="+")
        widget.bind("<Leave>", self._leave, add="+")
        widget.bind("<ButtonPress>", self._leave, add="+")

    def _enter(self, _=None):
        self._cancel()
        self._job = self.widget.after(self.delay, self._show)

    def _cancel(self):
        if self._job:
            try:
                self.widget.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None

    def _show(self):
        if self.tip:
            return
        try:
            x = self.widget.winfo_rootx() + 16
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
            self.tip = tk.Toplevel(self.widget)
            self.tip.wm_overrideredirect(True)
            self.tip.wm_geometry(f"+{x}+{y}")
            tk.Label(self.tip, text=self.text, justify="left", wraplength=300,
                     bg=C["panel2"], fg=C["text"], relief="solid", bd=1,
                     padx=10, pady=6, font=ui(10)).pack()
        except tk.TclError:
            self.tip = None

    def _leave(self, _=None):
        self._cancel()
        if self.tip:
            try:
                self.tip.destroy()
            except tk.TclError:
                pass
            self.tip = None


class NeonButton(tk.Label):
    def __init__(self, master, text, command, bg=None, fg=None, hover=None, size=11, **kw):
        bg = bg or C["cyan"]
        fg = fg or C["btn_fg"]
        super().__init__(master, text=text, fg=fg, bg=bg, font=ui(size, True),
                         pady=9, padx=12, cursor="hand2", **kw)
        self.base_bg, self.command = bg, command
        self.hover_bg = hover or C["hover"]
        self.bind("<Button-1>", lambda e: self.command())
        self.bind("<Enter>", lambda e: self.config(bg=self.hover_bg))
        self.bind("<Leave>", lambda e: self.config(bg=self.base_bg))


class Chip(tk.Label):
    """Small selectable pill used for presets, tabs and mini-actions."""
    def __init__(self, master, text, command, size=10, selected=False):
        super().__init__(master, text=text, font=ui(size, True), padx=10, pady=6,
                         cursor="hand2", bd=0)
        self.command, self.selected = command, selected
        self.bind("<Button-1>", lambda e: self.command())
        self.bind("<Enter>", lambda e: self._paint(True))
        self.bind("<Leave>", lambda e: self._paint(False))
        self._paint(False)

    def _paint(self, hover):
        if self.selected:
            bg, fg = C["cyan"], C["btn_fg"]
        elif hover:
            bg, fg = C["border"], C["text"]
        else:
            bg, fg = C["panel2"], C["text"]
        self.config(bg=bg, fg=fg)

    def set_selected(self, sel):
        self.selected = sel
        self._paint(False)


def autowrap(label, parent, pad=0):
    parent.bind("<Configure>",
                lambda e: label.config(wraplength=max(120, e.width - pad)), add="+")



class App(tk.Tk):
    def __init__(self):
        super().__init__()
        cfg = load_settings()
        set_theme(cfg["theme"])
        self.title("CIPHER // Password Generator")
        self.geometry("1280x720")
        self.minsize(980, 640)
        self.configure(bg=C["bg"])

        self.words, self.words_source = load_wordlist()


        self.vars = {}
        for k, v in cfg.items():
            if isinstance(v, bool):
                self.vars[k] = tk.BooleanVar(value=v)
            elif isinstance(v, int):
                self.vars[k] = tk.IntVar(value=v)
            else:
                self.vars[k] = tk.StringVar(value=v)
        self.preset = self.vars["preset"]
        self.hidden = self.vars["hidden"]
        for k in CHAR_KEYS:
            self.vars[k].trace_add("write", lambda *_: self._on_var("char"))
        for k in PHRASE_KEYS:
            self.vars[k].trace_add("write", lambda *_: self._on_var("phrase"))


        self.password, self.plan = "", None
        self._settings_dirty = True
        self.advanced_open = False
        self.history, self.batch = [], []
        self.list_mode = "recent"
        self._list_items = []
        self._applying = 0
        self._custom_snap = None
        self._anim_job = self._clip_job = self._save_job = None
        self._clip_text = ""
        self._dlg = self._guide = None
        self._fit_key = None
        self._bar_state = (0.0, "green")
        self._sb_visible = False

        self._build_menu()
        self._rebuild()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Control-g>", lambda e: self.generate_again())
        self.bind("<Control-G>", lambda e: self.generate_again())
        self.bind("<Control-Shift-C>", lambda e: self.copy())
        self.bind("<F2>", lambda e: self.toggle_hidden())
        self.bind("<F1>", lambda e: self.open_guide())
        self.bind("<Control-comma>", lambda e: self.open_settings())

        self._update_preview_estimate(initial=True)


    def _build_menu(self):
        bar = tk.Menu(self)
        s = tk.Menu(bar, tearoff=0)
        s.add_command(label="Preferences\u2026", accelerator="Ctrl+,", command=self.open_settings)
        s.add_command(label="Reset to Defaults\u2026", command=self.reset_defaults)
        s.add_separator()
        s.add_command(label="Clear recent & batch lists", command=self.clear_lists)
        s.add_separator()
        s.add_command(label="Quit", command=self._on_close)
        bar.add_cascade(label="Settings", menu=s)
        h = tk.Menu(bar, tearoff=0)
        h.add_command(label="Guide & explanations", accelerator="F1", command=self.open_guide)
        h.add_command(label="About", command=lambda: messagebox.showinfo(
            "About CIPHER",
            "CIPHER password generator\n\nRandomness: Python 'secrets' (OS CSPRNG).\n"
            "Passwords are never saved to disk by CIPHER or sent online.\n"
            "Preferences are stored locally. Recent history is opt-in; batch results remain in memory until cleared or exit.\n"
            f"{SETTINGS_PATH}"))
        bar.add_cascade(label="Help", menu=h)
        self.config(menu=bar)


    def _rebuild(self):
        self._cancel_anim()
        if getattr(self, "shell", None):
            self.shell.destroy()
        self.configure(bg=C["bg"])
        self.shell = tk.Frame(self, bg=C["bg"])
        self.shell.pack(fill="both", expand=True)
        self._fit_key = None
        self._build(self.shell)
        self._refresh_ui_state()
        self._refresh_list()
        if self.plan is not None:
            self._load(self.password, self.plan)
        else:
            self._show("")

    def _build(self, shell):
        head = tk.Frame(shell, bg=C["bg"])
        head.pack(fill="x", padx=32, pady=(20, 8))
        tk.Label(head, text="CIPHER", fg=C["cyan"], bg=C["bg"], font=ui(28, True)).pack(side="left")
        tk.Label(head, text="//  SECURE PASSWORD GENERATOR", fg=C["muted"], bg=C["bg"],
                 font=ui(13)).pack(side="left", padx=14, pady=(10, 0))
        gear = NeonButton(head, "\u2699  SETTINGS", self.open_settings, bg=C["panel2"],
                          fg=C["text"], hover=C["border"], size=10)
        gear.pack(side="right")
        Tooltip(gear, "Preferences, theme, clipboard and history options (Ctrl+,)")
        tk.Label(head,
                 text="Passwords are never saved to disk or sent online.\nPreferences are stored locally.",
                 fg=C["muted"], bg=C["bg"], font=ui(9), justify="right",
                 wraplength=320).pack(side="right", padx=16, pady=(8, 0))
        tk.Frame(shell, bg=C["magenta"], height=2).pack(fill="x", padx=32)

        body = tk.Frame(shell, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=32, pady=(16, 22))
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=C["panel"], width=390,
                        highlightbackground=C["border"], highlightthickness=1)
        left.grid(row=0, column=0, sticky="ns")
        left.pack_propagate(False)
        self._settings(left)

        right = tk.Frame(body, bg=C["bg"])
        right.grid(row=0, column=1, sticky="nsew", padx=(24, 0))
        self._output(right)

    def _section(self, parent, text):
        tk.Label(parent, text=text, fg=C["magenta"], bg=C["panel"],
                 font=ui(10, True)).pack(anchor="w", padx=20, pady=(16, 6))

    def _check(self, parent, text, key):
        cb = tk.Checkbutton(parent, text=text, variable=self.vars[key], fg=C["text"],
                            bg=C["panel"], font=ui(11), selectcolor=C["panel2"],
                            activebackground=C["panel"], activeforeground=C["cyan"],
                            highlightthickness=0, bd=0, anchor="w", cursor="hand2")
        cb.pack(fill="x", padx=20, pady=2)
        Tooltip(cb, TIPS[key])
        return cb

    def _scale(self, parent, key, lo, hi):
        row = tk.Frame(parent, bg=C["panel"])
        row.pack(fill="x", padx=20)
        lbl = tk.Label(row, text="", fg=C["cyan"], bg=C["panel"], font=mono(22, True),
                       width=4, anchor="e")
        lbl.pack(side="right")
        sc = tk.Scale(row, from_=lo, to=hi, orient="horizontal", variable=self.vars[key],
                      showvalue=False, bg=C["muted"], fg=C["text"], troughcolor=C["panel2"],
                      activebackground=C["cyan"], highlightthickness=0, bd=0,
                      sliderrelief="flat", sliderlength=22, width=16)
        sc.pack(side="left", fill="x", expand=True)
        Tooltip(sc, TIPS[key])
        return sc, lbl

    def _entry(self, parent, key, width=None):
        e = tk.Entry(parent, textvariable=self.vars[key], bg=C["panel2"], fg=C["cyan"],
                     insertbackground=C["cyan"], relief="flat", font=mono(12),
                     highlightbackground=C["border"], highlightcolor=C["cyan"],
                     highlightthickness=1, **({"width": width} if width else {}))
        Tooltip(e, TIPS[key])
        return e

    def _settings(self, left):
        NeonButton(left, "GENERATE", self.generate_again).pack(
            side="bottom", fill="x", padx=20, pady=(8, 20))

        self.sb = tk.Scrollbar(left, orient="vertical", width=10, troughcolor=C["panel2"],
                               bg=C["border"], bd=0, highlightthickness=0)
        self.canvas = tk.Canvas(left, bg=C["panel"], highlightthickness=0, bd=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.configure(yscrollcommand=self.sb.set)
        self.sb.configure(command=self.canvas.yview)
        p = tk.Frame(self.canvas, bg=C["panel"])
        win = self.canvas.create_window((0, 0), window=p, anchor="nw")
        p.bind("<Configure>", lambda e: (
            self.canvas.configure(scrollregion=self.canvas.bbox("all")), self._sync_scroll()))
        self.canvas.bind("<Configure>", lambda e: (
            self.canvas.itemconfigure(win, width=e.width), self._sync_scroll()))
        self._inner = p
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            left.bind_all(seq, self._wheel, add="+")


        self._section(p, "PRESET")
        grid = tk.Frame(p, bg=C["panel"])
        grid.pack(fill="x", padx=17)
        self.preset_chips = {}
        for i, name in enumerate(PRESETS):
            chip = Chip(grid, name, lambda n=name: self.apply_preset(n))
            chip.grid(row=i // 3, column=i % 3, sticky="ew", padx=3, pady=3)
            grid.columnconfigure(i % 3, weight=1, uniform="chip")
            self.preset_chips[name] = chip
            Tooltip(chip, PRESETS[name]["desc"])
        self.preset_desc = tk.Label(p, text="", fg=C["muted"], bg=C["panel"], font=ui(10),
                                    justify="left", anchor="w")
        self.preset_desc.pack(fill="x", padx=20, pady=(8, 0))
        autowrap(self.preset_desc, p, pad=40)

        self.mode_box = tk.Frame(p, bg=C["panel"])
        self.mode_box.pack(fill="x")


        cf = self.char_frame = tk.Frame(self.mode_box, bg=C["panel"])
        self._section(cf, "LENGTH")
        self.len_scale, self.len_label = self._scale(
            cf, "length", self.vars["min_len"].get(), self.vars["max_len"].get())
        self._section(cf, "CHARACTER TYPES")
        self._check(cf, "Uppercase letters  (A\u2013Z, e.g. K)", "upper")
        self._check(cf, "Lowercase letters  (a\u2013z, e.g. q)", "lower")
        self._check(cf, "Numbers  (0\u20139, e.g. 7)", "digits")
        self._check(cf, "Symbols  (e.g. ! @ #)", "symbols")
        self.advanced_toggle = tk.Label(
            cf, text="\u25b8  ADVANCED OPTIONS", fg=C["cyan"], bg=C["panel"],
            font=ui(10, True), cursor="hand2", anchor="w")
        self.advanced_toggle.pack(fill="x", padx=20, pady=(14, 4))
        self.advanced_toggle.bind("<Button-1>", lambda _e: self._toggle_advanced())
        self.advanced_frame = tk.Frame(cf, bg=C["panel"])
        if self.advanced_open:
            self.advanced_frame.pack(fill="x")
            self.advanced_toggle.config(text="\u25be  ADVANCED OPTIONS")
        self._section(self.advanced_frame, "CUSTOM SYMBOLS")
        self._entry(self.advanced_frame, "symbol_set").pack(fill="x", padx=20, ipady=7)
        self._section(self.advanced_frame, "OPTIONS")
        self._check(self.advanced_frame, "Avoid look-alike characters  (I l 1 O 0 o)", "no_ambig")
        self._check(self.advanced_frame, "Easy-to-type mode  (simple symbols)", "easy")
        self._check(self.advanced_frame, "Require 1+ of each selected type", "require_each")

        pf = self.phrase_frame = tk.Frame(self.mode_box, bg=C["panel"])
        self._section(pf, "NUMBER OF WORDS")
        self.words_scale, self.words_label = self._scale(pf, "words", 4, 10)
        self._section(pf, "SEPARATOR")
        self._entry(pf, "separator").pack(fill="x", padx=20, ipady=7)
        self._section(pf, "OPTIONS")
        self._check(pf, "Capitalize each word", "capitalize")
        self._check(pf, "Add a 2-digit number at the end", "add_number")
        info = tk.Label(
            pf, fg=C["muted"], bg=C["panel"], font=ui(10), justify="left", anchor="w",
            text=f"Word list: {len(self.words):,} words ({self.words_source}) "
                 f"\u2248 {math.log2(len(self.words)):.1f} bits per word.\n"
                 "Add a wordlist.txt next to this script to use a bigger list.")
        info.pack(fill="x", padx=20, pady=(10, 4))
        autowrap(info, p, pad=40)

        tk.Frame(p, bg=C["panel"], height=8).pack()

    def _output(self, p):

        box = tk.Frame(p, bg=C["panel"], highlightbackground=C["cyan"], highlightthickness=1)
        box.pack(fill="x")
        top = tk.Frame(box, bg=C["panel"])
        top.pack(fill="x", padx=20, pady=(14, 0))
        tk.Label(top, text="YOUR PASSWORD", fg=C["magenta"], bg=C["panel"],
                 font=ui(10, True)).pack(side="left")
        self.hide_btn = Chip(top, "HIDE", self.toggle_hidden)
        self.hide_btn.pack(side="right")
        Tooltip(self.hide_btn, "Show or hide the password on screen (F2). Copy still copies the real password.")
        self.pw_text = tk.Text(
            box, height=2, wrap="char", bg=C["panel"], fg=C["cyan"], relief="flat", bd=0,
            highlightthickness=0, font=mono(26, True), padx=20, pady=10, cursor="xterm",
            insertwidth=0, selectbackground=C["magenta"], selectforeground=C["btn_fg"],
            state="disabled")
        self.pw_text.pack(fill="x", pady=(6, 2))
        self.pw_text.bind("<Configure>", lambda e: self._fit_display())
        self.pw_text.bind("<Double-Button-1>", self._select_all)
        tk.Label(box, text="Double-click to select all  \u00b7  Ctrl+Shift+C to copy",
                 fg=C["muted"], bg=C["panel"], font=ui(9)).pack(anchor="w", padx=20, pady=(0, 10))


        self.notice = tk.Label(p, text="", fg=C["muted"], bg=C["bg"], font=ui(10, True),
                               justify="left", anchor="w")
        self.notice.pack(fill="x", pady=(8, 0))
        autowrap(self.notice, p, pad=4)


        meter = tk.Frame(p, bg=C["bg"])
        meter.pack(fill="x", pady=(8, 0))
        top = tk.Frame(meter, bg=C["bg"])
        top.pack(fill="x")
        self.rating = tk.Label(top, text="", fg=C["green"], bg=C["bg"], font=ui(13, True))
        self.rating.pack(side="left")
        self.bits_lbl = tk.Label(top, text="", fg=C["muted"], bg=C["bg"], font=mono(11))
        self.bits_lbl.pack(side="right")
        self.bar = tk.Canvas(meter, height=10, bg=C["panel2"], highlightthickness=0)
        self.bar.pack(fill="x", pady=(8, 0))
        self.bar.bind("<Configure>", lambda e: self._draw_bar())
        self.summary = tk.Label(meter, text="", fg=C["text"], bg=C["bg"], font=ui(11),
                                justify="left", anchor="w")
        self.summary.pack(fill="x", pady=(8, 0))
        autowrap(self.summary, p, pad=4)
        self.tip = tk.Label(meter, text="", fg=C["muted"], bg=C["bg"], font=ui(10),
                            justify="left", anchor="w")
        self.tip.pack(fill="x", pady=(2, 0))
        autowrap(self.tip, p, pad=4)

        btns = tk.Frame(p, bg=C["bg"])
        btns.pack(fill="x", pady=(14, 0))
        btns.columnconfigure((0, 1), weight=1, uniform="b")
        self.copy_btn = NeonButton(btns, "COPY", self.copy, bg=C["magenta"])
        self.copy_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        again = NeonButton(btns, "GENERATE AGAIN", self.generate_again, bg=C["panel2"],
                           fg=C["text"], hover=C["border"])
        again.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        Tooltip(again, "New password with the same settings (Ctrl+G). Never changes your preferences.")
        for col, n in enumerate((5, 10)):
            b = NeonButton(btns, f"GENERATE {n}", lambda n=n: self.generate_batch(n),
                           bg=C["panel2"], fg=C["text"], hover=C["border"], size=10)
            b.grid(row=1, column=col, sticky="ew", padx=(0, 6) if col == 0 else (6, 0), pady=(10, 0))
            Tooltip(b, f"Make {n} passwords at once with your current settings.")
        self.hint = tk.Label(btns, text="", fg=C["green"], bg=C["bg"], font=ui(10, True),
                             anchor="w", justify="left")
        self.hint.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        autowrap(self.hint, btns, pad=4)

        lh = tk.Frame(p, bg=C["bg"])
        lh.pack(fill="x", pady=(14, 0))
        self.tab_recent = Chip(lh, "RECENT", lambda: self._set_list_mode("recent"), size=9)
        self.tab_recent.pack(side="left")
        self.tab_batch = Chip(lh, "BATCH", lambda: self._set_list_mode("batch"), size=9)
        self.tab_batch.pack(side="left", padx=6)
        clr = Chip(lh, "CLEAR", self.clear_lists, size=9)
        clr.pack(side="right")
        Tooltip(clr, "Remove all recent and batch passwords from memory.")
        ca = Chip(lh, "COPY ALL", self.copy_all, size=9)
        ca.pack(side="right", padx=6)
        Tooltip(ca, "Copy every password in the list shown, one per line.")

        lf = tk.Frame(p, bg=C["panel"], highlightbackground=C["border"], highlightthickness=1)
        lf.pack(fill="both", expand=True, pady=(8, 0))
        sb = tk.Scrollbar(lf, width=10, troughcolor=C["panel2"], bg=C["border"], bd=0,
                          highlightthickness=0)
        self.listbox = tk.Listbox(
            lf, bg=C["panel"], fg=C["muted"], font=mono(11), bd=0, highlightthickness=0,
            selectbackground=C["panel2"], selectforeground=C["cyan"], activestyle="none",
            yscrollcommand=sb.set, height=4, cursor="hand2")
        sb.config(command=self.listbox.yview)
        sb.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True, padx=8, pady=6)
        self.listbox.bind("<<ListboxSelect>>", self._on_list_select)
        tk.Label(p,
                 text="Recent history is opt-in. Batch results stay in memory until cleared or the app closes.",
                 fg=C["muted"], bg=C["bg"], font=ui(9), anchor="w", justify="left",
                 wraplength=700).pack(fill="x", pady=(4, 0))

    def _sync_scroll(self):
        try:
            need = self._inner.winfo_reqheight() > self.canvas.winfo_height() > 1
            if need and not self._sb_visible:
                self.sb.pack(side="right", fill="y", before=self.canvas)
                self._sb_visible = True
            elif not need and self._sb_visible:
                self.sb.pack_forget()
                self._sb_visible = False
                self.canvas.yview_moveto(0)
        except tk.TclError:
            pass

    def _wheel(self, e):
        try:
            if not self._sb_visible:
                return
            x, y = self.winfo_pointerxy()
            if self.winfo_containing(x, y) is None:
                return
            w = self.winfo_containing(x, y)
            inside = False
            while w is not None:
                if w is self.canvas or w is self._inner:
                    inside = True
                    break
                w = w.master
            if not inside:
                return
            if getattr(e, "num", 0) == 4:
                d = -1
            elif getattr(e, "num", 0) == 5:
                d = 1
            else:
                d = -1 if e.delta > 0 else 1
            self.canvas.yview_scroll(d, "units")
        except (tk.TclError, KeyError):
            pass

    def _refresh_ui_state(self):
        v = self.vars
        mn, mx = v["min_len"].get(), v["max_len"].get()
        cur = v["length"].get()
        if not mn <= cur <= mx:
            self._set_quiet("length", _clamp(cur, mn, mx))
        self.len_scale.config(from_=mn, to=mx)
        self.len_label.config(text=str(v["length"].get()))
        self.words_label.config(text=str(v["words"].get()))

        name = self.preset.get()
        for n, chip in self.preset_chips.items():
            chip.set_selected(n == name)
        info = PRESETS[name]
        text = info["desc"]
        if info["fmt"]:
            text += f"\nExample format:  {info['fmt']}"
            if name != "Passphrase":
                text += f"\n{FORMAT_KEY}"
        self.preset_desc.config(text=text)

        if name == "Passphrase":
            self.char_frame.pack_forget()
            self.phrase_frame.pack(fill="x")
        else:
            self.phrase_frame.pack_forget()
            self.char_frame.pack(fill="x")
        self.hide_btn.config(text="SHOW" if self.hidden.get() else "HIDE")
        self.after_idle(self._sync_scroll)

    def _toggle_advanced(self):
        self.advanced_open = not self.advanced_open
        if self.advanced_open:
            self.advanced_frame.pack(fill="x")
            self.advanced_toggle.config(text="\u25be  ADVANCED OPTIONS")
        else:
            self.advanced_frame.pack_forget()
            self.advanced_toggle.config(text="\u25b8  ADVANCED OPTIONS")
        self.after_idle(self._sync_scroll)

    def _set_quiet(self, key, value):
        self._applying += 1
        try:
            self.vars[key].set(value)
        finally:
            self._applying -= 1

    def _on_var(self, kind):
        if self._applying:
            return
        if kind == "char" and self.preset.get() != "Custom":
            self.preset.set("Custom")
        self._settings_dirty = True
        self._refresh_ui_state()
        self._update_preview_estimate()
        self._schedule_save()

    def apply_preset(self, name):
        prev = self.preset.get()
        if prev == "Custom" and name != "Custom":
            self._custom_snap = {k: self.vars[k].get() for k in CHAR_KEYS}
        self._applying += 1
        try:
            self.preset.set(name)
            if name == "Custom":
                if self._custom_snap:
                    for k, val in self._custom_snap.items():
                        self.vars[k].set(val)
            else:
                for k, val in PRESETS[name]["values"].items():
                    if k == "length":
                        val = _clamp(val, self.vars["min_len"].get(), self.vars["max_len"].get())
                    self.vars[k].set(val)
        finally:
            self._applying -= 1
        self._settings_dirty = True
        self._refresh_ui_state()
        self._update_preview_estimate()
        self._schedule_save()

    def _plan_chars(self):
        v = self.vars
        easy = v["easy"].get()
        symbols, dropped = clean_symbols(v["symbol_set"].get())
        if easy:
            symbols = "".join(c for c in symbols if c in EASY_SYMBOLS)
        use_sym = v["symbols"].get()
        if use_sym and not symbols:
            hint = f" Easy mode only allows: {EASY_SYMBOLS}" if easy else ""
            raise ValueError("Symbols are on, but the symbol list is empty. "
                             "Add a symbol or turn Symbols off." + hint)
        named = build_pools(v["upper"].get(), v["lower"].get(), v["digits"].get(),
                            use_sym, symbols, v["no_ambig"].get() or easy)
        if not named:
            raise ValueError("Select at least one character type.")
        pools = [c for _, c in named]
        notes = []
        if dropped:
            notes.append("Letters, digits and spaces in the symbol list are ignored.")
        req = v["require_each"].get()
        length = v["length"].get()
        need = len(pools) if req else 1
        if length < need:
            length = need
            self._set_quiet("length", need)
            notes.append(f"Length raised to {need} so every selected type fits.")
        combined = "".join(dict.fromkeys("".join(pools)))
        n = len(combined)
        bits = entropy_bits(length, pools, req)
        per = math.log2(n) if n > 1 else 1
        tip = f"Each extra character multiplies the possibilities by about {n}\u00d7 (+{per:.1f} bits)."
        if bits < 80:
            tip += f" Try {math.ceil(80 / per)}+ characters for a stronger result."
        tip += " Estimate assumes an attacker knows your settings."
        extras = []
        if v["no_ambig"].get() or easy:
            extras.append("Look-alike characters excluded.")
        if easy:
            extras.append("Easy-to-type mode on.")
        if req and len(pools) > 1:
            extras.append("Every selected type is guaranteed.")
        summary = (f"{length} characters \u00b7 " + ", ".join(name for name, _ in named)
                   + ("\n" + " ".join(extras) if extras else ""))
        return dict(kind="chars", length=length, pools=pools, require=req, bits=bits,
                    tip=tip, summary=summary, notice=" ".join(notes))

    def _plan_phrase(self):
        v = self.vars
        n = len(self.words)
        count = v["words"].get()
        sep = "".join(c for c in v["separator"].get() if c.isprintable())[:3]
        cap, add = v["capitalize"].get(), v["add_number"].get()
        bits = passphrase_bits(n, count, add)
        tip = (f"Each extra word multiplies the possibilities by {n:,}\u00d7 (+{math.log2(n):.1f} bits). "
               "Estimate assumes the attacker knows the word list and your settings.")
        summary = (f"{count} random words" + (", capitalized" if cap else "")
                   + (" \u00b7 plus a 2-digit number" if add else "")
                   + f"\nSeparator: {'(none)' if not sep else repr(sep)} \u00b7 word list: {n:,} words ({self.words_source})")
        return dict(kind="phrase", count=count, sep=sep, cap=cap, add=add, bits=bits,
                    tip=tip, summary=summary, notice="")

    def _plan(self):
        return self._plan_phrase() if self.preset.get() == "Passphrase" else self._plan_chars()

    def _draw(self, plan):
        if plan["kind"] == "phrase":
            return generate_passphrase(self.words, plan["count"], plan["sep"], plan["cap"], plan["add"])
        return generate_password(plan["length"], plan["pools"], plan["require"])

    def _update_preview_estimate(self, initial=False):
        """Update the strength estimate for current settings without generating a password."""
        try:
            plan = self._plan()
        except ValueError as exc:
            self.rating.config(text="", fg=C["muted"])
            self.bits_lbl.config(text="")
            self.summary.config(text="")
            self.tip.config(text="")
            self._bar_state = (0.0, C["muted"])
            self._draw_bar()
            self._set_notice("Settings need attention: " + str(exc), "red")
            return
        self._update_meter(plan)
        if initial and not self.password:
            self._set_notice("Choose settings, then click Generate to create a password.", "muted")
        elif self._settings_dirty:
            self._set_notice("Settings changed — click Generate to create a password with these options.",
                             "yellow")
        elif plan.get("notice"):
            self._set_notice(plan["notice"], "yellow")
        else:
            self._set_notice("Ready to generate.", "muted")

    def generate_again(self):
        self.generate(record=True)

    def generate(self, animate=None, record=True):
        self._cancel_anim()
        self.hint.config(text="")
        try:
            plan = self._plan()
            pw = self._draw(plan)
        except ValueError as e:
            self._show_error(str(e))
            return
        self.password, self.plan = pw, plan
        self._settings_dirty = False
        self._set_notice(plan["notice"], "yellow")
        self._update_meter(plan)
        if record:
            self._add_history(pw, plan)
        if animate is None:
            animate = self.vars["animate"].get()
        if animate and not self.hidden.get():
            self._scramble(pw, 0)
        else:
            self._show(pw)

    def generate_batch(self, n):
        self._cancel_anim()
        try:
            plan = self._plan()
            items = [(self._draw(plan), plan) for _ in range(n)]
        except ValueError as e:
            self._show_error(str(e))
            return
        self.batch = items
        self._settings_dirty = False
        self.list_mode = "batch"
        self._refresh_list()
        self._load(*items[0])
        self._set_notice(plan["notice"], "yellow")
        self._set_hint(f"Generated {n}. Click an entry to view it, or use COPY ALL.", "green")


    def _display_string(self, pw):
        return MASK_CHAR * len(pw) if self.hidden.get() else pw

    def _set_text(self, s, color=None):
        self.pw_text.config(state="normal", fg=color or C["cyan"])
        self.pw_text.delete("1.0", "end")
        self.pw_text.insert("1.0", s)
        self.pw_text.config(state="disabled")
        self._fit_display(s)

    def _show(self, pw):
        if not pw:
            self._set_text("\u2014", C["muted"])
        else:
            self._set_text(self._display_string(pw))

    def _fit_display(self, s=None):
        try:
            if s is None:
                s = self.pw_text.get("1.0", "end-1c")
            width = self.pw_text.winfo_width() - 40
            if width < 60:
                return
            key = (width, len(s))
            if key == self._fit_key:
                return
            n = max(1, len(s))

            def lines_at(sz):
                f = tkfont.Font(family=MONO_FAMILY, size=sz, weight="bold")
                return math.ceil(n / max(1, width // max(1, f.measure("0"))))


            size = next((z for z in (28, 24, 20, 18, 16) if lines_at(z) <= 1), None)
            if size is None:
                size = next((z for z in (28, 24, 20, 18, 16, 14, 13, 12)
                             if lines_at(z) <= 2), 12)
            lines = lines_at(size)
            self.pw_text.config(font=mono(size, True), height=min(lines, 8))
            self._fit_key = key
        except tk.TclError:
            pass

    def _select_all(self, _=None):
        self.pw_text.tag_add("sel", "1.0", "end-1c")
        return "break"

    def _scramble(self, target, revealed):
        step = max(1, len(target) // 18)
        revealed = min(len(target), revealed + step)
        noise = "".join(secrets.choice(SCRAMBLE_CHARS) for _ in range(len(target) - revealed))
        self._set_text(target[:revealed] + noise)
        if revealed < len(target):
            self._anim_job = self.after(28, self._scramble, target, revealed)
        else:
            self._anim_job = None
            self._show(target)

    def _cancel_anim(self):
        if self._anim_job:
            self.after_cancel(self._anim_job)
            self._anim_job = None

    def _update_meter(self, plan):
        name, ckey = rate(plan["bits"])
        color = C[ckey]
        self.rating.config(text=name, fg=color)
        self.bits_lbl.config(text=f"\u2248 {plan['bits']:.0f} bits  (estimate)")
        self.summary.config(text=plan["summary"])
        self.tip.config(text=plan["tip"])
        self._bar_state = (plan["bits"], color)
        self._draw_bar()

    def _draw_bar(self):
        try:
            self.bar.delete("all")
            bits, color = self._bar_state
            if bits > 0:
                self.bar.create_rectangle(0, 0, self.bar.winfo_width() * min(bits / 128, 1.0),
                                          10, fill=color, width=0)
        except tk.TclError:
            pass

    def _show_error(self, msg):

        self.password, self.plan = "", None
        self._show("")
        self._set_notice("\u26a0  " + msg, "red")
        self.rating.config(text="", fg=C["muted"])
        self.bits_lbl.config(text="")
        self.summary.config(text="")
        self.tip.config(text="")
        self._bar_state = (0.0, C["muted"])
        self._draw_bar()

    def _set_notice(self, text, color):
        self.notice.config(text=text, fg=C[color] if color in C else C["muted"])

    def _set_hint(self, text, color="green"):
        self.hint.config(text=text, fg=C[color])

    def _load(self, pw, plan):

        self._cancel_anim()
        self.password, self.plan = pw, plan
        self._update_meter(plan)
        self._show(pw)

    def toggle_hidden(self):
        self.hidden.set(not self.hidden.get())
        self._cancel_anim()
        self._refresh_ui_state()
        self._show(self.password)
        self._refresh_list()
        self._schedule_save()


    def _add_history(self, pw, plan):
        if not self.vars["keep_history"].get():
            return
        size = self.vars["history_size"].get()
        self.history = ([(pw, plan)] + [h for h in self.history if h[0] != pw])[:size]
        self._refresh_list()

    def _set_list_mode(self, mode):
        self.list_mode = mode
        self._refresh_list()

    def _refresh_list(self):
        try:
            self.tab_recent.set_selected(self.list_mode == "recent")
            self.tab_batch.set_selected(self.list_mode == "batch")
            items = self.history if self.list_mode == "recent" else self.batch
            self._list_items = list(items)
            self.listbox.delete(0, "end")
            if not items:
                msg = ("History is off or empty." if self.list_mode == "recent"
                       else "Use GENERATE 5 / 10 to fill this list.")
                self.listbox.insert("end", msg)
                return
            for pw, _ in items:
                shown = MASK_CHAR * min(len(pw), 40) if self.hidden.get() else pw
                if len(shown) > 60:
                    shown = shown[:57] + "..."
                self.listbox.insert("end", shown)
        except tk.TclError:
            pass

    def _on_list_select(self, _=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        i = sel[0]
        self.listbox.selection_clear(0, "end")
        if i < len(self._list_items):
            self._settings_dirty = False
            self._load(*self._list_items[i])
            self._set_hint("Loaded from list.", "muted")

    def clear_lists(self):
        self.history, self.batch = [], []
        self._refresh_list()
        self._set_hint("Recent and batch lists cleared.", "muted")


    def copy(self):
        if not self.password:
            self._set_hint("Click Generate first to create a password.", "red")
            return
        if self._settings_dirty:
            self._set_hint("Settings changed. Click Generate before copying so the password matches them.",
                            "yellow")
            return
        self._copy_text(self.password, "Password copied")
        self.copy_btn.config(text="COPIED \u2714")
        self.after(1200, self._reset_copy_label)

    def _reset_copy_label(self):
        try:
            self.copy_btn.config(text="COPY")
        except tk.TclError:
            pass

    def copy_all(self):
        if not self._list_items:
            self._set_hint("Nothing in the list to copy.", "red")
            return
        self._copy_text("\n".join(p for p, _ in self._list_items),
                        f"{len(self._list_items)} passwords copied")

    def _copy_text(self, text, msg):
        self.clipboard_clear()
        self.clipboard_append(text)
        if self._clip_job:
            self.after_cancel(self._clip_job)
            self._clip_job = None
        secs = self.vars["clip_secs"].get()
        if secs > 0:
            self._clip_text = text
            self._set_hint(
                f"\u2714 {msg}. CIPHER will try to clear it in {secs}s if the clipboard still matches; "
                "other apps or clipboard managers may retain copies.", "green")
            self._clip_job = self.after(secs * 1000, self._clear_clipboard)
        else:
            self._clip_text = ""
            self._set_hint(
                f"\u2714 {msg}. Clipboard auto-clear is off; other apps or clipboard managers may retain copies.",
                "green")

    def _clear_clipboard(self):
        self._clip_job = None
        try:
            if clipboard_matches(self.clipboard_get(), self._clip_text):
                self.clipboard_clear()
                self.clipboard_append("")
                if self.hint.cget("text").startswith("\u2714"):
                    self._set_hint("Clipboard cleared.", "muted")
        except tk.TclError:
            pass
        self._clip_text = ""

    def _on_close(self):
        if self._clip_text:
            self._clear_clipboard()
        self._save_now()
        self.destroy()


    def _collect_cfg(self):
        return {k: self.vars[k].get() for k in DEFAULTS}

    def _schedule_save(self):
        if self._save_job:
            self.after_cancel(self._save_job)
        self._save_job = self.after(500, self._save_now)

    def _save_now(self):
        if self._save_job:
            try:
                self.after_cancel(self._save_job)
            except tk.TclError:
                pass
            self._save_job = None
        save_settings(self._collect_cfg())

    def open_settings(self):
        if self._dlg is not None and self._dlg.winfo_exists():
            self._dlg.lift()
            return
        v = self.vars
        win = self._dlg = tk.Toplevel(self)
        win.title("CIPHER \u00b7 Settings")
        win.configure(bg=C["panel"])
        win.resizable(False, False)
        win.transient(self)

        theme = tk.StringVar(value=v["theme"].get())
        minl = tk.StringVar(value=str(v["min_len"].get()))
        maxl = tk.StringVar(value=str(v["max_len"].get()))
        anim = tk.BooleanVar(value=v["animate"].get())
        cur_label = next((l for l, s in CLIP_CHOICES if s == v["clip_secs"].get()), CLIP_CHOICES[2][0])
        clip = tk.StringVar(value=cur_label)
        keep = tk.BooleanVar(value=v["keep_history"].get())
        hsize = tk.StringVar(value=str(v["history_size"].get()))

        body = tk.Frame(win, bg=C["panel"])
        body.pack(padx=26, pady=(22, 8))

        def lab(r, text, sub=None):
            tk.Label(body, text=text, fg=C["text"], bg=C["panel"], font=ui(11),
                     anchor="w").grid(row=r, column=0, sticky="w", pady=7, padx=(0, 22))
            if sub:
                Tooltip(body.grid_slaves(row=r, column=0)[0], sub)

        def menu(r, var, options):
            om = tk.OptionMenu(body, var, *options)
            om.config(bg=C["panel2"], fg=C["text"], activebackground=C["border"],
                      activeforeground=C["cyan"], highlightthickness=0, relief="flat",
                      bd=0, font=ui(10), width=16, anchor="w")
            om["menu"].config(bg=C["panel2"], fg=C["text"], font=ui(10))
            om.grid(row=r, column=1, sticky="w")

        def spin(r, var, lo, hi):
            tk.Spinbox(body, from_=lo, to=hi, textvariable=var, width=6, bg=C["panel2"],
                       fg=C["cyan"], buttonbackground=C["panel2"], relief="flat",
                       insertbackground=C["cyan"], font=mono(11), highlightthickness=1,
                       highlightbackground=C["border"]).grid(row=r, column=1, sticky="w")

        def chk(r, text, var):
            cb = tk.Checkbutton(body, text=text, variable=var, fg=C["text"], bg=C["panel"],
                                selectcolor=C["panel2"], activebackground=C["panel"],
                                activeforeground=C["cyan"], font=ui(11), highlightthickness=0,
                                bd=0, anchor="w", cursor="hand2")
            cb.grid(row=r, column=0, columnspan=2, sticky="w", pady=4)
            return cb

        lab(0, "Theme")
        menu(0, theme, list(THEMES))
        lab(1, "Minimum length (1\u201364)", "Smallest value the length slider allows.")
        spin(1, minl, 1, 64)
        lab(2, "Maximum length (8\u2013256)", "Largest value the length slider allows.")
        spin(2, maxl, 8, 256)
        lab(3, "Clipboard auto-clear",
            "CIPHER tries to clear the value later only if the clipboard still matches. This cannot remove copies kept by every clipboard manager or other app.")
        menu(3, clip, [l for l, _ in CLIP_CHOICES])
        chk(4, "Show the decode animation when generating", anim)
        history_check = chk(5, "Keep a Recent list (opt-in; memory only)", keep)
        Tooltip(history_check, "Off by default. When enabled, recent generated passwords remain in this app's memory until cleared or the app closes; they are never written to the settings file.")
        lab(6, "Recent list size (1\u201310)")
        spin(6, hsize, 1, 10)

        err = tk.Label(win, text="", fg=C["red"], bg=C["panel"], font=ui(10, True))
        err.pack(padx=26, anchor="w")

        def save():
            try:
                mn, mx, hs = int(minl.get()), int(maxl.get()), int(hsize.get())
            except ValueError:
                err.config(text="Length limits and list size must be whole numbers.")
                return
            if not 1 <= mn <= 64:
                err.config(text="Minimum length must be between 1 and 64.")
                return
            if not 8 <= mx <= 256:
                err.config(text="Maximum length must be between 8 and 256.")
                return
            if mx <= mn:
                err.config(text="Maximum length must be larger than the minimum.")
                return
            if not 1 <= hs <= 10:
                err.config(text="Recent list size must be between 1 and 10.")
                return
            changed_theme = theme.get() != v["theme"].get()
            prior_dirty = self._settings_dirty
            prior_length = v["length"].get()
            prior_clip_secs = v["clip_secs"].get()
            v["theme"].set(theme.get())
            v["min_len"].set(mn)
            v["max_len"].set(mx)
            v["animate"].set(anim.get())
            v["clip_secs"].set(dict(CLIP_CHOICES)[clip.get()])
            if v["clip_secs"].get() == 0 and prior_clip_secs != 0 and self._clip_job:
                try:
                    self.after_cancel(self._clip_job)
                except tk.TclError:
                    pass
                self._clip_job = None
                self._clip_text = ""
            v["keep_history"].set(keep.get())
            v["history_size"].set(hs)
            if not keep.get():
                self.history = []
            else:
                self.history = self.history[:hs]
            win.destroy()
            self._dlg = None
            if changed_theme:
                set_theme(theme.get())
                self._rebuild()
            else:
                self._refresh_ui_state()
                self._refresh_list()
            self._settings_dirty = prior_dirty or (v["length"].get() != prior_length)
            self._update_preview_estimate()
            self._save_now()

        btns = tk.Frame(win, bg=C["panel"])
        btns.pack(fill="x", padx=26, pady=(8, 22))
        NeonButton(btns, "SAVE", save, size=10).pack(side="left")
        NeonButton(btns, "RESET TO DEFAULTS", self.reset_defaults, bg=C["panel2"],
                   fg=C["text"], hover=C["border"], size=10).pack(side="left", padx=8)
        NeonButton(btns, "CANCEL", lambda: (win.destroy(), setattr(self, "_dlg", None)),
                   bg=C["panel2"], fg=C["text"], hover=C["border"], size=10).pack(side="left")
        win.protocol("WM_DELETE_WINDOW", lambda: (win.destroy(), setattr(self, "_dlg", None)))
        win.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - win.winfo_width()) // 2
        y = self.winfo_rooty() + 80
        win.geometry(f"+{max(0, x)}+{max(0, y)}")

    def reset_defaults(self):
        parent = self._dlg if (self._dlg is not None and self._dlg.winfo_exists()) else self
        if not messagebox.askyesno(
                "Reset to Defaults",
                "Reset every preference (generator options and settings) to its default?\n"
                "Passwords are not affected.", parent=parent):
            return
        if self._dlg is not None and self._dlg.winfo_exists():
            self._dlg.destroy()
        self._dlg = None
        self._applying += 1
        try:
            for k, val in DEFAULTS.items():
                self.vars[k].set(val)
        finally:
            self._applying -= 1
        self._custom_snap = None
        self.history = [] if not DEFAULTS["keep_history"] else self.history[:DEFAULTS["history_size"]]
        set_theme(DEFAULTS["theme"])
        self._settings_dirty = True
        self._rebuild()
        self._update_preview_estimate()
        self._save_now()
        self._set_hint("Preferences reset. Click Generate to create a password with the defaults.", "green")

    def open_guide(self):
        if self._guide is not None and self._guide.winfo_exists():
            self._guide.lift()
            return
        win = self._guide = tk.Toplevel(self)
        win.title("CIPHER \u00b7 Guide")
        win.configure(bg=C["panel"])
        win.geometry("640x600")
        sb = tk.Scrollbar(win, width=10)
        txt = tk.Text(win, wrap="word", bg=C["panel"], fg=C["text"], relief="flat", bd=0,
                      font=ui(11), padx=24, pady=18, highlightthickness=0,
                      yscrollcommand=sb.set, spacing3=6)
        sb.config(command=txt.yview)
        sb.pack(side="right", fill="y")
        txt.pack(side="left", fill="both", expand=True)
        txt.tag_configure("h", foreground=C["magenta"], font=ui(11, True), spacing1=12)
        for head, body in GUIDE:
            txt.insert("end", head.upper() + "\n", "h")
            txt.insert("end", body + "\n")
        txt.config(state="disabled")


def selftest():
    global SETTINGS_PATH

    def ok(cond, msg):
        print(("PASS  " if cond else "FAIL  ") + msg)
        if not cond:
            raise SystemExit(1)

    full = build_pools(True, True, True, True, DEFAULT_SYMBOLS, False)
    pools = [c for _, c in full]

    good = True
    for length in range(len(pools), 70):
        for _ in range(60):
            pw = generate_password(length, pools, True)
            good &= len(pw) == length and all(any(c in p for c in pw) for p in pools)
    ok(good, "every selected type present for lengths 4..69")


    try:
        generate_password(3, pools, True)
        ok(False, "length < #types is rejected")
    except ValueError:
        ok(True, "length < #types is rejected")


    small = ["ab", "12"]
    brute = sum(1 for t in itertools.product("ab12", repeat=3)
                if set(t) & set("ab") and set(t) & set("12"))
    ok(abs(entropy_bits(3, small, True) - math.log2(brute)) < 1e-9,
       f"exact entropy matches brute force ({brute} valid strings)")
    ok(entropy_bits(3, small, False) == math.log2(4 ** 3), "no-constraint entropy = L*log2(N)")
    ok(entropy_bits(16, pools, True) < 16 * math.log2(len("".join(pools))),
       "required-each rule lowers the estimate slightly (never overstates)")


    pw_pools = [c for _, c in build_pools(True, True, True, True, "!|'`", True)]
    ok(all(c not in AMBIGUOUS for p in pw_pools for c in p), "look-alikes removed from every pool")
    try:
        build_pools(False, False, False, True, "|`'\"", True)
        ok(False, "empty pool after exclusions raises")
    except ValueError:
        ok(True, "empty pool after exclusions raises")


    try:
        build_pools(False, False, False, False, "", False)
        ok(False, "no character types selected is rejected")
    except ValueError:
        ok(True, "no character types selected is rejected")
    try:
        build_pools(True, False, False, True, "", False)
        ok(False, "empty custom symbol pool is rejected when symbols are enabled")
    except ValueError:
        ok(True, "empty custom symbol pool is rejected when symbols are enabled")


    min_cfg = sanitize({"settings_version": SETTINGS_VERSION, "min_len": 1,
                        "max_len": 256, "length": 1})
    min_pw = generate_password(1, ["ab"], False)
    max_pw = generate_password(256, [string.ascii_lowercase], False)
    max_cfg = sanitize({"settings_version": SETTINGS_VERSION, "min_len": 1,
                        "max_len": 256, "length": 256})
    ok(len(min_pw) == 1 and min_cfg["length"] == 1, "minimum password length 1 is supported")
    ok(len(max_pw) == 256 and max_cfg["length"] == 256, "maximum password length 256 is supported")


    words, source = load_wordlist()
    pp = generate_passphrase(words, 9,      "-", True, True)
    ok(len(pp.split("-")) == 10 and pp.split("-")[-1].isdigit(),
       "passphrase: 9 words plus a two-digit number")
    ok(DEFAULTS["words"] == 9 and PRESETS["Passphrase"]["values"]["words"] == 9,
       "nine-word passphrase is the default and preset")
    ok(passphrase_bits(len(words), 9, True) >= 80,
       "default built-in passphrase estimates at least 80 bits")
    ok(passphrase_bits(len(words), 9, True) > passphrase_bits(len(words), 6, True),
       "more words = more bits")
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        wordfile = Path(td) / "wordlist.txt"
        def alpha_code(number):
            chars = []
            while True:
                number, rem = divmod(number, 26)
                chars.append(chr(ord("a") + rem))
                if number == 0:
                    break
            return "".join(reversed(chars))
        custom_words = ["custom" + alpha_code(i) for i in range(300)]
        wordfile.write_text("\n".join(custom_words), encoding="utf-8")
        optional_words, optional_source = load_wordlist(wordfile)
        optional_phrase = generate_passphrase(optional_words, 4, "-", False, False)
        ok(len(optional_words) == 300 and optional_source == "wordlist.txt"
           and len(optional_phrase.split("-")) == 4,
           "optional wordlist loads and generates passphrases")


    ok(clipboard_matches("same-value", "same-value"), "clipboard clears only when value still matches")
    ok(not clipboard_matches("changed-by-another-app", "original-value"),
       "clipboard auto-clear preserves a value changed by another app")


    original_settings_path = SETTINGS_PATH
    try:
        with tempfile.TemporaryDirectory() as td:
            SETTINGS_PATH = Path(td) / "cipher_settings.json"
            cfg = dict(DEFAULTS)
            cfg["theme"] = "Midnight"
            cfg["length"] = 37
            cfg["keep_history"] = True
            save_settings(cfg)
            loaded = load_settings()
            ok(loaded["theme"] == "Midnight" and loaded["length"] == 37
               and loaded["keep_history"] is True,
               "preferences save and load correctly")
            save_settings(dict(DEFAULTS))
            reset_loaded = load_settings()
            ok(reset_loaded["words"] == 9 and reset_loaded["keep_history"] is False
               and reset_loaded["theme"] == DEFAULTS["theme"],
               "reset preferences restore new defaults")
            legacy = sanitize({"keep_history": True, "length": 24})
            ok(legacy["keep_history"] is False and legacy["settings_version"] == SETTINGS_VERSION,
               "legacy settings migrate recent history to opt-in")
    finally:
        SETTINGS_PATH = original_settings_path


    labels = {rate(b)[0] for b in (0, 39, 59, 79, 111, 500)}
    ok("UNBREAKABLE" not in labels and "EXCELLENT" in labels, f"labels are non-absolute: {sorted(labels)}")


    s = sanitize({"length": 9999, "min_len": 50, "max_len": 10, "theme": "nope", "words": "x"})
    ok(s["theme"] in THEMES and s["min_len"] < s["max_len"] and s["length"] <= s["max_len"],
       "corrupt settings are repaired")
    ok(not any("password" in k.lower() for k in DEFAULTS), "no password field in saved preferences")
    print(f"\nAll checks passed. Built-in word list: {len(words)} words "
          f"(~{math.log2(len(words)):.1f} bits/word).")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        App().mainloop() 