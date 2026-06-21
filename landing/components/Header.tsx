import { Github } from "lucide-react";
import { LINK_GITHUB, URL_CHATBOT } from "@/lib/constants";

export function Header() {
  return (
    <header className="bg-primary">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-5 text-primary-foreground sm:px-8">
        <a href="#top" className="text-lg font-extrabold tracking-tight">
          Arcos Transparente
        </a>

        <nav aria-label="Principal" className="flex items-center gap-5 text-sm">
          <a
            href={LINK_GITHUB}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-white/80 hover:text-white"
          >
            <Github className="h-4 w-4" aria-hidden="true" /> GitHub
            <span className="sr-only"> (abre em nova aba)</span>
          </a>
          <a
            href={URL_CHATBOT}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex min-h-[44px] items-center rounded-md bg-white px-4 py-2.5 font-semibold text-primary hover:bg-white/90"
          >
            Experimente →<span className="sr-only"> (abre em nova aba)</span>
          </a>
        </nav>
      </div>
    </header>
  );
}
