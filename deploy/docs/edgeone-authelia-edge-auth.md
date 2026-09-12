# EdgeOne authentication before private CDN cache

`nas.wttliou.top` uses an EdgeOne Edge Function to run Authelia authorization
before EdgeOne is allowed to serve a cached private response. Caddy's existing
Authelia `forward_auth` remains enabled at the origin as a second check on cache
misses.

## Why this is required

Origin-only authentication is too late for a shared CDN cache:

```text
unsafe: client -> EdgeOne cache -> Caddy -> Authelia -> application
safe:   client -> Edge Function -> Authelia -> EdgeOne cache -> origin
```

On 2026-09-01 an unauthenticated request for `/dist/devices/` returned an
EdgeOne `HIT` with status 200. A unique query string and a direct-origin request
both returned the expected Authelia 302, proving that the cached authenticated
HTML had bypassed origin authorization. The management API still required
Authelia, but the public cache hit invalidated the security boundary.

## Source of truth

The deployed function source is tracked at:

```text
deploy/edge-functions/authelia-edge-auth.js
```

The code performs these operations for every protected request:

1. Forward the Authelia session cookie and trusted request metadata to
   `/authelia/api/authz/forward-auth`.
2. Add a unique authorization-query nonce so the authorization response itself
   cannot be reused from EdgeOne's content cache.
3. Only after a 2xx authorization response, call `fetch(request)`, which may use
   the EdgeOne content cache and falls back to the origin on a miss.
4. Redirect unauthenticated browsers to the Authelia portal.
5. Return 503 when the authorization subrequest fails. Authorization failures
   must fail closed.

`/authelia/` is excluded to avoid intercepting the login portal.
`/device-api/` is excluded because the Android client uses its own scoped bearer
token and cannot perform an interactive browser login. The Caddy allowlist and
tag-server token checks remain authoritative for that API.

## Initial EdgeOne console configuration

In the `wttliou.top` site:

1. Open **Edge Functions -> Function Management**.
2. Create a function from **Remote Authentication** or **Custom Function**.
3. Name it `authelia-edge-auth`, replace the template with the tracked source,
   and choose **Deploy Function Directly**. No environment variables or secrets
   are required.
4. Test the assigned `eo-edgefunctions.com` default hostname without cookies.
   It must return a 302 to `https://nas.wttliou.top/authelia/` and include
   `Cache-Control: private, no-store`.
5. Add trigger rule `nas-authelia-auth` with the sole condition
   `HOST equals nas.wttliou.top`. The function itself owns the two path
   exclusions.
6. In the top-level console, open **Toolbox -> Purge Cache**. Select site
   `wttliou.top`, content type `Hostname`, method `Mark Expired`, and submit
   `nas.wttliou.top` as the only line.

Do not purge before enabling the trigger: enabling the function first ensures
that old cache objects are already behind authorization while purge propagates.

## Validation

Use a client with no Authelia cookie:

```bash
curl -sS -D - -o /dev/null https://nas.wttliou.top/dist/devices/
curl -sS -D - -o /dev/null https://nas.wttliou.top/authelia/
curl -sS -D - -o /dev/null https://nas.wttliou.top/device-api/v1/enrollments
```

Expected results:

- the protected page is always 302 to Authelia with `private, no-store`;
- the Authelia portal is 200 and does not recurse;
- the disallowed GET to the enrollment path remains the Caddy 404, not an
  interactive-login redirect.

Then validate both browser branches:

- a private/incognito window must first show Authelia;
- a browser with a valid `authelia_session` cookie must open the device center
  directly.

The 2026-09-01 production validation passed all of the checks above. Two
successive cookie-free requests both returned 302 after the hostname purge.

## Updating and rollback

### 2026-09-07 upload forwarding diagnostics (console deployment pending)

The tracked source now wraps origin forwarding with request correlation and
exception handling. Device API connect timeout is 15s and read/write timeouts
are 300s, using `eo.timeoutSetting` in milliseconds. Other forwarding uses
60s read/write limits. Redirects remain manual so POST bodies and login cookies
are not silently redirected. Forwarding exceptions return non-cacheable JSON
502 with `error=edge_forward_failed`, `request_id`, `stage=forward`, elapsed
milliseconds and `outcome=unknown`; this is not proof of a timeout or a failed
origin operation. Log only correlation/status/timing, not URLs or credentials.

The device path exclusion skips interactive authorization, not Edge Functions.
It still passes through `fetch`. Keep scoped token checks at the origin and
keep device/auth API caching disabled in the EdgeOne rules; setting no-store
on a returned response cannot undo a cache hit that has already happened.

The source change alone does not update the EdgeOne console. Replace the full
function with the tracked JS and deploy, retaining the existing HOST trigger.
Do not paste Markdown link wrappers or a trailing character after the script.
After publishing, verify unauthenticated private-page redirects and device API
request-ID responses. Long transcoding still needs an asynchronous job/status
API: increasing fetch limits is only interim mitigation, not a guarantee.

Reference: https://cloud.tencent.cn/document/product/1552/81897


Edit the tracked JavaScript first, copy it into the EdgeOne editor, deploy it,
and validate the function's default hostname before changing the production
trigger. Keep the origin Caddy `forward_auth`; the Edge Function is not a reason
to remove defense in depth.

Never disable the trigger while private cache objects may still exist. For a
safe rollback:

1. make `nas.wttliou.top` non-cacheable at EdgeOne;
2. purge the hostname and verify a cookie-free request reaches the origin 302;
3. only then disable or delete the trigger.

The Free plan currently documents a monthly Edge Function allowance. Monitor
both request-count and CPU-time usage: a free-plan function rule may be disabled
when its allowance is exhausted, so quota state is part of the authentication
health check rather than merely a performance metric.

## References

- <https://edgeone.ai/zh/document/56723> — EdgeOne processing order
- <https://edgeone.ai/zh/document/57425> — remote authentication example
- <https://www.authelia.com/reference/guides/proxy-authorization/> — Authelia
  proxy authorization metadata and CookieSession

## 响应编码一致性修复（控制台发布待验收）
公网实测：请求br时响应声明Content-Encoding: br，但正文实际是未压缩JS，Node Brotli解码失败；无压缩请求取得完整JS。转发子请求现显式请求identity，包装响应移除旧Content-Encoding、Content-Length及源站Alt-Svc，保留CSP与认证边界。运行`node deploy/tests/test_edge_response.cjs`覆盖7种场景；这是模拟运行时已解码正文的回归，不代替EdgeOne实测。
控制台用`deploy/edge-functions/authelia-edge-auth.js`完整纯JS替换原函数，先验证调试域名，再验证公网JS/CSS/favicon的identity/gzip/br及登录。未认证私有资源仍应跳登录、device-api仍须令牌，不能因为资源可加载就把App401/502标为修复。
