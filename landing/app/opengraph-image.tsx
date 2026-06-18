import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt =
  "Arcos Transparente — transparência pública que qualquer pessoa consegue usar.";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          backgroundColor: "#ffffff",
          padding: "80px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            fontSize: 34,
            fontWeight: 700,
            color: "#1d4ed8",
          }}
        >
          Arcos Transparente
        </div>
        <div
          style={{
            display: "flex",
            fontSize: 64,
            fontWeight: 800,
            lineHeight: 1.1,
            color: "#0f172a",
            maxWidth: 900,
          }}
        >
          Transparência pública que qualquer pessoa consegue usar.
        </div>
        <div
          style={{
            display: "flex",
            fontSize: 30,
            color: "#475569",
            maxWidth: 980,
          }}
        >
          Pergunte, em português, sobre as contas públicas de Arcos (MG).
        </div>
      </div>
    ),
    { ...size },
  );
}
