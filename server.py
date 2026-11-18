"""KASIN JSON API. Uses Supabase when credentials are set; otherwise SQLite."""
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import mimetypes
import os
import sqlite3
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, parse_qs, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent
DB_PATH = ROOT / "kasin.db"
TABLE = "transactions"


def load_dotenv():
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                name, value = line.split("=", 1)
                os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)
BENDAHARA_INVITE_CODE = os.getenv("BENDAHARA_INVITE_CODE", "")


def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def initialize():
    if USE_SUPABASE:
        return
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL CHECK(kind IN ('masuk','keluar')),
            description TEXT NOT NULL,
            person TEXT NOT NULL DEFAULT '',
            amount INTEGER NOT NULL CHECK(amount > 0),
            category TEXT NOT NULL,
            happened_on TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        if db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0:
            samples = [
                ('masuk', 'Iuran kas mingguan', 'Seluruh kelas', 250000, 'Iuran', date.today().isoformat()),
                ('keluar', 'Isi ulang tinta printer', '—', 45000, 'Perlengkapan', date.today().isoformat()),
                ('masuk', 'Iuran kas mingguan', 'Seluruh kelas', 200000, 'Iuran', date.today().isoformat()),
                ('keluar', 'Air minum kelas', '—', 30000, 'Kebutuhan kelas', date.today().isoformat()),
            ]
            db.executemany("INSERT INTO transactions(kind,description,person,amount,category,happened_on) VALUES(?,?,?,?,?,?)", samples)


def supabase_request(method, query=None, payload=None):
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}"
    if query:
        url += "?" + urlencode(query)
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json", "Accept": "application/json"}
    # Current sb_secret keys authenticate through apikey. Legacy service_role keys are JWTs.
    if not SUPABASE_KEY.startswith("sb_"):
        headers["Authorization"] = f"Bearer {SUPABASE_KEY}"
    if method == "POST":
        headers["Prefer"] = "return=representation"
    request = Request(url, data=json.dumps(payload).encode("utf-8") if payload is not None else None,
                      headers=headers, method=method)
    try:
        with urlopen(request, timeout=12) as response:
            body = response.read()
            return json.loads(body) if body else []
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        try:
            message = json.loads(details).get("message", "")
        except json.JSONDecodeError:
            message = ""
        raise RuntimeError(message or f"Supabase mengembalikan HTTP {exc.code}.") from None
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"Supabase tidak dapat dihubungi: {getattr(exc, 'reason', str(exc))}") from None


def auth_request(path, method="GET", payload=None, access_token=""):
    """Call Supabase Auth from the server; the secret key never reaches the browser."""
    if not USE_SUPABASE:
        raise RuntimeError("Buat akun memerlukan koneksi Supabase. Lengkapi file .env terlebih dahulu.")
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json", "Accept": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    elif not SUPABASE_KEY.startswith("sb_"):
        headers["Authorization"] = f"Bearer {SUPABASE_KEY}"
    request = Request(f"{SUPABASE_URL}/auth/v1/{path.lstrip('/')}",
                      data=json.dumps(payload).encode("utf-8") if payload is not None else None,
                      headers=headers, method=method)
    try:
        with urlopen(request, timeout=12) as response:
            body = response.read()
            return json.loads(body) if body else {}
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        try:
            error = json.loads(details)
            message = error.get("msg") or error.get("message") or error.get("error_description") or error.get("error")
        except json.JSONDecodeError:
            message = ""
        raise RuntimeError(message or f"Supabase Auth mengembalikan HTTP {exc.code}.") from None
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"Supabase Auth tidak dapat dihubungi: {getattr(exc, 'reason', str(exc))}") from None


def sign_in(email, password):
    session = auth_request("token?grant_type=password", "POST", {"email": email, "password": password})
    user = session.get("user") or {}
    role = (user.get("app_metadata") or {}).get("role")
    if role not in ("bendahara", "siswa"):
        raise RuntimeError("Akun ini belum memiliki peran KASIN. Hubungi bendahara.")
    return {"access_token": session.get("access_token"), "refresh_token": session.get("refresh_token"),
            "expires_in": session.get("expires_in"), "user": user}


