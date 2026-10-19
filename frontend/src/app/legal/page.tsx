import type { Metadata } from "next";
import Link from "next/link";
import { Heart } from "lucide-react";

export const metadata: Metadata = {
  title: "Terms, privacy & medical disclaimer — NutriMed AI",
  description: "How NutriMed AI may be used, how your health data is handled, and the limits of its advice.",
};

const LAST_UPDATED = "October 19, 2026";

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-20">
      <h2 className="text-xl font-semibold text-slate-100">{title}</h2>
      <div className="mt-3 space-y-3 text-sm leading-relaxed text-slate-300">{children}</div>
    </section>
  );
}

export default function LegalPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <header className="border-b border-slate-800/80">
        <div className="mx-auto flex h-16 max-w-3xl items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2">
            <Heart className="h-6 w-6 text-blue-600" />
            <span className="text-lg font-bold">NutriMed AI</span>
          </Link>
          <Link href="/login" className="text-sm text-slate-400 hover:text-slate-200">
            Sign in
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
        <h1 className="text-3xl font-bold">Terms, privacy &amp; medical disclaimer</h1>
        <p className="mt-2 text-sm text-slate-500">Last updated {LAST_UPDATED}</p>

        <nav className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-sm">
          <a href="#disclaimer" className="text-blue-400 hover:text-blue-300">Medical disclaimer</a>
          <a href="#terms" className="text-blue-400 hover:text-blue-300">Terms of use</a>
          <a href="#privacy" className="text-blue-400 hover:text-blue-300">Privacy</a>
        </nav>

        <div className="mt-10 space-y-10">
          <Section id="disclaimer" title="Medical disclaimer">
            <p>
              NutriMed AI provides general wellness and nutrition information. It is not a medical device and
              does not provide medical advice, diagnosis or treatment. Analyses, suggestions and plans are
              generated automatically from the data you provide and may be incomplete or wrong.
            </p>
            <p>
              Always talk to a qualified doctor or registered dietitian before changing your diet, exercise,
              supplements or medication, and about any result that concerns you. This matters especially if you
              have a medical condition, are pregnant or breastfeeding, are under 18, or take prescription drugs.
              Never ignore professional advice or delay seeking it because of something you read here.
            </p>
            <p className="font-medium text-amber-300">
              If you think you may have a medical emergency, call your local emergency number immediately.
            </p>
          </Section>

          <Section id="terms" title="Terms of use">
            <p>By creating an account you agree to these terms. You must be at least 18 years old.</p>
            <ul className="list-disc space-y-1.5 pl-5">
              <li>Only upload reports that belong to you, or that you are authorised to share.</li>
              <li>Keep your password private. You are responsible for activity under your account.</li>
              <li>Do not misuse the service, attempt to access other people&apos;s data, or overload it.</li>
              <li>
                The service is provided &quot;as is&quot;, without warranties. To the extent the law allows, we are
                not liable for decisions you make based on its output.
              </li>
              <li>We may update these terms. Material changes will be shown in the app before they apply.</li>
            </ul>
          </Section>

          <Section id="privacy" title="Privacy">
            <p className="font-medium text-slate-200">What we store</p>
            <ul className="list-disc space-y-1.5 pl-5">
              <li>Account details: name, email and a securely hashed password.</li>
              <li>Profile and medical profile: age, sex, height, weight, goals, allergies, conditions, medications.</li>
              <li>Uploaded lab reports and the values, analyses and plans produced from them.</li>
              <li>Progress entries you log, and a security log of account activity.</li>
            </ul>
            <p className="font-medium text-slate-200">How it is handled</p>
            <ul className="list-disc space-y-1.5 pl-5">
              <li>Uploaded report files are encrypted at rest.</li>
              <li>
                Results are analysed by AI models, which may be run by a third-party AI provider acting on our
                behalf. Only de-identified health information is sent to it, such as lab values, age, sex, body
                measurements, activity level, goals, diet preference, and the conditions, medications, allergies
                and injuries you entered. Your name, contact details and the report file itself are never sent.
              </li>
              <li>Your data is never sold or used for advertising.</li>
              <li>
                Administrators can see account details (name, email, role, number of reports) to run the service,
                but not the contents of your reports.
              </li>
            </ul>
            <p className="font-medium text-slate-200">Your choices</p>
            <ul className="list-disc space-y-1.5 pl-5">
              <li>Delete any report, with everything generated from it, from the report page.</li>
              <li>
                Delete your account and all of its health data at any time from{" "}
                <Link href="/settings" className="text-blue-400 hover:text-blue-300">Settings</Link>. This cannot be
                undone. Security logs are kept for a limited period to protect the service.
              </li>
            </ul>
          </Section>
        </div>
      </main>
    </div>
  );
}
