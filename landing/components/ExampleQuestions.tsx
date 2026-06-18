"use client";

import { useState } from "react";
import { Banknote, Bus, Truck, Users, type LucideIcon } from "lucide-react";
import { DATA_RANGE } from "@/lib/constants";

const categories: {
  icon: LucideIcon;
  title: string;
  themes: string[];
  questions: string[];
}[] = [
  {
    icon: Banknote,
    title: "Dinheiro público",
    themes: ["Gastos", "Receitas", "Contratos", "Licitações"],
    questions: [
      "Quanto a prefeitura gastou com saúde em 2025?",
      "Quais foram os maiores contratos do ano?",
      "Quem ganhou a licitação 147/2025?",
      "Quanto a prefeitura arrecadou em 2025?",
    ],
  },
  {
    icon: Users,
    title: "Pessoas e salários",
    themes: ["Salários", "Servidores", "Câmara", "Prefeitura"],
    questions: [
      "Qual foi o salário do prefeito em março de 2025?",
      "Quais são os maiores salários do município?",
      "Quantas pessoas trabalham na saúde?",
      "Quais são os cargos e salários da Câmara?",
    ],
  },
  {
    icon: Truck,
    title: "Bens, frota e operação",
    themes: ["Frota", "Patrimônio", "Almoxarifado", "Diárias"],
    questions: [
      "Quais veículos da prefeitura mais gastam com manutenção?",
      "Quanto foi gasto com diárias em 2025?",
      "Quais bens a prefeitura tem registrados?",
      "O que tem no estoque do almoxarifado?",
    ],
  },
  {
    icon: Bus,
    title: "Serviços e cidade",
    themes: ["Telefones úteis", "Ônibus", "Secretarias"],
    questions: [
      "Qual é o telefone da Secretaria de Saúde?",
      "Quais são os horários de ônibus?",
      "Como funciona a tarifa zero?",
      "Onde encontro os contatos da prefeitura?",
    ],
  },
];

function QuestionButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* clipboard unavailable — ignore */
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  return (
    <button
      type="button"
      onClick={copy}
      aria-label={`Copiar pergunta: ${text}`}
      className="group flex w-full items-start gap-2 text-left text-lg font-medium leading-snug text-slate-800 hover:text-primary"
    >
      <span aria-hidden="true" className="text-primary">
        ›
      </span>
      <span className="flex-1">{text}</span>
      <span
        className={`shrink-0 text-xs font-semibold text-primary transition-opacity ${
          copied ? "opacity-100" : "opacity-0 group-hover:opacity-100"
        }`}
      >
        {copied ? "Copiado!" : "Copiar"}
      </span>
    </button>
  );
}

export function ExampleQuestions() {
  return (
    <section id="perguntas" className="bg-white py-24">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <h2 className="text-4xl font-black tracking-tight text-slate-900">
          Pergunte sobre a cidade do seu jeito.
        </h2>
        <p className="mt-4 max-w-2xl text-xl leading-relaxed text-slate-600">
          Escolha um tema ou faça uma pergunta livre. A ferramenta busca nos
          dados públicos e mostra a resposta com a fonte.
        </p>

        <div className="mt-12 grid gap-6 md:grid-cols-2">
          {categories.map((cat) => (
            <div
              key={cat.title}
              className="rounded-2xl border border-slate-200 bg-slate-50 p-7 transition-shadow hover:shadow-lg"
            >
              <div className="flex items-center gap-4">
                <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-md shadow-primary/20">
                  <cat.icon className="h-7 w-7" aria-hidden="true" />
                </span>
                <h3 className="text-2xl font-black tracking-tight text-slate-900">
                  {cat.title}
                </h3>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {cat.themes.map((t) => (
                  <span
                    key={t}
                    className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-500 ring-1 ring-slate-200"
                  >
                    {t}
                  </span>
                ))}
              </div>
              <ul className="mt-5 space-y-2.5">
                {cat.questions.map((q) => (
                  <li key={q}>
                    <QuestionButton text={q} />
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <p className="mt-12 text-slate-500">{DATA_RANGE}</p>
      </div>
    </section>
  );
}
