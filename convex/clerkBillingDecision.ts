// Pure decision logic for Clerk Billing subscriptionItem.* webhooks.
// No Convex imports: the module is unit-testable outside the Convex runtime.

export type PlanId = "free" | "pro" | "business";

export type SubscriptionStatus = "active" | "canceled" | "past_due" | "trialing";

// Clerk plan slugs are the same strings we store in users.plan.
export function planFromSlug(slug?: string | null): PlanId {
  if (slug === "pro") return "pro";
  if (slug === "business") return "business";
  return "free";
}

// Clerk plan slugs are the same strings we store in users.plan — but `payer.id` is NOT a
// Clerk user id (it identifies the payer record / organization), and users.clerkId is a
// user id, so an `id` fallback is only safe when it is unambiguously one.
export function clerkUserIdFromPayer(payer: unknown): string | undefined {
  const p = payer as { user_id?: unknown; id?: unknown } | null | undefined;
  if (typeof p?.user_id === "string" && p.user_id !== "") return p.user_id;
  if (typeof p?.id === "string" && p.id.startsWith("user_")) return p.id;
  return undefined;
}

type Intent = "active" | "trialing" | "past_due" | "canceled" | "ended" | "none";

// Where the intent came from:
//  - "type"   the event NAME is a documented Clerk transition, so it is evidence about
//             this item's lifecycle.
//  - "status" the event name is not a documented transition (e.g. subscriptionItem.updated,
//             which Clerk fires when a property changed WITHOUT a status change — every
//             renewal moves period_start/period_end), so the payload status is the only
//             hint available. It is NOT evidence that this item is the current one.
type IntentSource = "type" | "status";

function intentOf(
  eventType: string,
  eventStatus?: string
): { intent: Intent; source: IntentSource } {
  switch (eventType) {
    case "subscriptionItem.active":
      // Clerk marks a free-trial item active too; only the payload status tells them apart.
      return { intent: eventStatus === "trialing" ? "trialing" : "active", source: "type" };
    case "subscriptionItem.canceled":
      return { intent: "canceled", source: "type" };
    case "subscriptionItem.ended":
      return { intent: "ended", source: "type" };
    // Clerk emits camelCase; the snake_case spelling is tolerated defensively.
    case "subscriptionItem.pastDue":
    case "subscriptionItem.past_due":
      return { intent: "past_due", source: "type" };
    case "subscriptionItem.freeTrialEnding":
    case "subscriptionItem.upcoming":
      return { intent: "none", source: "type" };
  }
  // Unrecognised types (subscriptionItem.updated on renewal, .abandoned, .incomplete)
  // are classified from the item status carried by the payload — status-only, see below.
  switch (eventStatus) {
    case "active":
      return { intent: "active", source: "status" };
    case "trialing":
      return { intent: "trialing", source: "status" };
    case "past_due":
      return { intent: "past_due", source: "status" };
    case "canceled":
      return { intent: "canceled", source: "status" };
    case "ended":
      return { intent: "ended", source: "status" };
    default:
      return { intent: "none", source: "status" };
  }
}

export type ClerkBillingDecision =
  | { action: "apply"; plan: PlanId; subscriptionStatus: SubscriptionStatus }
  | { action: "ignore"; reason: string };

export function decideClerkBillingUpdate(input: {
  eventType: string;
  eventStatus?: string;
  slug?: string | null;
  currentPlan: PlanId;
  currentSubscriptionStatus?: SubscriptionStatus;
}): ClerkBillingDecision {
  const eventPlan = planFromSlug(input.slug);
  // The default free_user item is always "active" in Clerk's model and would
  // otherwise clobber a paid plan depending on event ordering.
  if (eventPlan === "free") return { action: "ignore", reason: "unmapped_or_free_slug" };

  const { intent, source } = intentOf(input.eventType, input.eventStatus);
  if (intent === "none") return { action: "ignore", reason: "no_actionable_status" };

  // An intent inferred from the payload status may only REFRESH the status of the plan
  // the user already holds (self-heal after a missed event). It must never write `plan`:
  // a status of "active" on a subscriptionItem.updated is not evidence that this item is
  // the current one, and Svix delivers the two items of a plan switch in any order — so
  // trusting it would silently flip a paying business customer to pro and back.
  if (source === "status") {
    if (eventPlan !== input.currentPlan) {
      return { action: "ignore", reason: "stale_item_plan_mismatch" };
    }
    if (intent === "ended") {
      // A plan revocation is only ever taken from a documented `subscriptionItem.ended`.
      return { action: "ignore", reason: "plan_change_needs_typed_event" };
    }
    if (
      (intent === "active" || intent === "trialing") &&
      input.currentSubscriptionStatus === "canceled"
    ) {
      // Clerk keeps the ITEM active through the grace period after a cancel, so every
      // renewal-shaped `updated` in that window would otherwise erase the churn marker.
      return { action: "ignore", reason: "would_resurrect_canceled_status" };
    }
    return { action: "apply", plan: input.currentPlan, subscriptionStatus: intent };
  }

  // ITEM-AWARENESS, applied once for every transition that is NOT an activation.
  // Only an activation legitimately CHANGES which plan the user holds. `past_due`,
  // `canceled` and `ended` are lifecycle transitions OF an item, so an event whose slug is
  // not the plan currently stored is the stale old item of a switch — Svix delivers the two
  // items of a switch in either order, and dunning on an old item can even arrive after the
  // new item's activation in genuine time order. Applying the event's slug there would
  // downgrade (or over-grant) a paying customer, because gating reads users.plan.
  // Keeping this as ONE guard rather than one per branch is deliberate: the per-branch
  // version already let `past_due` through (see OPEN-ISSUES BILL-01).
  if (intent !== "active" && intent !== "trialing" && eventPlan !== input.currentPlan) {
    return { action: "ignore", reason: "stale_item_plan_mismatch" };
  }

  switch (intent) {
    case "active":
    case "trialing":
      return { action: "apply", plan: eventPlan, subscriptionStatus: intent };
    case "past_due":
    case "canceled":
      // Neither transition may ever MOVE the plan: dunning is a status change on an item,
      // and Clerk keeps plan features until the end of the billing period on cancel.
      // Written as `input.currentPlan` — identical to `eventPlan` once the guard above has
      // run — so that weakening the guard can at worst mislabel a status, never revoke or
      // grant a plan. Billing code: the second encoding is worth two lines.
      return { action: "apply", plan: input.currentPlan, subscriptionStatus: intent };
    case "ended":
      // KNOWN RESIDUAL: slug equality cannot distinguish two items of the SAME plan
      // (cancel-then-resubscribe on pro yields an old and a new pro item), so an `ended`
      // for the old one delivered after the new one's `active` still revokes a paying
      // customer. The durable fix needs a monotonic per-item marker (subscription item id
      // or period_start) stored on the user — a schema change, deferred: see OPEN-ISSUES
      // BILL-01.
      return { action: "apply", plan: "free", subscriptionStatus: "canceled" };
  }
}

export type ClerkBillingApplyResult =
  | {
      ok: true;
      applied: boolean;
      reason?: string;
      plan?: PlanId;
      subscriptionStatus?: SubscriptionStatus;
      /** True when the plan changed and the search allowance window was re-anchored. */
      allowanceReset?: boolean;
    }
  | { ok: false; reason: "user_not_found" };
