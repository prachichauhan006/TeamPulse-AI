import { Link } from "react-router-dom";
import { EmptyState } from "../components/ui";

export function NotFound() {
  return <EmptyState title="Page not found" description="The page may have moved, or you may not have access to it." action={<Link to="/" className="btn-primary">Return to dashboard</Link>} />;
}
