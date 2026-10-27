import { useState } from "react";
import FileUploader from "../components/FileUploader";
import RepositoryImport from "../components/RepositoryImport";

type Tab = "files" | "repository";

export default function UploadPage() {
  const [tab, setTab] = useState<Tab>("files");

  return (
    <>
      <h1>Add code to the graph</h1>
      <p className="lead">
        Upload source files or import a GitHub repository. Each file’s symbols and
        imports are stored so you can search and trace dependencies.
      </p>

      <div className="tabs" role="tablist" aria-label="Source">
        <button
          role="tab"
          type="button"
          aria-selected={tab === "files"}
          className={tab === "files" ? "tab tab--active" : "tab"}
          onClick={() => setTab("files")}
        >
          Files
        </button>
        <button
          role="tab"
          type="button"
          aria-selected={tab === "repository"}
          className={tab === "repository" ? "tab tab--active" : "tab"}
          onClick={() => setTab("repository")}
        >
          GitHub repository
        </button>
      </div>

      <div role="tabpanel">
        {tab === "files" ? <FileUploader /> : <RepositoryImport />}
      </div>
    </>
  );
}
