import { MessageSquare, Search, FileText, Scale } from "lucide-react";

const steps = [
  {
    icon: MessageSquare,
    title: "Você pergunta",
    body: "Digite sua dúvida do jeito que falaria no dia a dia.",
  },
  {
    icon: Search,
    title: "O sistema procura",
    body: "Ele busca a informação nos dados públicos disponíveis.",
  },
  {
    icon: FileText,
    title: "Você confere a resposta",
    body: "A resposta vem com a fonte, o período consultado e os dados encontrados.",
  },
];

export function HowItWorks() {
  return (
    <section className="bg-slate-50 py-24">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-4xl font-black tracking-tight text-slate-900">
            Funciona como uma conversa.
          </h2>
          <p className="mt-4 text-xl leading-relaxed text-slate-600">
            De graça, sem cadastro e sem precisar abrir planilhas.
          </p>
        </div>

        <div className="relative mt-16 grid gap-12 md:grid-cols-3 md:gap-8">
          {/* Linha conectando os passos (apenas no desktop) */}
          <div
            aria-hidden="true"
            className="absolute left-[16.66%] right-[16.66%] top-7 hidden h-0.5 bg-slate-200 md:block"
          />
          {steps.map((step, i) => (
            <div key={step.title} className="relative text-center">
              <div className="relative z-10 mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary text-xl font-black text-primary-foreground ring-8 ring-slate-50">
                {i + 1}
              </div>
              <step.icon
                className="mx-auto mt-5 h-6 w-6 text-primary"
                aria-hidden="true"
              />
              <h3 className="mt-3 text-lg font-bold text-slate-900">
                {step.title}
              </h3>
              <p className="mx-auto mt-2 max-w-xs leading-relaxed text-slate-600">
                {step.body}
              </p>
            </div>
          ))}
        </div>

        <p className="mt-14 flex items-center justify-center gap-2 text-center text-sm text-slate-500">
          <Scale className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
          O{" "}
          <strong className="font-semibold text-slate-700">
            Arcos Transparente
          </strong>{" "}
          só consulta informações públicas. Nada é alterado.
        </p>
      </div>
    </section>
  );
}
