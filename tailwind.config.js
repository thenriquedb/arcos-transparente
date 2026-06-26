/** Config do build estático do Tailwind (binário standalone, sem Node).
 * Gera ui/static/tailwind.css; escaneia templates e o JS da landing (classes
 * alternadas em runtime, ex.: translate-y-0/opacity-0/pointer-events-auto). */
module.exports = {
  content: ["./ui/templates/**/*.html", "./ui/static/**/*.js"],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "rgb(var(--color-primary) / <alpha-value>)",
          hover: "rgb(var(--color-primary-hover) / <alpha-value>)",
          foreground: "rgb(var(--color-primary-foreground) / <alpha-value>)",
        },
        surface: {
          DEFAULT: "rgb(var(--color-surface) / <alpha-value>)",
          subtle: "rgb(var(--color-surface-subtle) / <alpha-value>)",
        },
      },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] },
      keyframes: { blink: { "0%,100%": { opacity: "0.2" }, "50%": { opacity: "1" } } },
      animation: { blink: "blink 1.2s ease-in-out infinite" },
    },
  },
};
