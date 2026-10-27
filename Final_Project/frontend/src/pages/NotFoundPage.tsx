import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <>
      <h1>Page not found</h1>
      <p className="lead">
        That address doesn’t match a page. Go to <Link to="/upload">Upload</Link>.
      </p>
    </>
  );
}
