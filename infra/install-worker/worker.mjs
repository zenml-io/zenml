// Cloudflare Worker that serves the one-line installers on zenml.io.
//
// Bound only to the zenml.io/install* routes (see wrangler.toml), it serves
// each script straight from GitHub, without a redirect hop, so that
// `curl -fsSL https://zenml.io/install | bash` works:
//
//   /install         install.sh from zenml-io/zenml: asks ZenML, Kitaru or both
//   /install-zenml   install-zenml.sh from zenml-io/zenml
//   /install-kitaru  install.sh from zenml-io/kitaru, as kitaru.ai/install serves
//
// Each also answers with a trailing slash or a `.sh` suffix. The scripts come
// from `main`: for ZenML that is the latest release (plus backports), so an
// installer change reaches users with a release, not when it lands on develop.
// Any other path under the routes (/installation, say) goes to the website.

const ZENML_MAIN = "https://raw.githubusercontent.com/zenml-io/zenml/main";
const KITARU_MAIN = "https://raw.githubusercontent.com/zenml-io/kitaru/main";

export const INSTALLERS = new Map([
  ["/install", `${ZENML_MAIN}/install.sh`],
  ["/install-zenml", `${ZENML_MAIN}/install-zenml.sh`],
  ["/install-kitaru", `${KITARU_MAIN}/install.sh`],
]);

export function installerFor(pathname) {
  const path = pathname.replace(/\/+$/, "").replace(/\.sh$/, "");
  return INSTALLERS.get(path);
}

/**
 * Serve one script from GitHub, cached at the edge for five minutes so a
 * release lands quickly without hammering GitHub.
 */
export async function serveInstaller(request, url) {
  if (request.method !== "GET" && request.method !== "HEAD") {
    return new Response("Method not allowed\n", { status: 405 });
  }
  // A shell piping this into bash runs whatever it gets, so a failure must be
  // a non-2xx status (curl -f then prints nothing), never an HTML error page.
  const unavailable = () =>
    new Response(
      "This installer is temporarily unavailable. See https://docs.zenml.io/getting-started/installation\n",
      { status: 502, headers: { "content-type": "text/plain; charset=utf-8" } },
    );
  let upstream;
  try {
    upstream = await fetch(url, { cf: { cacheTtl: 300, cacheEverything: true } });
  } catch {
    // DNS, connection, and timeout failures reject rather than resolve.
    return unavailable();
  }
  if (!upstream.ok) {
    return unavailable();
  }
  return new Response(request.method === "HEAD" ? null : upstream.body, {
    status: 200,
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "cache-control": "public, max-age=300",
      "x-content-type-options": "nosniff",
    },
  });
}

export default {
  async fetch(request) {
    const installer = installerFor(new URL(request.url).pathname);
    return installer ? serveInstaller(request, installer) : fetch(request);
  },
};
