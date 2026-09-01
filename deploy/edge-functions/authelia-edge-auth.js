const PORTAL = "https://nas.wttliou.top/authelia/";
const AUTHZ =
  "https://nas.wttliou.top/authelia/api/authz/forward-auth";

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
    return fetch(request);
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
    return fetch(request);
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