def authenticated_user(handler):
    authorization = handler.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    if not token:
        return None
    user = auth_request("user", "GET", access_token=token)
    app_metadata = user.get("app_metadata") or {}
    role = app_metadata.get("role")
    if role not in ("bendahara", "siswa"):
        return None
    user["kasin_role"] = role
    return user


def get_transactions(month=""):
    if USE_SUPABASE:
        query = [("select", "id,kind,description,person,amount,category,happened_on,created_at"),
                 ("order", "happened_on.desc,id.desc"), ("limit", "10000")]
        if month and len(month) == 7:
            try:
                start = datetime.strptime(month, "%Y-%m").date().replace(day=1)
                end = start.replace(year=start.year + (start.month == 12), month=1 if start.month == 12 else start.month + 1)
                query += [("and", f"(happened_on.gte.{start.isoformat()},happened_on.lt.{end.isoformat()})")]
            except ValueError:
                pass
        return supabase_request("GET", query)
    # Keep the local API usable even when the module is started by an IDE runner
    # that does not execute the __main__ startup block.
    initialize()
    with connect() as db:
        if month and len(month) == 7:
            rows = db.execute("SELECT * FROM transactions WHERE substr(happened_on,1,7)=? ORDER BY happened_on DESC,id DESC", (month,)).fetchall()
        else:
            rows = db.execute("SELECT * FROM transactions ORDER BY happened_on DESC,id DESC").fetchall()
    return [dict(row) for row in rows]


