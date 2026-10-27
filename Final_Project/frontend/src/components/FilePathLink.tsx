import { Link } from "react-router-dom";

// Any file path shown in the UI links to its dependency view.
export default function FilePathLink({ path }: { path: string }) {
  return (
    <Link
      className="path"
      to={`/dependencies?file=${encodeURIComponent(path)}`}
    >
      {path}
    </Link>
  );
}
