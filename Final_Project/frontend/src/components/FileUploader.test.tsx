import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import JSZip from "jszip";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { api, ApiError } from "../api/client";
import FileUploader, { itemsFromZip } from "./FileUploader";

function renderUploader() {
  render(
    <MemoryRouter>
      <FileUploader />
    </MemoryRouter>,
  );
  // The hidden <input type="file"> behind the "Choose files" button.
  return document.querySelector<HTMLInputElement>('input[type="file"]')!;
}

function sourceFile(name: string, content = "import os\n") {
  return new File([content], name, { lastModified: 1 });
}

async function zipOf(entries: Record<string, string>, name = "project.zip") {
  const zip = new JSZip();
  for (const [path, content] of Object.entries(entries)) zip.file(path, content);
  return new File([await zip.generateAsync({ type: "uint8array" })], name);
}

describe("FileUploader", () => {
  it("queues supported files and rejects unsupported ones", async () => {
    const input = renderUploader();
    await userEvent.upload(input, [sourceFile("app.py"), sourceFile("notes.txt")], {
      applyAccept: false,
    });

    expect(screen.getByText("app.py")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
    expect(screen.getByText(/Unsupported file type/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Analyze 1 file" })).toBeEnabled();
  });

  it("analyzes queued files and shows the result", async () => {
    const analyze = vi.spyOn(api, "analyzeFile").mockResolvedValue({
      file: "app.py",
      language: "python",
      dependencies_found: 1,
      relationships_stored: 1,
      symbols_stored: 2,
      dependencies: [{ type: "import", target: "os", resolved_target: null }],
    });

    const input = renderUploader();
    await userEvent.upload(input, sourceFile("app.py"));
    await userEvent.click(screen.getByRole("button", { name: "Analyze 1 file" }));

    expect(await screen.findByText("Stored")).toBeInTheDocument();
    expect(analyze).toHaveBeenCalledWith("app.py", "import os\n", "python");
    expect(screen.getByText(/1 dependencies, 2 symbols stored/)).toBeInTheDocument();
  });

  it("shows the backend error when analysis fails", async () => {
    vi.spyOn(api, "analyzeFile").mockRejectedValue(new ApiError("Neo4j is down", 503));

    const input = renderUploader();
    await userEvent.upload(input, sourceFile("app.py"));
    await userEvent.click(screen.getByRole("button", { name: "Analyze 1 file" }));

    expect(await screen.findByText("Failed")).toBeInTheDocument();
    expect(screen.getByText("Neo4j is down")).toBeInTheDocument();
  });

  it("unpacks a ZIP into its source files with folder paths", async () => {
    const input = renderUploader();
    const zip = await zipOf({
      "src/app.py": "import utils\n",
      "src/utils.py": "x = 1\n",
      "README.md": "# hi",
      "node_modules/pkg/index.js": "module.exports = 1",
    });

    await userEvent.upload(input, zip);

    expect(await screen.findByText("src/app.py")).toBeInTheDocument();
    expect(screen.getByText("src/utils.py")).toBeInTheDocument();
    expect(screen.queryByText(/node_modules/)).not.toBeInTheDocument();
    expect(
      screen.getByText("project.zip: 2 source files added, 2 other files skipped."),
    ).toBeInTheDocument();
  });

  it("reports a file that is not a valid ZIP", async () => {
    const input = renderUploader();
    await userEvent.upload(input, new File(["not a zip"], "broken.zip"));

    await waitFor(() =>
      expect(
        screen.getByText("broken.zip could not be read as a ZIP archive."),
      ).toBeInTheDocument(),
    );
  });
});

describe("itemsFromZip", () => {
  it("keeps file contents so they can be sent to the backend", async () => {
    const { items } = await itemsFromZip(await zipOf({ "lib/a.ts": "export const a = 1;" }));

    expect(items).toHaveLength(1);
    expect(items[0]).toMatchObject({ path: "lib/a.ts", language: "typescript", status: "queued" });
    expect(await items[0].file.text()).toBe("export const a = 1;");
  });
});
