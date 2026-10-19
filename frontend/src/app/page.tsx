import type { Metadata } from "next";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  Dumbbell,
  FileText,
  Heart,
  LineChart,
  Lock,
  ShieldAlert,
  Sparkles,
  Upload,
  UtensilsCrossed,
} from "lucide-react";
import { DISCLAIMER_TEXT } from "@/components/medical-disclaimer";

export const metadata: Metadata = {
  title: "NutriMed AI — Turn your lab report into a health plan",
  description:
    "Upload a blood test. NutriMed AI reads your biomarkers, explains what is out of range, and builds a diet and workout plan around your results.",
};

const primaryCta =
  "inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700";
const secondaryCta =
  "inline-flex items-center justify-center gap-2 rounded-lg border border-slate-700 px-5 py-2.5 text-sm font-medium text-slate-200 transition-colors hover:bg-slate-800";

const steps = [
  {
    icon: Upload,
    title: "Upload your report",
    body: "Add a lab report such as a CBC, lipid, thyroid or vitamin panel. It is encrypted as soon as it arrives.",
  },
  {
    icon: Activity,
    title: "See what it means",
    body: "Your biomarkers are read, checked against reference ranges and explained in plain language.",
  },
  {
    icon: Sparkles,
    title: "Follow your plan",
    body: "Get food and training guidance built around your results and goal, then track how you progress.",
  },
];

const features = [
  {
    icon: FileText,
    title: "Biomarker analysis",
    body: "Out-of-range values, likely deficiencies and risk factors, highlighted and explained.",
  },
  {
    icon: UtensilsCrossed,
    title: "Personalised diet plans",
    body: "Day-by-day meals with calories and macros matched to your targets and restrictions.",
  },
  {
    icon: Dumbbell,
    title: "Workouts that fit your health",
    body: "Training plans that take your goal, level and lab findings into account.",
  },
  {
    icon: LineChart,
    title: "Progress tracking",
    body: "Log weight and measurements and watch the trend over time.",
  },
  {
    icon: FileText,
    title: "Downloadable PDF report",
    body: "One document with your results, plan and supplements to keep or share with your doctor.",
  },
  {
    icon: Lock,
    title: "Private by design",
    body: "Reports are encrypted at rest, and you can delete a report or your whole account at any time.",
  },
];

