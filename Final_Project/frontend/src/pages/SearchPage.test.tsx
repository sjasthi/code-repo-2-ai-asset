import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { api, ApiError } from "../api/client";
import SearchPage from "./SearchPage";

function renderPage() {
  render(
    <MemoryRouter>
      <SearchPage />
    </MemoryRouter>,
  );
}

describe("SearchPage", () => {
  it("searches symbols with the chosen filters and lists results", async () => {
    const search = vi.spyOn(api, "searchSymbols").mockResolvedValue({
      query: "Task",
      total: 1,
      limit: 50,
      offset: 0,
      results: [
        { type: "class", name: "TaskManager", file_path: "tasks.py", line: 3, score: 1, match: "prefix" },
      ],
    });

    renderPage();
    await userEvent.click(screen.getByRole("checkbox", { name: "class" }));
    await userEvent.type(screen.getByRole("searchbox", { name: "Search query" }), "Task");
    await userEvent.click(screen.getByRole("button", { name: "Search" }));

    expect(await screen.findByText("TaskManager")).toBeInTheDocument();
    expect(search).toHaveBeenCalledWith("Task", ["class"], true);
    expect(screen.getByText(/Showing 1 of 1 results/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "tasks.py" })).toHaveAttribute(
      "href",
      "/dependencies?file=tasks.py",
    );
  });

  it("searches files in file mode", async () => {
    const search = vi.spyOn(api, "searchFiles").mockResolvedValue({
      query: "utils",
      total: 0,
      limit: 50,
      offset: 0,
      results: [],
    });

    renderPage();
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Search for" }), "files");
    await userEvent.type(screen.getByRole("searchbox", { name: "Search query" }), "utils");
    await userEvent.click(screen.getByRole("button", { name: "Search" }));

    expect(await screen.findByText(/No files match “utils”/)).toBeInTheDocument();
    expect(search).toHaveBeenCalledWith("utils");
  });

  it("shows an error message when the request fails", async () => {
    vi.spyOn(api, "searchSymbols").mockRejectedValue(
      new ApiError("Cannot reach the backend", 0),
    );

    renderPage();
    await userEvent.type(screen.getByRole("searchbox", { name: "Search query" }), "x");
    await userEvent.click(screen.getByRole("button", { name: "Search" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Cannot reach the backend");
  });
});
