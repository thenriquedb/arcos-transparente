"use client";

import { useEffect, useState } from "react";
import { ArrowRight } from "lucide-react";
import { URL_CHATBOT } from "@/lib/constants";

export function MobileFloatingCTA() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const hero = document.getElementById("top");
    const finalCta = document.getElementById("cta");

    let heroVisible = true;
    let ctaVisible = false;
    const sync = () => setShow(!heroVisible && !ctaVisible);

    const observers: IntersectionObserver[] = [];

    if (hero) {
      const o = new IntersectionObserver(
        ([entry]) => {
          heroVisible = entry.isIntersecting;
          sync();
        },
        { threshold: 0 },
      );
      o.observe(hero);
      observers.push(o);
    }
    if (finalCta) {
      const o = new IntersectionObserver(
        ([entry]) => {
          ctaVisible = entry.isIntersecting;
          sync();
        },
        { threshold: 0 },
      );
      o.observe(finalCta);
      observers.push(o);
    }

    return () => observers.forEach((o) => o.disconnect());
  }, []);

  return (
    <div
      className={`fixed inset-x-0 bottom-0 z-40 p-4 transition-all duration-300 md:hidden ${
        show
          ? "pointer-events-auto translate-y-0 opacity-100"
          : "pointer-events-none translate-y-4 opacity-0"
      }`}
    >
      <a
        href={URL_CHATBOT}
        target="_blank"
        rel="noopener noreferrer"
        className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3.5 text-base font-semibold text-primary-foreground shadow-lg transition-colors hover:bg-primary-hover"
      >
        Experimente
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
        <span className="sr-only">(abre em nova aba)</span>
      </a>
    </div>
  );
}
