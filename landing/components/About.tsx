import { Github, Linkedin, Mail, User } from "lucide-react";
import {
  CREATOR_EMAIL,
  CREATOR_LINKEDIN,
  CREATOR_NAME,
  CREATOR_ROLE,
  LINK_GITHUB,
} from "@/lib/constants";

export function About() {
  const hasCreatorName = !CREATOR_NAME.startsWith("__");
  const hasCreatorRole = !CREATOR_ROLE.startsWith("__");
  const hasLinkedIn = CREATOR_LINKEDIN !== "#";

  return (
    <section id="sobre" className="bg-slate-50 py-24">
      <div className="mx-auto grid max-w-4xl items-center gap-10 px-5 sm:px-8 sm:grid-cols-[auto_1fr]">
        <div className="flex h-32 w-32 items-center justify-center rounded-2xl bg-white ring-4 ring-primary/20">
          <User className="h-14 w-14 text-primary" aria-hidden="true" />
        </div>
        <div>
          <p className="text-sm font-bold uppercase tracking-widest text-primary">
            Sobre o projeto
          </p>
          <h2 className="mt-3 text-3xl font-black tracking-tight text-slate-900">
            {hasCreatorName ? "Quem fez" : "Um projeto independente"}
          </h2>
          <p className="mt-4 text-lg leading-relaxed text-slate-600">
            {hasCreatorName ? (
              <>
                Sou <strong className="text-slate-900">{CREATOR_NAME}</strong>
                {hasCreatorRole ? (
                  <>
                    , <strong className="text-slate-900">{CREATOR_ROLE}</strong>
                  </>
                ) : null}
                . Construí o{" "}
                <strong className="font-semibold text-slate-900">
                  Arcos Transparente
                </strong>{" "}
                para provar, na prática, que dados públicos podem ser fáceis de
                consultar — e para colocar isso nas mãos de quem mora aqui.
                <br />
                <br />
                Este projeto não tem viés político. Não foi criado para atacar
                nem para defender ninguém. A ideia é simplesmente facilitar o
                acesso público às informações da cidade.
              </>
            ) : (
              <>
                O{" "}
                <strong className="font-semibold text-slate-900">
                  Arcos Transparente
                </strong>{" "}
                é uma ferramenta independente que utiliza dados públicos
                disponíveis em fontes oficiais, como o Portal da Transparência,
                para facilitar a consulta e compreensão das informações
                municipais. O projeto não substitui os canais oficiais. As
                respostas procuram indicar a fonte dos dados utilizados e deixar
                claro quando a informação não está disponível ou é limitada.
                <br />
                <br />
                Este projeto não tem viés político. Não foi criado para atacar
                nem para defender ninguém. A ideia é simplesmente facilitar o
                acesso público às informações da cidade.
              </>
            )}
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-5 text-sm font-semibold">
            <a
              href={LINK_GITHUB}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-slate-700 hover:text-primary"
            >
              <Github className="h-4 w-4" aria-hidden="true" /> GitHub
            </a>
            {hasLinkedIn ? (
              <a
                href={CREATOR_LINKEDIN}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-slate-700 hover:text-primary"
              >
                <Linkedin className="h-4 w-4" aria-hidden="true" /> LinkedIn
              </a>
            ) : null}
            <a
              href={`mailto:${CREATOR_EMAIL}`}
              className="inline-flex items-center gap-1.5 text-slate-700 hover:text-primary"
            >
              <Mail className="h-4 w-4" aria-hidden="true" /> E-mail
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
