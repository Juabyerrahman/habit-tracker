from flask import Blueprint, Response, abort, current_app

bp = Blueprint("dev", __name__, url_prefix="/dev")

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Auth test (dev only)</title>
<style>
 body{font:15px/1.5 system-ui,sans-serif;max-width:640px;margin:2rem auto;padding:0 1rem;color:#111}
 section{border:1px solid #ddd;border-radius:10px;padding:1rem;margin:1rem 0}
 h1{font-size:1.2rem} h2{font-size:.95rem;margin:0 0 .5rem;color:#555}
 button,a.btn{font:inherit;padding:.45rem .8rem;border:1px solid #111;border-radius:8px;background:#111;color:#fff;cursor:pointer;text-decoration:none;display:inline-block}
 button.alt{background:#fff;color:#111} input{font:inherit;padding:.4rem;border:1px solid #bbb;border-radius:8px;margin:0 .3rem .5rem 0}
 pre{background:#f5f5f5;padding:.8rem;border-radius:8px;overflow:auto;white-space:pre-wrap}
 #status{font-weight:600}.err{color:#b00020}
</style></head><body>
<h1>Habit Tracker: auth test page <small>(development only)</small></h1>
<section><h2>Status</h2><div id="status">Checking session...</div></section>
<section><h2>Google</h2>
 <a class="btn" id="google" href="#">Continue with Google</a>
 <button class="alt" id="link">Link Google to the signed-in account</button>
</section>
<section><h2>Email / password</h2>
 <input id="email" type="email" placeholder="email" autocomplete="username">
 <input id="pw" type="password" placeholder="password (10+ chars)" autocomplete="current-password"><br>
 <button id="login">Log in</button> <button class="alt" id="register">Register</button>
</section>
<section><h2>Session</h2>
 <button class="alt" id="me">GET /api/me</button> <button class="alt" id="refresh">Refresh</button> <button id="logout">Log out</button>
</section>
<pre id="out"></pre>
<script>
let token = null;
const $ = id => document.getElementById(id), out = $("out");
const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
const show = (label, data) => { out.textContent = label + "\\n" + JSON.stringify(data, null, 2); };
function status(text, bad) { const s = $("status"); s.textContent = text; s.className = bad ? "err" : ""; }
async function api(path, method, body) {
  const headers = {"Content-Type": "application/json"};
  if (token) headers.Authorization = "Bearer " + token;
  const r = await fetch(path, {method, headers, credentials: "same-origin", body: body ? JSON.stringify(body) : undefined});
  let data = null; try { data = await r.json(); } catch (e) {}
  return {status: r.status, data};
}
function adopt(res) {
  if (res.status < 300 && res.data && res.data.access_token) {
    token = res.data.access_token;
    status("Signed in as " + res.data.user.email + " | providers: " + res.data.user.auth_providers.join(", "));
  } else { token = null; status("Not signed in", true); }
  show("HTTP " + res.status, res.data && res.data.access_token ? {...res.data, access_token: "(hidden, kept in memory only)"} : res.data);
}
$("google").href = "/auth/google/login?return=dev&tz=" + encodeURIComponent(tz);
$("link").onclick = async () => {
  const r = await api("/api/auth/google/link", "POST", {return: "dev"});
  if (r.data && r.data.authorization_url) window.location = r.data.authorization_url; else show("HTTP " + r.status, r.data);
};
$("login").onclick = async () => adopt(await api("/api/auth/login", "POST", {email: $("email").value, password: $("pw").value}));
$("register").onclick = async () => adopt(await api("/api/auth/register", "POST", {email: $("email").value, password: $("pw").value, timezone: tz}));
$("refresh").onclick = async () => adopt(await api("/api/auth/refresh", "POST"));
$("me").onclick = async () => { const r = await api("/api/me", "GET"); show("HTTP " + r.status, r.data); };
$("logout").onclick = async () => { await api("/api/auth/logout", "POST"); token = null; status("Logged out (refresh token revoked)"); show("Logged out", {}); };
(async () => {
  const q = new URLSearchParams(location.search);
  history.replaceState(null, "", location.pathname);
  const res = await api("/api/auth/refresh", "POST");
  adopt(res);
  if (q.get("error")) { status("Google sign-in failed: " + q.get("error"), true); show("Redirect error", {error: q.get("error")}); }
  else if (q.get("linked")) { status("Linked " + q.get("linked") + " to your account"); }
})();
</script></body></html>"""


@bp.get("/auth-test")
def auth_test():
    if not current_app.config["ENABLE_DEV_TOOLS"]:
        abort(404)
    resp = Response(PAGE, mimetype="text/html")
    resp.headers["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
        "connect-src 'self'; base-uri 'none'; form-action 'none'"
    )
    return resp
