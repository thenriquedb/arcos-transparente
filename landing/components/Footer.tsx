import { LINK_GITHUB } from "@/lib/constants";

export function Footer() {
  return (
    <footer className="bg-slate-900 py-10 text-slate-400">
      <div className="mx-auto max-w-6xl px-5 text-sm leading-relaxed sm:px-8">
        Dados públicos do município de Arcos (MG). Projeto independente, sem
        vínculo oficial com a prefeitura. Código aberto sob licença AGPL-3.0 ·{" "}
        <a
          href={LINK_GITHUB}
          target="_blank"
          rel="noopener noreferrer"
          className="underline hover:text-white"
        >
          Repositório
        </a>
      </div>
    </footer>
  );
}
