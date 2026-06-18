import { ArrowRight, Scale } from "lucide-react";
import { URL_CHATBOT } from "@/lib/constants";

const LAI_URL =
  "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12527.htm";

export function FinalCTA() {
  return (
    <section id="cta" className="bg-white py-24">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <h2 className="text-center text-4xl font-black leading-tight tracking-tight text-slate-900 sm:text-5xl">
          Consultar dados públicos é um direito seu.
        </h2>
      </div>
      <div className="mx-auto mt-12 grid max-w-6xl items-center gap-12 px-5 sm:px-8 lg:grid-cols-2 lg:gap-16">
        {/* Texto e ação */}
        <div>
          <p className="text-lg leading-relaxed text-slate-600">
            A{" "}
            <a
              href={LAI_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-slate-900 underline decoration-primary/40 underline-offset-2 hover:decoration-primary"
            >
              Lei de Acesso à Informação
            </a>{" "}
            garante que qualquer cidadão possa acessar informações públicas. O{" "}
            <strong className="font-semibold text-slate-900">
              Arcos Transparente
            </strong>{" "}
            ajuda a tornar esse caminho mais simples, aproximando os dados
            oficiais da população.
          </p>
          <a
            href={URL_CHATBOT}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-8 inline-flex items-center gap-2 rounded-lg bg-primary px-8 py-4 text-lg font-bold text-primary-foreground hover:bg-primary-hover"
          >
            Fazer uma pergunta <ArrowRight className="h-5 w-5" aria-hidden="true" />
          </a>
        </div>

        {/* Box de destaque sobre cidadania */}
        <div className="rounded-3xl bg-primary/5 p-8 ring-1 ring-primary/15 sm:p-10">
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10">
            <Scale className="h-7 w-7 text-primary" aria-hidden="true" />
          </span>
          <p className="mt-6 text-2xl font-black leading-snug tracking-tight text-slate-900">
            Buscar, consultar e compartilhar dados públicos não é crime.{" "}
            <span className="text-primary">É exercer cidadania.</span>
          </p>
        </div>
      </div>
    </section>
  );
}
