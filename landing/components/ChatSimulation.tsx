"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowRight, Building2 } from "lucide-react";
import { URL_CHATBOT } from "@/lib/constants";

type Pair = { user: string; assistant: string };

const PAIRS: Pair[] = [
  {
    user: "Qual foi o salário do prefeito em março de 2025?",
    assistant:
      "Em março de 2025, o prefeito recebeu R$ 14.283,50 líquidos, já considerando os descontos registrados na folha.",
  },
  {
    user: "Quanto a prefeitura gastou com diárias em 2025?",
    assistant:
      "Posso buscar o total de diárias registradas em 2025 e mostrar o valor por período ou por órgão, conforme a base disponível.",
  },
  {
    user: "Quanto foi gasto com saúde no primeiro trimestre de 2025?",
    assistant:
      "No primeiro trimestre de 2025, a Secretaria de Saúde registrou R$ 4.182.340,00 em despesas empenhadas, com o período e a origem do dado indicados na resposta.",
  },
];

function useReducedMotion() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduced(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);
  return reduced;
}

function Avatar() {
  return (
    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
      <Building2 className="h-4 w-4 text-primary" aria-hidden="true" />
    </span>
  );
}

function UserBubble({ text, fading }: { text: string; fading: boolean }) {
  return (
    <div
      className={`flex justify-end transition-opacity duration-300 ${fading ? "opacity-0" : "opacity-100"
        }`}
    >
      <p className="max-w-[80%] rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground shadow-sm">
        {text}
      </p>
    </div>
  );
}

function AssistantBubble({
  children,
  fading,
}: {
  children: React.ReactNode;
  fading: boolean;
}) {
  return (
    <div
      className={`flex items-start gap-2 transition-opacity duration-300 ${fading ? "opacity-0" : "opacity-100"
        }`}
    >
      <Avatar />
      <div className="max-w-[80%] rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm">
        {children}
      </div>
    </div>
  );
}

function TypingDots() {
  return (
    <span className="flex items-center gap-1 py-1" aria-hidden="true">
      <span className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-blink [animation-delay:0ms]" />
      <span className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-blink [animation-delay:200ms]" />
      <span className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-blink [animation-delay:400ms]" />
    </span>
  );
}

export function ChatSimulation() {
  const reducedMotion = useReducedMotion();
  const rootRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  const [pairIndex, setPairIndex] = useState(0);
  const [showUser, setShowUser] = useState(false);
  const [showTyping, setShowTyping] = useState(false);
  const [typed, setTyped] = useState("");
  const [fading, setFading] = useState(false);

  // Pause the loop whenever the component is off-screen.
  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => setVisible(entry.isIntersecting),
      { threshold: 0.25 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (reducedMotion || !visible) return;

    let cancelled = false;
    const timeouts: number[] = [];
    const wait = (ms: number) =>
      new Promise<void>((resolve) => {
        const id = window.setTimeout(resolve, ms);
        timeouts.push(id);
      });

    async function run() {
      while (!cancelled) {
        for (let i = 0; i < PAIRS.length; i++) {
          if (cancelled) return;
          // Reset for the new pair.
          setPairIndex(i);
          setFading(false);
          setShowUser(false);
          setShowTyping(false);
          setTyped("");

          // 1. user bubble fades in
          await wait(20);
          if (cancelled) return;
          setShowUser(true);
          await wait(200);
          // 2. pause
          await wait(400);
          if (cancelled) return;
          // 3. typing indicator
          setShowTyping(true);
          // 4. "thinking"
          await wait(800);
          if (cancelled) return;
          // 5. typewriter response, 30ms/char
          setShowTyping(false);
          const text = PAIRS[i].assistant;
          for (let c = 0; c < text.length; c++) {
            if (cancelled) return;
            setTyped(text.slice(0, c + 1));
            await wait(30);
          }
          // 6. hold the complete response
          await wait(2500);
          if (cancelled) return;
          // 7. fade everything out
          setFading(true);
          await wait(300);
        }
        // pause before restarting the cycle
        if (cancelled) return;
        await wait(2000);
      }
    }

    run();
    return () => {
      cancelled = true;
      timeouts.forEach((id) => window.clearTimeout(id));
    };
  }, [reducedMotion, visible]);

  // Reduced motion: render the last pair statically, no animation.
  const staticMode = reducedMotion;
  const current = staticMode ? PAIRS[PAIRS.length - 1] : PAIRS[pairIndex];
  const assistantText = staticMode ? current.assistant : typed;
  const showAssistant = staticMode || showTyping || typed.length > 0;
  const showUserBubble = staticMode || showUser;

  return (
    <div
      ref={rootRef}
      role="group"
      aria-label="Demonstração ilustrativa do assistente"
      className="w-full overflow-hidden rounded-2xl border border-slate-200 bg-surface-subtle shadow-xl"
    >
      {/* Chat header */}
      <div className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3">
        <Avatar />
        <div className="leading-tight">
          <p className="text-sm font-semibold text-slate-900">
            Arcos Transparente
          </p>
          <p className="flex items-center gap-1.5 text-xs text-slate-500">
            <span className="h-2 w-2 rounded-full bg-green-500" aria-hidden="true" />
            online
          </p>
        </div>
      </div>

      {/* Messages — decorative animation; hidden from assistive tech to avoid
          flooding it with the per-character typewriter updates. */}
      <div
        aria-hidden="true"
        className="flex max-h-[320px] flex-col gap-3 overflow-y-auto p-4 md:max-h-none md:min-h-[360px]"
      >
        {showUserBubble && (
          <UserBubble text={current.user} fading={!staticMode && fading} />
        )}
        {showAssistant && (
          <AssistantBubble fading={!staticMode && fading}>
            {!staticMode && showTyping ? (
              <TypingDots />
            ) : (
              <span>{assistantText}</span>
            )}
          </AssistantBubble>
        )}
      </div>

      {/* Footer: disabled input */}
      <div className="border-t border-slate-200 bg-white px-4 py-3">
        <div className="flex items-center gap-2">
          <input
            type="text"
            disabled
            placeholder="Ex.: salários, contratos, receitas ou telefones úteis"
            aria-hidden="true"
            tabIndex={-1}
            className="flex-1 cursor-not-allowed rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-400 placeholder:text-slate-400"
          />
          <button
            type="button"
            disabled
            aria-hidden="true"
            tabIndex={-1}
            className="cursor-not-allowed rounded-lg bg-slate-200 px-4 py-2 text-sm font-medium text-slate-400"
          >
            Enviar
          </button>
        </div>
        <a
          href={URL_CHATBOT}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-primary hover:text-primary-hover"
        >
          Abrir o chat
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
          <span className="sr-only">(abre em nova aba)</span>
        </a>
      </div>
    </div>
  );
}