/** Static preview of the analysis screen, illustrative values only. */
const previewRows = [
  { name: "Hemoglobin", value: "11.2 g/dL", range: "13.0–17.0", status: "Low", tone: "text-amber-400 bg-amber-500/10" },
  { name: "Vitamin D", value: "18 ng/mL", range: "30–100", status: "Low", tone: "text-amber-400 bg-amber-500/10" },
  { name: "LDL cholesterol", value: "142 mg/dL", range: "< 100", status: "High", tone: "text-red-400 bg-red-500/10" },
  { name: "Fasting glucose", value: "92 mg/dL", range: "70–99", status: "Normal", tone: "text-emerald-400 bg-emerald-500/10" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <header className="border-b border-slate-800/80">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2">
            <Heart className="h-6 w-6 text-blue-600" />
            <span className="text-lg font-bold">NutriMed AI</span>
          </Link>
          <nav className="flex items-center gap-2">
            <Link href="/login" className="rounded-lg px-3 py-2 text-sm font-medium text-slate-300 hover:text-slate-100">
              Sign in
            </Link>
            <Link href="/register" className={primaryCta}>
              Get started
            </Link>
          </nav>
        </div>
      </header>

      <main>
        <section className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 sm:px-6 lg:grid-cols-2 lg:py-24">
          <div>
            <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-blue-500/20 bg-blue-500/10 px-3 py-1 text-xs font-medium text-blue-300">
              <Sparkles className="h-3.5 w-3.5" />
              Lab results, explained and acted on
            </p>
            <h1 className="text-4xl font-bold tracking-tight text-balance sm:text-5xl">
              Turn your lab report into a plan you can follow.
            </h1>
            <p className="mt-5 max-w-xl text-lg text-slate-400">
              Upload a blood test. NutriMed AI reads your biomarkers, explains what is out of range, and builds a
              diet and workout plan around your results.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link href="/register" className={primaryCta}>
                Create your free account
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="/login" className={secondaryCta}>
                I already have an account
              </Link>
            </div>
            <p className="mt-6 flex items-center gap-2 text-sm text-slate-500">
              <Lock className="h-4 w-4" />
              Encrypted storage · Delete your data any time
            </p>
          </div>

          <div aria-hidden className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-2xl shadow-blue-950/40">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-200">Complete Blood Count</p>
                <p className="text-xs text-slate-500">Analysed just now</p>
              </div>
              <span className="rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-400">
                Ready
              </span>
            </div>
            <div className="divide-y divide-slate-800 rounded-lg border border-slate-800">
              {previewRows.map((row) => (
                <div key={row.name} className="flex items-center justify-between gap-3 px-3 py-2.5 text-sm">
                  <div className="min-w-0">
                    <p className="truncate text-slate-200">{row.name}</p>
                    <p className="text-xs text-slate-500">Range {row.range}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-medium text-slate-100 tabular-nums">{row.value}</span>
                    <span className={`w-16 rounded-full px-2 py-0.5 text-center text-xs font-medium ${row.tone}`}>
                      {row.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 rounded-lg bg-blue-600/10 p-3 text-sm text-blue-200">
              <p className="font-medium">Suggested focus</p>
              <p className="mt-1 text-blue-200/80">
                Iron-rich foods with vitamin C, daily sunlight or a vitamin D check-in with your doctor, and more
                soluble fibre to help with LDL.
              </p>
            </div>
          </div>
        </section>

        <section className="border-t border-slate-800/80 bg-slate-900/30">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
            <h2 className="text-2xl font-bold sm:text-3xl">How it works</h2>
            <div className="mt-8 grid gap-6 md:grid-cols-3">
              {steps.map((step, i) => (
                <div key={step.title} className="rounded-xl border border-slate-800 bg-slate-900 p-6">
                  <div className="flex items-center gap-3">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-sm font-semibold">
                      {i + 1}
                    </span>
                    <step.icon className="h-5 w-5 text-blue-400" />
                  </div>
                  <h3 className="mt-4 font-semibold text-slate-100">{step.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-400">{step.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <h2 className="text-2xl font-bold sm:text-3xl">Everything in one place</h2>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <div key={feature.title} className="rounded-xl border border-slate-800 p-5">
                <feature.icon className="h-5 w-5 text-blue-400" />
                <h3 className="mt-3 font-semibold text-slate-100">{feature.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-slate-400">{feature.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
          <div className="flex gap-3 rounded-xl border border-amber-500/20 bg-amber-500/5 p-5 text-sm text-slate-300">
            <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
            <p>
              <span className="font-semibold text-amber-300">Important: </span>
              {DISCLAIMER_TEXT}
            </p>
          </div>

          <div className="mt-12 rounded-2xl bg-blue-600 px-6 py-10 text-center">
            <h2 className="text-2xl font-bold">Ready to understand your results?</h2>
            <p className="mx-auto mt-2 max-w-lg text-blue-100">
              Create an account, upload your latest report and get your plan in minutes.
            </p>
            <Link
              href="/register"
              className="mt-6 inline-flex items-center gap-2 rounded-lg bg-white px-5 py-2.5 text-sm font-semibold text-blue-700 hover:bg-blue-50"
            >
              Get started free
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-800/80">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-6 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <p>© {new Date().getFullYear()} NutriMed AI</p>
          <div className="flex gap-5">
            <Link href="/legal" className="hover:text-slate-300">
              Terms &amp; privacy
            </Link>
            <Link href="/login" className="hover:text-slate-300">
              Sign in
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
