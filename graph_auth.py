import threading
import time

import msal

from database import get_setting, set_setting

TENANT = 'common'
SCOPES = ['Calendars.ReadWrite', 'Mail.Send']

_TOKEN_REFRESH_SKEW = 60  # seconds before expiry to refresh proactively

_lock = threading.Lock()
_auth_done = threading.Event()
_auth_state = {'app': None, 'flow': None, 'cache': None, 'error': None}

_token_cache_mem = {'token': None, 'expires': 0.0}
_token_lock = threading.Lock()


def _load_cache():
    cache = msal.SerializableTokenCache()
    data = get_setting('graph_token_cache', '')
    if data:
        cache.deserialize(data)
    return cache


def _save_cache(cache):
    if cache.has_state_changed:
        set_setting('graph_token_cache', cache.serialize())


def _build_app(cache):
    client_id = get_setting('graph_client_id', '')
    if not client_id:
        raise RuntimeError('no_client_id')
    return msal.PublicClientApplication(
        client_id,
        authority=f'https://login.microsoftonline.com/{TENANT}',
        token_cache=cache,
    )


def get_token():
    with _token_lock:
        if _token_cache_mem['token'] and time.monotonic() < _token_cache_mem['expires']:
            return _token_cache_mem['token']

    cache = _load_cache()
    app = _build_app(cache)
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and 'access_token' in result:
            _save_cache(cache)
            expires_in = int(result.get('expires_in', 3600))
            with _token_lock:
                _token_cache_mem['token'] = result['access_token']
                _token_cache_mem['expires'] = time.monotonic() + max(0, expires_in - _TOKEN_REFRESH_SKEW)
            return result['access_token']
    raise RuntimeError('not_connected')


def _invalidate_token():
    with _token_lock:
        _token_cache_mem['token'] = None
        _token_cache_mem['expires'] = 0.0


def get_headers():
    return {
        'Authorization': f'Bearer {get_token()}',
        'Content-Type':  'application/json',
    }


def start_device_flow():
    cache = _load_cache()
    app = _build_app(cache)
    flow = app.initiate_device_flow(SCOPES)
    if 'user_code' not in flow:
        raise RuntimeError(flow.get('error_description', 'Could not start authentication.'))
    with _lock:
        _auth_state.update({'app': app, 'flow': flow, 'cache': cache, 'error': None})
    _auth_done.clear()
    threading.Thread(target=_run_device_flow, daemon=True).start()
    return {'verification_url': flow['verification_uri'], 'user_code': flow['user_code']}


def _run_device_flow():
    with _lock:
        app, flow, cache = _auth_state['app'], _auth_state['flow'], _auth_state['cache']
    result = app.acquire_token_by_device_flow(flow)
    if 'access_token' in result:
        _save_cache(cache)
        _invalidate_token()
        _auth_done.set()
    else:
        with _lock:
            _auth_state['error'] = result.get('error_description', 'Authentication failed.')
        _auth_done.set()


def poll_auth():
    with _lock:
        error = _auth_state.get('error')
    return {'done': _auth_done.is_set() and not error, 'error': error}


def is_connected():
    try:
        get_token()
        return True
    except RuntimeError:
        return False


def disconnect():
    set_setting('graph_token_cache', '')
    _invalidate_token()
