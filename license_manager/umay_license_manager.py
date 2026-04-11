"""
Umay License Manager
────────────────────
Standalone Windows GUI for generating and verifying Umay license keys.
Requires: Python 3.10+, customtkinter, cryptography

Run:   python umay_license_manager.py
Build: pyinstaller --onefile --windowed --name "UmayLicenseManager" umay_license_manager.py
"""

import base64
import hashlib
import json
import zlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk

# ─── cryptography ───────────────────────────────────────────────────────────
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding, PrivateFormat, PublicFormat, NoEncryption,
        load_der_private_key, load_der_public_key,
    )
    from cryptography.exceptions import InvalidSignature
    CRYPTO_OK = True
except ImportError:
    CRYPTO_OK = False


# ─── License crypto (self-contained, mirrors backend/app/core/license_crypto.py)

LICENSE_PREFIX = "UMAY.1."

PLANS = ["trial", "starter", "professional", "enterprise"]

PLAN_FEATURES = {
    "trial":        {"transactions", "accounts", "categories", "dashboard"},
    "starter":      {"transactions", "accounts", "categories", "dashboard",
                     "reports", "export", "import_csv",
                     "planned_payments", "loans", "credit_cards"},
    "professional": {"transactions", "accounts", "categories", "dashboard",
                     "reports", "export", "import_csv",
                     "planned_payments", "loans", "credit_cards",
                     "investments", "assets", "institutions",
                     "documents", "ocr", "backup",
                     "period_lock", "audit", "calendar"},
    "enterprise":   {"transactions", "accounts", "categories", "dashboard",
                     "reports", "export", "import_csv",
                     "planned_payments", "loans", "credit_cards",
                     "investments", "assets", "institutions",
                     "documents", "ocr", "backup",
                     "period_lock", "audit", "calendar",
                     "multi_tenant", "sso", "api_access",
                     "custom_roles", "white_label"},
}

PLAN_MAX_USERS = {"trial": 2, "starter": 5, "professional": 25, "enterprise": 9999}


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _db64u(s: str) -> bytes:
    p = 4 - len(s) % 4
    if p != 4:
        s += "=" * p
    return base64.urlsafe_b64decode(s)


def sign_license(tenant_id: str, tenant_slug: str, issued_to: str,
                 plan: str, max_users: int, expires_at: Optional[datetime],
                 private_key_b64: str) -> str:
    raw = base64.b64decode(private_key_b64)
    priv: Ed25519PrivateKey = load_der_private_key(raw, password=None)

    now = datetime.now(timezone.utc)
    payload_dict = {
        "lid": str(uuid.uuid4()),
        "tid": tenant_id,
        "slug": tenant_slug,
        "plan": plan,
        "max_users": max_users,
        "features": sorted(PLAN_FEATURES.get(plan, set())),
        "ito": issued_to,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()) if expires_at else None,
        "ver": 1,
    }
    payload_bytes = zlib.compress(
        json.dumps(payload_dict, sort_keys=True, separators=(",", ":")).encode(),
        level=9,
    )
    sig = priv.sign(payload_bytes)
    return f"{LICENSE_PREFIX}{_b64u(payload_bytes)}.{_b64u(sig)}"


def verify_license(key: str) -> dict:
    if not key.startswith(LICENSE_PREFIX):
        raise ValueError("Geçersiz lisans formatı")
    parts = key[len(LICENSE_PREFIX):].split(".")
    if len(parts) != 2:
        raise ValueError("Geçersiz lisans yapısı")

    payload_bytes = _db64u(parts[0])
    sig_bytes = _db64u(parts[1])

    data = json.loads(zlib.decompress(payload_bytes))

    # We return data without verifying signature here (verification
    # requires the public key which is embedded in the backend).
    # The "Verify" tab shows what's inside the key.
    return data, payload_bytes, sig_bytes


def generate_keypair() -> tuple[str, str]:
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    priv_der = priv.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())
    pub_der = pub.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
    return base64.b64encode(priv_der).decode(), base64.b64encode(pub_der).decode()


