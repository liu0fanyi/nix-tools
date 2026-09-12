const PORTAL = "https://nas.wttliou.top/authelia/";
const AUTHZ =
  "https://nas.wttliou.top/authelia/api/authz/forward-auth";

async function forwardRequest(request, deviceApi) {
  const supplied = request.headers.get("X-Request-ID") || "";
  const requestId = /^[A-Za-z0-9-]{1,64}$/.test(supplied)
    ? supplied : `edge-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const started = Date.now();
  const headers = new Headers(request.headers);
  headers.set("X-Request-ID", requestId);
  // Fetch bodies are decoded by the edge runtime. Prefer the identity cache
  // variant so wrapping the body cannot retain a stale compression envelope.
  headers.set("Accept-Encoding", "identity");
  try {
    const response = await fetch(request, {
      headers,
      redirect: "manual",
      eo: { timeoutSetting: {
        connectTimeout: 15000,
        readTimeout: deviceApi ? 300000 : 60000,
        writeTimeout: deviceApi ? 300000 : 60000,
      } },
    });
    console.log(JSON.stringify({ request_id: requestId, stage: "forward",
      status: response.status, elapsed_ms: Date.now() - started }));
    const resultHeaders = new Headers(response.headers);
    resultHeaders.delete("Content-Encoding");
    resultHeaders.delete("Content-Length");
    // This origin advertises its private :5009 HTTP/3 listener.
    resultHeaders.delete("Alt-Svc");
    const result = new Response(response.body, {
      status: response.status, statusText: response.statusText, headers: resultHeaders,
    });
    result.headers.set("X-Request-ID", requestId);
    if (deviceApi) result.headers.set("Cache-Control", "private, no-store");
    return result;
  } catch (error) {
    // Do not log URLs, credentials or arbitrary exception messages.
    console.error(JSON.stringify({ request_id: requestId, stage: "forward",
      error: "edge_forward_failed", elapsed_ms: Date.now() - started }));
    return new Response(JSON.stringify({ error: "edge_forward_failed",
      request_id: requestId, stage: "forward", outcome: "unknown",
      elapsed_ms: Date.now() - started }), { status: 502, headers: {
        "Content-Type": "application/json", "Cache-Control": "private, no-store",
        "X-Request-ID": requestId,
      } });
  }
}

function loginRedirect(request) {
  const location = `${PORTAL}?rd=${encodeURIComponent(request.url)}`;

  return new Response(null, {
    status: 302,
    headers: {
      Location: location,
      "Cache-Control": "private, no-store",
    },
  });
}

async function handleRequest(request) {
  const url = new URL(request.url);

  // Authelia itself and the token-authenticated mobile API do not use the
  // interactive browser login.
  if (
    url.pathname.startsWith("/authelia/") ||
    url.pathname === "/device-api" ||
    url.pathname.startsWith("/device-api/")
  ) {
    return forwardRequest(request, url.pathname === "/device-api" || url.pathname.startsWith("/device-api/"));
  }

  const headers = new Headers();
  const cookie = request.headers.get("Cookie");
  const authorization = request.headers.get("Authorization");

  if (cookie) headers.set("Cookie", cookie);
  if (authorization) headers.set("Authorization", authorization);

  headers.set("X-Forwarded-Method", request.method);
  headers.set("X-Forwarded-Proto", url.protocol.replace(":", ""));
  headers.set("X-Forwarded-Host", url.host);
  headers.set("X-Forwarded-URI", url.pathname + url.search);

  const clientIp =
    request.eo?.clientIp ||
    request.headers.get("EO-Connecting-IP") ||
    "127.0.0.1";
  headers.set("X-Forwarded-For", clientIp);

  // Never reuse an authorization response from the CDN cache itself.
  const authUrl = new URL(AUTHZ);
  authUrl.searchParams.set("authelia_url", PORTAL);
  authUrl.searchParams.set(
    "_edge_auth_nonce",
    `${Date.now()}-${Math.random()}`
  );

  let authResponse;
  try {
    authResponse = await fetch(authUrl.toString(), {
      method: "GET",
      headers,
      redirect: "manual",
    });
  } catch (error) {
    return new Response("Authentication service unavailable", {
      status: 503,
      headers: {
        "Cache-Control": "private, no-store",
      },
    });
  }

  if (authResponse.status >= 200 && authResponse.status < 300) {
    // This subrequest is the first operation allowed to consult EdgeOne's
    // content cache or pull from the origin.
    return forwardRequest(request, false);
  }

  const location = authResponse.headers.get("Location");
  if (location) {
    return new Response(null, {
      status: 302,
      headers: {
        Location: new URL(location, PORTAL).toString(),
        "Cache-Control": "private, no-store",
      },
    });
  }

  return loginRedirect(request);
}

addEventListener("fetch", (event) => {
  event.respondWith(handleRequest(event.request));
});
