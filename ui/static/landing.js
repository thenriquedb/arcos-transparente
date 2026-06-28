// Comportamentos da landing do Arcos Transparente (vanilla JS, sem build).
// Portado de landing/components/ChatSimulation.tsx, MobileFloatingCTA.tsx e
// dos botoes "Copiar" de ExampleQuestions.tsx.

(function () {
  "use strict";

  const prefersReducedMotion = () =>
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // --- Simulacao de chat (decorativa) --------------------------------------
  // Conteudo meramente ilustrativo (rotulado "Exemplo ilustrativo" na UI). Evita
  // numeros atribuidos a pessoas identificaveis; usa agregados e linguagem
  // condicional para nao sugerir precisao garantida.
  const PAIRS = [
    {
      user: "Quanto a prefeitura gastou com saúde em 2025?",
      assistant:
        "Exemplo: somando as despesas da função Saúde no período, mostro o total e indico o período e a fonte para você conferir.",
    },
    {
      user: "Quais foram os maiores contratos do ano?",
      assistant:
        "Exemplo: listo os maiores contratos por valor, com fornecedor, objeto e data, e aponto onde conferir no portal oficial.",
    },
    {
      user: "Quanto foi gasto com diárias em 2025?",
      assistant:
        "Exemplo: somo as diárias registradas e mostro o total por período ou por órgão, conforme a base disponível.",
    },
  ];

  function initChatSimulation() {
    const root = document.getElementById("chat-sim");
    if (!root) return;

    const userWrap = document.getElementById("chat-sim-user");
    const userText = document.getElementById("chat-sim-user-text");
    const assistantWrap = document.getElementById("chat-sim-assistant");
    const typingDots = document.getElementById("chat-sim-typing");
    const typedText = document.getElementById("chat-sim-text");

    const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    const setOpacity = (el, on) => {
      el.classList.toggle("opacity-100", on);
      el.classList.toggle("opacity-0", !on);
    };

    // Movimento reduzido: mostra o ultimo par estatico, sem animacao.
    if (prefersReducedMotion()) {
      const last = PAIRS[PAIRS.length - 1];
      userText.textContent = last.user;
      typedText.textContent = last.assistant;
      typingDots.classList.add("hidden");
      userWrap.classList.remove("hidden");
      assistantWrap.classList.remove("hidden");
      setOpacity(userWrap, true);
      setOpacity(assistantWrap, true);
      return;
    }

    let visible = false;
    let running = false;

    const observer = new IntersectionObserver(
      ([entry]) => {
        visible = entry.isIntersecting;
        if (visible && !running) run();
      },
      { threshold: 0.25 },
    );
    observer.observe(root);

    async function run() {
      running = true;
      while (visible) {
        for (let i = 0; i < PAIRS.length && visible; i++) {
          const pair = PAIRS[i];

          // reset
          setOpacity(userWrap, false);
          setOpacity(assistantWrap, false);
          userWrap.classList.add("hidden");
          assistantWrap.classList.add("hidden");
          typedText.textContent = "";
          userText.textContent = pair.user;

          // 1. bolha do usuario
          await wait(20);
          if (!visible) break;
          userWrap.classList.remove("hidden");
          setOpacity(userWrap, true);
          await wait(600);

          // 2. indicador de digitacao
          if (!visible) break;
          assistantWrap.classList.remove("hidden");
          setOpacity(assistantWrap, true);
          typingDots.classList.remove("hidden");
          typedText.textContent = "";
          await wait(800);

          // 3. resposta com efeito de digitacao (30ms/char)
          if (!visible) break;
          typingDots.classList.add("hidden");
          const text = pair.assistant;
          for (let c = 0; c < text.length && visible; c++) {
            typedText.textContent = text.slice(0, c + 1);
            await wait(30);
          }

          // 4. segura a resposta completa
          await wait(2500);
          if (!visible) break;

          // 5. fade out
          setOpacity(userWrap, false);
          setOpacity(assistantWrap, false);
          await wait(300);
        }
        if (!visible) break;
        await wait(2000);
      }
      running = false;
    }
  }

  // --- CTA flutuante no mobile ----------------------------------------------
  function initMobileCta() {
    const bar = document.getElementById("mobile-cta");
    if (!bar) return;
    const hero = document.getElementById("top");
    const finalCta = document.getElementById("cta");

    let heroVisible = true;
    let ctaVisible = false;
    const sync = () => {
      const show = !heroVisible && !ctaVisible;
      bar.classList.toggle("pointer-events-auto", show);
      bar.classList.toggle("translate-y-0", show);
      bar.classList.toggle("opacity-100", show);
      bar.classList.toggle("pointer-events-none", !show);
      bar.classList.toggle("translate-y-4", !show);
      bar.classList.toggle("opacity-0", !show);
    };

    if (hero) {
      new IntersectionObserver(
        ([e]) => {
          heroVisible = e.isIntersecting;
          sync();
        },
        { threshold: 0 },
      ).observe(hero);
    }
    if (finalCta) {
      new IntersectionObserver(
        ([e]) => {
          ctaVisible = e.isIntersecting;
          sync();
        },
        { threshold: 0 },
      ).observe(finalCta);
    }
    sync();
  }

  // --- Botoes "Copiar" das perguntas de exemplo -----------------------------
  function initCopyButtons() {
    document.querySelectorAll("[data-copy-question]").forEach((btn) => {
      const label = btn.querySelector("[data-copy-label]");
      btn.addEventListener("click", async () => {
        const text = btn.getAttribute("data-copy-question") || "";
        try {
          await navigator.clipboard.writeText(text);
        } catch (_) {
          /* clipboard indisponivel — ignora */
        }
        if (!label) return;
        const original = label.textContent;
        label.textContent = "Copiado!";
        label.classList.add("opacity-100");
        setTimeout(() => {
          label.textContent = original;
          label.classList.remove("opacity-100");
        }, 1500);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    // Renderiza os icones Lucide (script self-hosted carregado com defer).
    if (window.lucide) window.lucide.createIcons();
    initChatSimulation();
    initMobileCta();
    initCopyButtons();
  });
})();