# ─── App ────────────────────────────────────────────────────────────────────

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_TITLE = "Umay License Manager"
APP_VERSION = "1.0"
ACCENT = "#1a7fd4"
SUCCESS = "#2ecc71"
ERROR = "#e74c3c"
WARN = "#f39c12"

FONT_TITLE = ("Segoe UI", 20, "bold")
FONT_LABEL = ("Segoe UI", 12)
FONT_SMALL = ("Segoe UI", 10)
FONT_MONO  = ("Consolas", 10)


class App(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry("820x680")
        self.resizable(False, False)
        self._private_key = tk.StringVar()

        self._build_ui()
        self._check_crypto()

    # ── Crypto check ────────────────────────────────────────────────────────

    def _check_crypto(self):
        if not CRYPTO_OK:
            messagebox.showerror(
                "Eksik Bağımlılık",
                "cryptography paketi bulunamadı.\n\n"
                "Terminalde şunu çalıştırın:\n  pip install cryptography",
            )

    # ── Main layout ─────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="#111827", corner_radius=0, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="⚿  Umay License Manager",
                     font=FONT_TITLE, text_color="#e2e8f0").pack(side="left", padx=20, pady=14)
        ctk.CTkLabel(header, text=f"v{APP_VERSION}",
                     font=FONT_SMALL, text_color="#64748b").pack(side="right", padx=20)

        # Private key bar
        key_bar = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=0, height=52)
        key_bar.pack(fill="x")
        key_bar.pack_propagate(False)
        ctk.CTkLabel(key_bar, text="Private Key:", font=FONT_LABEL,
                     text_color="#94a3b8").pack(side="left", padx=(16, 6), pady=12)
        self._pk_entry = ctk.CTkEntry(
            key_bar, textvariable=self._private_key, width=480,
            show="•", font=FONT_MONO, fg_color="#0f172a", border_color="#334155",
            placeholder_text="MC4CAQAwBQYD...  (generate_keys.py çıktısı)",
        )
        self._pk_entry.pack(side="left", pady=12)
        ctk.CTkButton(key_bar, text="👁 Göster", width=80, height=30,
                      fg_color="#334155", hover_color="#475569",
                      command=self._toggle_pk).pack(side="left", padx=6, pady=12)
        ctk.CTkButton(key_bar, text="Yeni Keypair Üret", width=150, height=30,
                      fg_color="#7c3aed", hover_color="#6d28d9",
                      command=self._generate_keypair_dialog).pack(side="right", padx=16, pady=12)

        # Tabs
        self._tabs = ctk.CTkTabview(self, anchor="nw")
        self._tabs.pack(fill="both", expand=True, padx=12, pady=(8, 12))
        self._tabs.add("🔑  Key Oluştur")
        self._tabs.add("🔍  Key Doğrula")

        self._build_generate_tab(self._tabs.tab("🔑  Key Oluştur"))
        self._build_verify_tab(self._tabs.tab("🔍  Key Doğrula"))

    # ── Generate tab ────────────────────────────────────────────────────────

    def _build_generate_tab(self, tab):
        tab.columnconfigure(1, weight=1)

        fields = [
            ("Tenant ID (UUID):",   "tenant_id",   "550e8400-e29b-41d4-a716-446655440001"),
            ("Tenant Slug:",        "tenant_slug",  "acme-corp"),
            ("İsim / Şirket:",      "issued_to",    "ACME A.Ş."),
        ]

        self._gen_vars = {}
        for row, (label, key, placeholder) in enumerate(fields):
            ctk.CTkLabel(tab, text=label, font=FONT_LABEL, anchor="e").grid(
                row=row, column=0, sticky="e", padx=(0, 10), pady=8)
            var = tk.StringVar()
            self._gen_vars[key] = var
            entry = ctk.CTkEntry(tab, textvariable=var, width=360,
                                 placeholder_text=placeholder, font=FONT_LABEL)
            entry.grid(row=row, column=1, sticky="ew", pady=8, padx=(0, 20))

        # Plan
        ctk.CTkLabel(tab, text="Plan:", font=FONT_LABEL, anchor="e").grid(
            row=3, column=0, sticky="e", padx=(0, 10), pady=8)
        self._plan_var = tk.StringVar(value="professional")
        plan_menu = ctk.CTkOptionMenu(tab, values=PLANS, variable=self._plan_var,
                                      width=200, command=self._on_plan_change)
        plan_menu.grid(row=3, column=1, sticky="w", pady=8)

        # Max users
        ctk.CTkLabel(tab, text="Max Kullanıcı:", font=FONT_LABEL, anchor="e").grid(
            row=4, column=0, sticky="e", padx=(0, 10), pady=8)
        self._max_users_var = tk.StringVar(value="25")
        ctk.CTkEntry(tab, textvariable=self._max_users_var, width=100,
                     font=FONT_LABEL).grid(row=4, column=1, sticky="w", pady=8)

        # Expiry
        ctk.CTkLabel(tab, text="Bitiş Tarihi:", font=FONT_LABEL, anchor="e").grid(
            row=5, column=0, sticky="e", padx=(0, 10), pady=8)
        expiry_frame = ctk.CTkFrame(tab, fg_color="transparent")
        expiry_frame.grid(row=5, column=1, sticky="w", pady=8)
        self._expiry_var = tk.StringVar(value=(datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"))
        self._expiry_entry = ctk.CTkEntry(expiry_frame, textvariable=self._expiry_var,
                                           width=150, font=FONT_LABEL)
        self._expiry_entry.pack(side="left")
        self._no_expiry_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(expiry_frame, text="Süresiz", variable=self._no_expiry_var,
                        command=self._on_no_expiry).pack(side="left", padx=12)

        # Generate button
        ctk.CTkButton(tab, text="🔑  Lisans Key Oluştur", height=44,
                      font=("Segoe UI", 13, "bold"),
                      fg_color=ACCENT, hover_color="#1565c0",
                      command=self._generate).grid(
            row=6, column=0, columnspan=2, pady=(16, 8), padx=20, sticky="ew")

        # Output
        ctk.CTkLabel(tab, text="Oluşturulan Key:", font=FONT_LABEL,
                     text_color="#94a3b8").grid(row=7, column=0, columnspan=2,
                                                 sticky="w", padx=4, pady=(4, 0))
        self._output_box = ctk.CTkTextbox(tab, height=90, font=FONT_MONO,
                                           fg_color="#0f172a", border_color="#334155",
                                           wrap="char")
        self._output_box.grid(row=8, column=0, columnspan=2, sticky="ew",
                               padx=4, pady=(0, 6))
        self._output_box.configure(state="disabled")

        # Copy button + status
        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.grid(row=9, column=0, columnspan=2, sticky="ew", padx=4)
        ctk.CTkButton(btn_row, text="📋  Kopyala", width=130, height=34,
                      fg_color="#334155", hover_color="#475569",
                      command=self._copy_key).pack(side="left")
        self._gen_status = ctk.CTkLabel(btn_row, text="", font=FONT_SMALL)
        self._gen_status.pack(side="left", padx=12)

    def _on_plan_change(self, plan: str):
        self._max_users_var.set(str(PLAN_MAX_USERS.get(plan, 25)))

    def _on_no_expiry(self):
        if self._no_expiry_var.get():
            self._expiry_entry.configure(state="disabled")
        else:
            self._expiry_entry.configure(state="normal")

    def _generate(self):
        if not CRYPTO_OK:
            return

        pk = self._private_key.get().strip()
        if not pk:
            self._set_gen_status("Private key girilmedi", ERROR)
            return

        tid = self._gen_vars["tenant_id"].get().strip()
        slug = self._gen_vars["tenant_slug"].get().strip()
        ito = self._gen_vars["issued_to"].get().strip()

        if not all([tid, slug, ito]):
            self._set_gen_status("Tüm alanları doldurun", ERROR)
            return

        try:
            uuid.UUID(tid)
        except ValueError:
            self._set_gen_status("Tenant ID geçerli bir UUID değil", ERROR)
            return

        try:
            max_u = int(self._max_users_var.get())
        except ValueError:
            self._set_gen_status("Max kullanıcı sayısı geçersiz", ERROR)
            return

        expires_at = None
        if not self._no_expiry_var.get():
            try:
                expires_at = datetime.strptime(
                    self._expiry_var.get().strip(), "%Y-%m-%d"
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                self._set_gen_status("Tarih formatı: YYYY-MM-DD", ERROR)
                return

        try:
            key = sign_license(
                tenant_id=tid,
                tenant_slug=slug,
                issued_to=ito,
                plan=self._plan_var.get(),
                max_users=max_u,
                expires_at=expires_at,
                private_key_b64=pk,
            )
        except Exception as exc:
            self._set_gen_status(f"Hata: {exc}", ERROR)
            return

        self._output_box.configure(state="normal")
        self._output_box.delete("1.0", "end")
        self._output_box.insert("1.0", key)
        self._output_box.configure(state="disabled")
        self._set_gen_status(f"✓  Key oluşturuldu ({len(key)} karakter)", SUCCESS)

    def _copy_key(self):
        key = self._output_box.get("1.0", "end").strip()
        if not key:
            return
        self.clipboard_clear()
        self.clipboard_append(key)
        self._set_gen_status("✓  Panoya kopyalandı", SUCCESS)

    def _set_gen_status(self, msg: str, color: str = "#94a3b8"):
        self._gen_status.configure(text=msg, text_color=color)

    # ── Verify tab ──────────────────────────────────────────────────────────

    def _build_verify_tab(self, tab):
        ctk.CTkLabel(tab, text="Doğrulanacak Key:", font=FONT_LABEL,
                     text_color="#94a3b8").pack(anchor="w", padx=4, pady=(8, 2))
        self._verify_input = ctk.CTkTextbox(tab, height=80, font=FONT_MONO,
                                             fg_color="#0f172a", border_color="#334155",
                                             wrap="char")
        self._verify_input.pack(fill="x", padx=4, pady=(0, 8))

        ctk.CTkButton(tab, text="🔍  Key'i İncele", height=40,
                      font=("Segoe UI", 13, "bold"),
                      fg_color=ACCENT, hover_color="#1565c0",
                      command=self._verify).pack(fill="x", padx=4, pady=(0, 10))

        self._verify_status = ctk.CTkLabel(tab, text="", font=FONT_LABEL)
        self._verify_status.pack(anchor="w", padx=8)

        self._verify_result = ctk.CTkTextbox(tab, height=320, font=FONT_MONO,
                                              fg_color="#0f172a", border_color="#334155")
        self._verify_result.pack(fill="both", expand=True, padx=4, pady=(4, 8))
        self._verify_result.configure(state="disabled")

    def _verify(self):
        key = self._verify_input.get("1.0", "end").strip()
        if not key:
            return

        self._verify_result.configure(state="normal")
        self._verify_result.delete("1.0", "end")

        try:
            data, payload_bytes, sig_bytes = verify_license(key)
        except Exception as exc:
            self._verify_status.configure(
                text=f"⚠  Çözümlenemedi: {exc}", text_color=ERROR)
            self._verify_result.configure(state="disabled")
            return

        exp = data.get("exp")
        exp_str = "Süresiz" if exp is None else datetime.fromtimestamp(exp, tz=timezone.utc).strftime("%Y-%m-%d")
        iat_str = datetime.fromtimestamp(data.get("iat", 0), tz=timezone.utc).strftime("%Y-%m-%d")

        is_expired = exp is not None and datetime.now(timezone.utc).timestamp() > exp
        expiry_warn = "  ⚠ SÜRESİ DOLMUŞ" if is_expired else ""

        lines = [
            f"{'─'*54}",
            f"  KEY İÇERİĞİ (Payload Decode)",
            f"{'─'*54}",
            f"  License ID   : {data.get('lid', '?')}",
            f"  Tenant ID    : {data.get('tid', '?')}",
            f"  Tenant Slug  : {data.get('slug', '?')}",
            f"  Issued To    : {data.get('ito', '?')}",
            f"  Plan         : {data.get('plan', '?').upper()}",
            f"  Max Users    : {data.get('max_users', '?')}",
            f"  Issued At    : {iat_str}",
            f"  Expires At   : {exp_str}{expiry_warn}",
            f"  Version      : {data.get('ver', '?')}",
            f"{'─'*54}",
            f"  Features ({len(data.get('features', []))}):",
        ]
        for f in sorted(data.get("features", [])):
            lines.append(f"    • {f}")

        lines += [
            f"{'─'*54}",
            f"  Payload size : {len(payload_bytes)} bytes (compressed)",
            f"  Sig size     : {len(sig_bytes)} bytes (Ed25519)",
            f"  Key length   : {len(key)} chars",
            f"{'─'*54}",
            f"  ⚠  İmza doğrulaması backend'de (public key gerekli)",
        ]

        self._verify_result.insert("1.0", "\n".join(lines))
        self._verify_result.configure(state="disabled")

        status_color = ERROR if is_expired else SUCCESS
        status_text = "✓  Yapı geçerli — payload çözümlendi" + (" (SÜRESİ DOLMUŞ)" if is_expired else "")
        self._verify_status.configure(text=status_text, text_color=status_color)

    # ── Keypair generator dialog ─────────────────────────────────────────────

    def _generate_keypair_dialog(self):
        if not CRYPTO_OK:
            return

        priv_b64, pub_b64 = generate_keypair()
        pub_bytes = base64.b64decode(pub_b64)
        fp = hashlib.sha256(pub_bytes).hexdigest()[:32].upper()

        dlg = ctk.CTkToplevel(self)
        dlg.title("Yeni Keypair Üretildi")
        dlg.geometry("680x520")
        dlg.resizable(False, False)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="⚠  Yeni Ed25519 Keypair",
                     font=("Segoe UI", 16, "bold"), text_color=WARN).pack(pady=(20, 4))
        ctk.CTkLabel(dlg,
                     text="Private key'i bir vault'a kaydedin. Public key'i license_crypto.py'ye yapıştırın.",
                     font=FONT_SMALL, text_color="#94a3b8").pack()

        def labeled_box(parent, label, value, color):
            ctk.CTkLabel(parent, text=label, font=FONT_LABEL,
                         text_color="#94a3b8").pack(anchor="w", padx=16, pady=(12, 2))
            box = ctk.CTkTextbox(parent, height=56, font=FONT_MONO,
                                  fg_color="#0f172a", border_color=color)
            box.pack(fill="x", padx=16)
            box.insert("1.0", value)
            box.configure(state="disabled")
            def copy():
                self.clipboard_clear()
                self.clipboard_append(value)
            ctk.CTkButton(parent, text="📋 Kopyala", width=110, height=26,
                          fg_color="#334155", hover_color="#475569",
                          command=copy).pack(anchor="e", padx=16, pady=(2, 0))

        labeled_box(dlg, "🔒 PRIVATE KEY  (vault'a kaydet, asla paylaşma)",
                    priv_b64, "#ef4444")
        labeled_box(dlg, "🔓 PUBLIC KEY  (license_crypto.py → _PUBLIC_KEY_B64)",
                    pub_b64, "#22c55e")

        ctk.CTkLabel(dlg, text=f"Parmak izi: {fp}",
                     font=FONT_MONO, text_color="#64748b").pack(pady=(10, 0))

        def use_this_key():
            self._private_key.set(priv_b64)
            self._pk_entry.configure(show="•")
            dlg.destroy()

        ctk.CTkButton(dlg, text="Bu Private Key'i Kullan", height=38,
                      fg_color=ACCENT, command=use_this_key).pack(pady=16, padx=16, fill="x")

    # ── Toggle private key visibility ────────────────────────────────────────

    def _toggle_pk(self):
        if self._pk_entry.cget("show") == "•":
            self._pk_entry.configure(show="")
        else:
            self._pk_entry.configure(show="•")


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = App()
    app.mainloop()
