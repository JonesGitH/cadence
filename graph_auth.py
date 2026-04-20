import threading
import msal
from database import get_setting, set_setting

TENANT = 'common'
SCOPES = ['Calendars.ReadWrite', 'Mail.Send']

_lock       = threading.Lock()
_auth_state = {}


def _load_cache():
    cache = msal.SerializableTokenCache()
    data  = get_setting('graph_token_cache', '')
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
    cache = _load_cache()
    app   = _build_app(cache)
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and 'access_token' in result:
            _save_cache(cache)
            return result['access_token']
    raise RuntimeError('not_connected')


def get_headers():
    return {
        'Authorization': f'Bearer {get_token()}',
        'Content-Type':  'application/json',
    }


def start_device_flow():
    cache = _load_cache()
    app   = _build_app(cache)
    flow  = app.initiate_device_flow(SCOPES)
    if 'user_code' not in flow:
        raise RuntimeError(flow.get('error_description', 'Could not start authentication.'))
    with _lock:
        _auth_state.clear()
        _auth_state.update({'app': app, 'flow': flow, 'cache': cache, 'done': False, 'error': None})
    threading.Thread(target=_run_device_flow, daemon=True).start()
    return {'verification_url': flow['verification_uri'], 'user_code': flow['user_code']}


def _run_device_flow():
    with _lock:
        app, flow, cache = _auth_state['app'], _auth_state['flow'], _auth_state['cache']
    result = app.acquire_token_by_device_flow(flow)
    with _lock:
        if 'access_token' in result:
            _save_cache(cache)
            _auth_state['done'] = True
        else:
            _auth_state['error'] = result.get('error_description', 'Authentication failed.')


def poll_auth():
    with _lock:
        return {'done': _auth_state.get('done', False), 'error': _auth_state.get('error')}


def is_connected():
    try:
        get_token()
        return True
    except RuntimeError:
        return False


def disconnect():
    set_setting('graph_token_cache', '')
