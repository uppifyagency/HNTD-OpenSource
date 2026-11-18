"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "convex/react";
import {
  CheckoutProvider,
  useCheckout,
  usePaymentElement,
  PaymentElement,
  usePlans,
} from "@clerk/nextjs/experimental";
import { api } from "../../../convex/_generated/api";
import { Plan, Filing } from "@/components/editorial";

/**
 * EditorialPlans — custom Clerk Billing checkout in the editorial design system.
 * Marketing copy (EUR) stays on the cards; the real plan id comes from usePlans() (slug→id),
 * and the actual charge is handled by Clerk + Stripe via <PaymentElement /> (USD — Clerk
 * Billing is USD-only). Downgrade/cancel is intentionally out of scope (separate flow).
 */
type PlanCard = {
  slug: string;
  name: string;
  eyebrow?: string;
  pill?: string;
  price: string;
  suffix: string;
  features: string[];
  featured?: boolean;
};

const MARKETING: PlanCard[] = [
  {
    slug: "free_user",
    name: "Free",
    eyebrow: "esplora",
    price: "€0",
    suffix: "/per sempre",
    features: ["1 ricerca / mese", "scoring limitato", "export CSV"],
  },
  {
    slug: "pro",
    name: "Pro",
    pill: "consigliato",
    price: "€390",
    suffix: "/mese",
    features: ["50 ricerche / mese", "matching AI da JD", "pipeline kanban", "export PDF + CSV"],
    featured: true,
  },
  {
    slug: "business",
    name: "Business",
    eyebrow: "scala",
    price: "€590",
    suffix: "/mese",
    features: ["ricerche illimitate", "posti team", "API access", "onboarding dedicato"],
  },
];

export function EditorialPlans() {
  const me = useQuery(api.users.getCurrentUser);
  const { data: clerkPlans } = usePlans({ for: "user" });
  const [selected, setSelected] = useState<{ planId: string; name: string } | null>(null);

  const currentPlan = me?.plan ?? "free";
  const planIdBySlug: Record<string, string> = {};
  for (const p of clerkPlans ?? []) planIdBySlug[p.slug] = p.id;

  return (
    <>
      <div className="cols-3" style={{ gap: 16, marginTop: 16 }}>
        {MARKETING.map((p) => {
          const isCurrent = p.slug === currentPlan || (p.slug === "free_user" && currentPlan === "free");
          const planId = planIdBySlug[p.slug];
          const variant = p.featured ? ("accent" as const) : ("primary" as const);

          let cta: { label: string; onClick?: () => void; disabled?: boolean; variant?: "ghost" | "primary" | "accent" };
          if (isCurrent) {
            cta = { label: "[ piano attuale ]", variant: "ghost", disabled: true };
          } else if (p.slug === "free_user") {
            cta = { label: "[ piano base ]", variant: "ghost", disabled: true };
          } else if (planId) {
            cta = { label: `[ passa a ${p.name} → ]`, variant, onClick: () => setSelected({ planId, name: p.name }) };
          } else {
            // usePlans not loaded yet, or slug missing in Clerk Dashboard. Keep the plan's
            // own variant (not ghost) so the label stays visible on the dark featured card.
            cta = { label: "[ caricamento… ]", variant, disabled: true };
          }

          return (
            <Plan
              key={p.slug}
              name={p.name}
              eyebrow={p.eyebrow}
              pill={p.pill}
              price={p.price}
              suffix={p.suffix}
              features={p.features}
              featured={p.featured ?? false}
              cta={cta}
            />
          );
        })}
      </div>

      {selected && (
        <div style={{ marginTop: 24, maxWidth: 560 }}>
          <CheckoutProvider for="user" planId={selected.planId} planPeriod="month">
            <CheckoutInner planName={selected.name} onClose={() => setSelected(null)} />
          </CheckoutProvider>
        </div>
      )}
    </>
  );
}

function CheckoutInner({ planName, onClose }: { planName: string; onClose: () => void }) {
  const { checkout } = useCheckout();
  const starting = checkout.fetchStatus === "fetching";

  if (checkout.status === "needs_initialization") {
    return (
      <Filing tab={`checkout · ${planName}`} corner="⊕ clerk billing">
        <div style={{ display: "grid", gap: 16, padding: 24 }}>
          <p className="mono dim" style={{ fontSize: 13 }}>
            stai per passare al piano <strong>{planName}</strong>. il pagamento è gestito in modo sicuro da Clerk + Stripe.
          </p>
          <button
            type="button"
            className="btn btn--accent"
            disabled={starting}
            onClick={() => checkout.start().catch(() => {})}
          >
            {starting ? "[ avvio… ]" : "[ procedi al pagamento → ]"}
          </button>
          <button type="button" className="btn btn--ghost btn--sm" onClick={onClose}>
            [ annulla ]
          </button>
        </div>
      </Filing>
    );
  }

  return <PayPanel planName={planName} onClose={onClose} />;
}

function PayPanel({ planName, onClose }: { planName: string; onClose: () => void }) {
  const { checkout } = useCheckout();
  const { submit, isFormReady } = usePaymentElement();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const pay = async (e: FormEvent) => {
    e.preventDefault();
    if (!isFormReady || submitting) return;
    setError(null);
    setSubmitting(true);
    try {
      // 1. Tokenize the card via Stripe; validation errors surface inside <PaymentElement />.
      const { data, error: submitError } = await submit();
      if (submitError) {
        setSubmitting(false);
        return;
      }
      // 2. Confirm the checkout with the payment token.
      const { error: confirmError } = await checkout.confirm(data);
      if (confirmError) {
        setError(typeof confirmError === "string" ? confirmError : "pagamento non riuscito");
        setSubmitting(false);
        return;
      }
      // 3. Finalize: syncs client/server auth state, then refresh so the new plan shows.
      await checkout.finalize({ navigate: () => router.refresh() });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "errore inatteso");
      setSubmitting(false);
    }
  };

  return (
    <Filing tab={`checkout · ${planName}`} corner="⊕ clerk billing">
      <form onSubmit={pay} style={{ display: "grid", gap: 16, padding: 24 }}>
        <p className="mono dim" style={{ fontSize: 12, margin: 0 }}>
          piano {planName} · <span className="dim">addebito mensile in USD (Clerk Billing)</span>
        </p>
        <PaymentElement />
        {error ? (
          <p className="mono" style={{ fontSize: 12, color: "#c0392b" }}>
            {error}
          </p>
        ) : null}
        <button type="submit" className="btn btn--accent" disabled={!isFormReady || submitting}>
          {submitting ? "[ pagamento… ]" : "[ conferma e paga → ]"}
        </button>
        <button type="button" className="btn btn--ghost btn--sm" onClick={onClose}>
          [ annulla ]
        </button>
      </form>
    </Filing>
  );
}