def create_transaction(payload):
    if USE_SUPABASE:
        return supabase_request("POST", payload=payload)[0]
    initialize()
    with connect() as db:
        cursor = db.execute("INSERT INTO transactions(kind,description,person,amount,category,happened_on) VALUES(?,?,?,?,?,?)",
                            (payload["kind"], payload["description"], payload["person"], payload["amount"], payload["category"], payload["happened_on"]))
        row = db.execute("SELECT * FROM transactions WHERE id=?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def get_summary():
    rows = get_transactions()
    result = {"masuk": {"total": 0, "count": 0}, "keluar": {"total": 0, "count": 0}}
    for row in rows:
        kind = row["kind"]
        if kind in result:
            result[kind]["total"] += int(row["amount"])
            result[kind]["count"] += 1
    result["saldo"] = result["masuk"]["total"] - result["keluar"]["total"]
    result["jumlah_transaksi"] = result["masuk"]["count"] + result["keluar"]["count"]
    return result


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def send_json(self, value, status=200):
        body = json_bytes(value)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            return self.send_json({"ok": True, "penyimpanan": "Supabase" if USE_SUPABASE else "SQLite lokal"})
        if path == "/api/summary":
            try:
                user = authenticated_user(self)
                if not user:
                    return self.send_json({"error": "Silakan masuk ke akun KASIN terlebih dahulu."}, 401)
                return self.send_json(get_summary())
            except RuntimeError as exc:
                return self.send_json({"error": str(exc)}, 401)
        if path == "/api/transactions":
            month = parse_qs(urlparse(self.path).query).get("bulan", [""])[0]
            try:
                user = authenticated_user(self)
                if not user:
                    return self.send_json({"error": "Silakan masuk ke akun KASIN terlebih dahulu."}, 401)
                return self.send_json(get_transactions(month))
            except RuntimeError as exc:
                return self.send_json({"error": str(exc)}, 401)
        if path == "/":
            body = (ROOT / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        if path in ("/styles.css", "/app.js"):
            body = (ROOT / path.lstrip("/")).read_bytes()
            content_type = "text/css; charset=utf-8" if path.endswith(".css") else "text/javascript; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        if path.startswith("/students/"):
            filename = path.rsplit("/", 1)[-1]
            stem, dot, extension = filename.partition(".")
            if dot and stem.isdigit() and len(stem) == 2 and 1 <= int(stem) <= 41 and extension.lower() in ("jpg", "jpeg", "png", "webp"):
                image_path = ROOT / "students" / filename
                if image_path.is_file():
                    body = image_path.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", mimetypes.guess_type(image_path.name)[0] or "application/octet-stream")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "public, max-age=3600")
                    self.end_headers()
                    return self.wfile.write(body)
            return self.send_error(404)
        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/register":
            if not USE_SUPABASE:
                return self.send_json({"error": "Akun memerlukan Supabase. Lengkapi .env dan jalankan ulang server."}, 503)
            try:
                data = self.read_json()
                name = str(data.get("name", "")).strip()
                email = str(data.get("email", "")).strip().lower()
                password = str(data.get("password", ""))
                role = str(data.get("role", "siswa"))
                if len(name) < 2 or len(name) > 60 or "@" not in email or len(email) > 254:
                    raise ValueError("Isi nama dan alamat email dengan benar.")
                if len(password) < 8:
                    raise ValueError("Kata sandi minimal 8 karakter.")
                if role not in ("bendahara", "siswa"):
                    raise ValueError("Pilih peran siswa atau bendahara.")
                if role == "bendahara":
                    invite_code = str(data.get("invite_code", ""))
                    if not BENDAHARA_INVITE_CODE:
                        raise ValueError("Kode undangan bendahara belum diatur. Minta pengelola mengaturnya di .env.")
                    if invite_code != BENDAHARA_INVITE_CODE:
                        raise ValueError("Kode undangan bendahara tidak cocok.")
                auth_request("admin/users", "POST", {
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                    "user_metadata": {"full_name": name},
                    "app_metadata": {"role": role},
                })
                return self.send_json(sign_in(email, password), 201)
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                return self.send_json({"error": str(exc) or "Data akun tidak valid."}, 400)
            except RuntimeError as exc:
                return self.send_json({"error": str(exc)}, 400)

        if path == "/api/login":
            try:
                data = self.read_json()
                email = str(data.get("email", "")).strip().lower()
                password = str(data.get("password", ""))
                if not email or not password:
                    raise ValueError("Masukkan email dan kata sandi.")
                return self.send_json(sign_in(email, password))
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                return self.send_json({"error": str(exc) or "Data masuk tidak valid."}, 400)
            except RuntimeError as exc:
                return self.send_json({"error": str(exc)}, 401)

        if path != "/api/transactions":
            return self.send_json({"error": "Alamat tidak ditemukan."}, 404)
        try:
            user = authenticated_user(self)
            if not user:
                return self.send_json({"error": "Silakan masuk ke akun KASIN terlebih dahulu."}, 401)
            if user["kasin_role"] != "bendahara":
                return self.send_json({"error": "Hanya akun bendahara yang dapat mencatat transaksi."}, 403)
            data = self.read_json()
            kind = data.get("kind")
            description = str(data.get("description", "")).strip()
            person = str(data.get("person", "")).strip()
            category = str(data.get("category", "")).strip()
            amount = int(data.get("amount", 0))
            happened_on = str(data.get("happened_on", ""))
            datetime.strptime(happened_on, "%Y-%m-%d")
            if kind not in ("masuk", "keluar") or not description or not category or amount < 1:
                raise ValueError("Lengkapi jenis, keterangan, kategori, dan nominal dengan benar.")
            if len(description) > 100 or len(person) > 60 or len(category) > 40:
                raise ValueError("Keterangan atau kategori terlalu panjang.")
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self.send_json({"error": str(exc) or "Data transaksi tidak valid."}, 400)
        try:
            row = create_transaction({"kind": kind, "description": description, "person": person, "amount": amount,
                                      "category": category, "happened_on": happened_on})
            self.send_json(row, 201)
        except RuntimeError as exc:
            self.send_json({"error": str(exc)}, 502)

    def log_message(self, *_args):
        pass


if __name__ == "__main__":
    initialize()
    backend = "Supabase" if USE_SUPABASE else "SQLite lokal (data contoh)"
    print(f"KASIN menggunakan {backend} — http://127.0.0.1:8000")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
