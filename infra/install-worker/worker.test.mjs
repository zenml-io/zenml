// Tests for the zenml.io installer worker.
// Run: node --test infra/install-worker/worker.test.mjs
import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import worker from "./worker.mjs";

const ZENML = "https://raw.githubusercontent.com/zenml-io/zenml/main";
const KITARU = "https://raw.githubusercontent.com/zenml-io/kitaru/main";
const realFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = realFetch;
});

// Records what the worker fetched and answers with `response`.
function stubFetch(response) {
  const calls = [];
  globalThis.fetch = async (input) => {
    calls.push(input);
    if (response instanceof Error) throw response;
    return response.clone();
  };
  return calls;
}

const script = () =>
  new Response("#!/usr/bin/env bash\necho installer\n", { status: 200 });

const cases = [
  ["https://zenml.io/install", `${ZENML}/install.sh`],
  ["https://zenml.io/install/", `${ZENML}/install.sh`],
  ["https://zenml.io/install.sh", `${ZENML}/install.sh`],
  ["https://www.zenml.io/install", `${ZENML}/install.sh`],
  ["https://zenml.io/install-zenml", `${ZENML}/install-zenml.sh`],
  ["https://zenml.io/install-zenml.sh", `${ZENML}/install-zenml.sh`],
  ["https://zenml.io/install-kitaru", `${KITARU}/install.sh`],
  ["https://zenml.io/install-kitaru/", `${KITARU}/install.sh`],
];

for (const [input, upstream] of cases) {
  test(`${input} serves ${upstream}`, async () => {
    const calls = stubFetch(script());
    const response = await worker.fetch(new Request(input));
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("content-type"), "text/plain; charset=utf-8");
    assert.equal(response.headers.get("x-content-type-options"), "nosniff");
    assert.match(await response.text(), /^#!\/usr\/bin\/env bash/);
    assert.deepEqual(calls.map(String), [upstream]);
  });
}

for (const input of [
  "https://zenml.io/installation",
  "https://zenml.io/install-foo",
  "https://zenml.io/installer",
]) {
  test(`${input} is passed through to the website`, async () => {
    const calls = stubFetch(new Response("<html>site</html>", { status: 200 }));
    const request = new Request(input);
    const response = await worker.fetch(request);
    assert.equal(await response.text(), "<html>site</html>");
    assert.equal(calls.length, 1);
    assert.equal(calls[0], request);
  });
}

test("HEAD answers without a body", async () => {
  stubFetch(script());
  const response = await worker.fetch(
    new Request("https://zenml.io/install", { method: "HEAD" }),
  );
  assert.equal(response.status, 200);
  assert.equal(await response.text(), "");
});

test("other methods are refused without fetching", async () => {
  const calls = stubFetch(script());
  const response = await worker.fetch(
    new Request("https://zenml.io/install", { method: "POST", body: "x" }),
  );
  assert.equal(response.status, 405);
  assert.equal(calls.length, 0);
});

for (const [why, upstream] of [
  ["GitHub answers 404", new Response("Not Found", { status: 404 })],
  ["GitHub is unreachable", new TypeError("fetch failed")],
]) {
  test(`a 502 in plain text, never an error page, when ${why}`, async () => {
    stubFetch(upstream);
    const response = await worker.fetch(new Request("https://zenml.io/install-zenml"));
    assert.equal(response.status, 502);
    assert.equal(response.headers.get("content-type"), "text/plain; charset=utf-8");
    assert.match(await response.text(), /temporarily unavailable/);
  });
}
