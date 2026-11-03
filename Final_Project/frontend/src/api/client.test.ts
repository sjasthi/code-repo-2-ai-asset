import { describe, expect, it, vi } from "vitest";
import { api, ApiError, API_URL, detectLanguage } from "./client";

function mockFetch(response: Partial<Response> | Error) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async () => {
    if (response instanceof Error) throw response;
    return response as Response;
  });
}

describe("api client", () => {
  it("repeats array query params and sends the other options", async () => {
    const fetchSpy = mockFetch({
      ok: true,
      json: async () => ({ query: "Task", total: 0, limit: 50, offset: 0, results: [] }),
    });

    await api.searchSymbols("Task", ["class", "function"], true);

    const url = new URL(String(fetchSpy.mock.calls[0][0]));
    expect(url.origin + url.pathname).toBe(`${API_URL}/search/symbols`);
    expect(url.searchParams.getAll("type")).toEqual(["class", "function"]);
    expect(url.searchParams.get("fuzzy")).toBe("true");
  });

  it("posts a JSON body when analyzing a file", async () => {
    const fetchSpy = mockFetch({ ok: true, json: async () => ({}) });

    await api.analyzeFile("src/app.py", "import os", "python");

    const [url, init] = fetchSpy.mock.calls[0];
    expect(String(url)).toContain("language=python");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual({
      file_path: "src/app.py",
      source_code: "import os",
    });
  });

  it("turns a FastAPI string detail into the error message", async () => {
    mockFetch({ ok: false, status: 404, json: async () => ({ detail: "Not found" }) });

    await expect(api.searchFiles("x")).rejects.toMatchObject({
      message: "Not found",
      status: 404,
    });
  });

  it("joins FastAPI validation errors", async () => {
    mockFetch({
      ok: false,
      status: 422,
      json: async () => ({ detail: [{ msg: "field required" }, { msg: "bad value" }] }),
    });

    await expect(api.searchFiles("x")).rejects.toThrow("field required; bad value");
  });

  it("reports an unreachable backend", async () => {
    mockFetch(new TypeError("Failed to fetch"));

    const error = await api.health().catch((err) => err);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(0);
    expect(error.message).toMatch(/Cannot reach the backend/);
  });
});

describe("detectLanguage", () => {
  it.each([
    ["app.py", "python"],
    ["src/index.JSX", "javascript"],
    ["lib/util.mts", "typescript"],
    ["README.md", null],
    ["Makefile", null],
  ])("%s -> %s", (name, language) => {
    expect(detectLanguage(name)).toBe(language);
  });
});
