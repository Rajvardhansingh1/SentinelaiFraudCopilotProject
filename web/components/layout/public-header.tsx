import Link from "next/link";
import { Button } from "@/components/ui/button";

export function PublicHeader() {
  return (
    <header className="flex items-center justify-between border-b border-bg-surface px-6 py-4">
      <Link href="/" className="text-lg font-semibold text-accent-teal">
        SentinelAI
      </Link>
      <nav className="flex items-center gap-6 text-sm text-text-primary/80">
        <Link href="/about" className="hover:text-text-primary">
          About
        </Link>
        <Link href="/install" className="hover:text-text-primary">
          Install
        </Link>
      </nav>
      <div className="flex items-center gap-2">
        <Link href="/login">
          <Button variant="ghost">Log in</Button>
        </Link>
        <Link href="/signup">
          <Button variant="primary">Sign up</Button>
        </Link>
      </div>
    </header>
  );
}
