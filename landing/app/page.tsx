import { About } from "@/components/About";
import { ExampleQuestions } from "@/components/ExampleQuestions";
import { FinalCTA } from "@/components/FinalCTA";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { Hero } from "@/components/Hero";
import { HowItWorks } from "@/components/HowItWorks";
import { MobileFloatingCTA } from "@/components/MobileFloatingCTA";
import { Problem } from "@/components/Problem";

export default function Home() {
  return (
    <>
      <Header />
      <main>
        <Hero />
        <Problem />
        <HowItWorks />
        <ExampleQuestions />
        <About />
        <FinalCTA />
      </main>
      <Footer />
      <MobileFloatingCTA />
    </>
  );
}
