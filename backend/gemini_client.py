"""Opt-in, bounded Gemini access. Never performs web grounding or retries."""
import hashlib
import json
import os
from contextlib import closing
from pathlib import Path
import sqlite3
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MODEL = 'gemini-3.5-flash-lite'  # Google pricing page checked 2026-11-18.
CACHE_PATH = Path(__file__).resolve().parent / '.gemini-usage.sqlite3'


class AIError(Exception):
    pass


def _request(prompt, schema, api_key, model):
    if os.environ.get('CI') or os.environ.get('GEMINI_TEST_MODE') == 'true':
        raise AIError('Live Gemini calls are disabled in tests and CI.')
    payload = {'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': {
        'responseMimeType': 'application/json', 'responseJsonSchema': schema,
        'maxOutputTokens': 1024, 'temperature': 0}}
    req = Request('https://generativelanguage.googleapis.com/v1beta/models/' + model + ':generateContent',
                  data=json.dumps(payload).encode(), method='POST', headers={
                      'Content-Type': 'application/json', 'x-goog-api-key': api_key})
    try:
        with urlopen(req, timeout=15) as response:
            raw = response.read(100_001)
        if len(raw) > 100_000:
            raise AIError('Gemini response was too large.')
        envelope = json.loads(raw)
        if envelope['candidates'][0].get('finishReason') != 'STOP':
            raise AIError('Gemini response was incomplete.')
        return json.loads(envelope['candidates'][0]['content']['parts'][0]['text'])
    except HTTPError as error:
        if error.code == 429:
            raise AIError('Gemini quota is exhausted; try later. Catalogue search is still available.') from None
        if error.code == 402:
            raise AIError('Gemini reported a billing error; stop and check the Free-tier project without enabling billing.') from None
        if error.code in (403, 404):
            raise AIError('Gemini denied access or the model is unavailable; stop and check project model access.') from None
        if error.code == 400:
            raise AIError('Gemini rejected the request (HTTP 400). Check the API key and request configuration; do not enable billing.') from None
        raise AIError(f'Gemini request failed (HTTP {error.code}). Check the service status and configuration.') from None
    except (URLError, TimeoutError, OSError, ValueError, KeyError, IndexError, TypeError):
        raise AIError('Gemini is unavailable or returned invalid output.') from None


def check_config():
    if os.environ.get('GEMINI_ENABLED', '').lower() != 'true':
        raise AIError('Gemini is disabled. Catalogue search is still available.')
    if os.environ.get('GEMINI_FREE_TIER_CONFIRMED', '').lower() != 'true':
        raise AIError('Confirm a dedicated Free-tier project with no linked billing before enabling Gemini.')
    key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not key:
        raise AIError('Gemini API key is missing.')
    model = os.environ.get('GEMINI_MODEL', MODEL)
    if model != MODEL:
        raise AIError('Model is not in the checked free-tier allowlist.')
    return key, model


def generate(prompt, schema, *, path=CACHE_PATH, transport=_request):
    key, model = check_config()
    if not isinstance(prompt, str) or not 1 <= len(prompt) <= 16000:
        raise AIError('Input exceeds the allowed size.')
    digest = hashlib.sha256(json.dumps([model, prompt, schema], sort_keys=True).encode()).hexdigest()
    now = int(time.time())
    with closing(sqlite3.connect(path, timeout=5)) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS calls (created INTEGER NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, created INTEGER NOT NULL, value TEXT NOT NULL)')
        db.execute('BEGIN IMMEDIATE')
        cached = db.execute('SELECT value FROM cache WHERE key=? AND created>?', (digest, now - 3600)).fetchone()
        if cached:
            return json.loads(cached[0])
        recent = db.execute('SELECT count(*) FROM calls WHERE created>?', (now - 86400,)).fetchone()[0]
        minute = db.execute('SELECT count(*) FROM calls WHERE created>?', (now - 60,)).fetchone()[0]
        if recent >= 20 or minute >= 2:
            raise AIError('Local Gemini request limit reached; catalogue search is still available.')
        db.execute('INSERT INTO calls VALUES (?)', (now,))
        db.commit()
    # One attempt only. The reservation above counts failures as well as successes.
    result = transport(prompt, schema, key, model)
    with closing(sqlite3.connect(path, timeout=5)) as db, db:
        db.execute('INSERT OR REPLACE INTO cache VALUES (?,?,?)', (digest, now, json.dumps(result)))
        db.execute('DELETE FROM cache WHERE created < ?', (now - 86400,))
        db.execute('DELETE FROM calls WHERE created < ?', (now - 86400,))
    return result
