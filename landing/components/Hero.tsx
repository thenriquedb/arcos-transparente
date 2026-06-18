import { ArrowRight } from "lucide-react";
import { URL_CHATBOT } from "@/lib/constants";
import { ChatSimulation } from "./ChatSimulation";

export function Hero() {
  return (
    <section
      id="top"
      className="relative bg-primary pb-32 pt-12 text-primary-foreground"
    >
      <div className="mx-auto grid max-w-6xl items-start gap-10 px-5 sm:px-8 lg:grid-cols-[1.1fr_1fr]">
        <div>
          <h1 className="text-5xl font-black leading-tight">
            Dados públicos de Arcos em linguagem simples
          </h1>
          <p className="mt-6 max-w-md text-xl leading-relaxed text-white/85">
            Consulte gastos, salários, contratos, receitas, diárias e
            informações úteis da cidade usando perguntas simples, como se
            estivesse conversando no WhatsApp ou no ChatGPT.
          </p>
          <a
            href={URL_CHATBOT}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-8 inline-flex items-center gap-2 rounded-lg bg-white px-7 py-4 text-lg font-bold text-primary hover:bg-white/90"
          >
            Fazer uma pergunta <ArrowRight className="h-5 w-5" aria-hidden="true" />
          </a>
        </div>
        <div className="lg:-mb-40">
          <div className="rounded-2xl bg-white p-2 shadow-2xl">
            <ChatSimulation />
          </div>
        </div>
      </div>
    </section>
  );
}
