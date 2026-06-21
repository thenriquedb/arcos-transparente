import { MessageSquare } from "lucide-react";

// Example questions shown as chat-suggestion cards alongside the problem copy.
const EXAMPLE_QUESTIONS = [
  "Quanto foi gasto com diárias em 2025?",
  "Quem ganhou determinada licitação?",
  "Quais contratos estão ativos?",
  "Quanto a prefeitura recebeu em transferências?",
  "Qual o telefone de uma secretaria?",
  "Quais são os horários de ônibus?",
];

export function Problem() {
  return (
    <section className="bg-white py-24">
      <div className="mx-auto grid max-w-6xl items-start gap-12 px-5 sm:px-8 lg:grid-cols-2 lg:gap-16">
        {/* Texto */}
        <div>
          <p className="text-sm font-bold uppercase tracking-widest text-primary">
            O problema
          </p>
          <h2 className="mt-3 text-4xl font-black leading-tight tracking-tight text-slate-900">
            Os dados são públicos.
            <br />
            <span className="text-slate-500">
              Mas nem sempre são fáceis de encontrar.
            </span>
          </h2>
          <div className="mt-6 space-y-4 text-lg leading-relaxed text-slate-600">
            <p>
              As informações existem, mas muitas vezes estão espalhadas em
              portais, planilhas, relatórios e páginas difíceis de navegar.
            </p>
            <p>
              Descobrir quanto custou uma obra, quem ganhou uma licitação ou
              quanto foi gasto em determinada área não deveria ser complicado.
            </p>
            <p>
              O{" "}
              <strong className="font-semibold text-slate-900">
                Arcos Transparente
              </strong>{" "}
              ajuda a transformar esses dados em respostas mais simples, para
              qualquer pessoa entender.
            </p>
          </div>
        </div>

        {/* Cards de exemplos de perguntas */}
        <div className="space-y-3">
          {EXAMPLE_QUESTIONS.map((q) => (
            <div
              key={q}
              className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3.5 text-slate-700"
            >
              <MessageSquare
                className="h-5 w-5 shrink-0 text-primary/60"
                aria-hidden="true"
              />
              <span className="text-base leading-snug">{q}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
