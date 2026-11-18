import { describe, it, expect } from "vitest";
import {
  clerkUserIdFromPayer,
  decideClerkBillingUpdate,
} from "../../../convex/clerkBillingDecision";

/**
 * The module under test lives in convex/ (so Convex bundles it), but the test lives
 * here because vitest.config.ts only includes src/**\/*.test.ts. The module is pure —
 * no Convex imports — so it loads in the default vitest environment.
 */

describe("decideClerkBillingUpdate — termination is item-aware", () => {
  it("ignores an `ended` event for a plan the user no longer holds (cross-item race)", () => {
    expect(
      decideClerkBillingUpdate({
        eventType: "subscriptionItem.ended",
        slug: "pro",
        currentPlan: "business",
      })
    ).toEqual({ action: "ignore", reason: "stale_item_plan_mismatch" });
  });

  it("downgrades when the terminating item is the plan the user holds", () => {
    expect(
      decideClerkBillingUpdate({
        eventType: "subscriptionItem.ended",
        slug: "business",
        currentPlan: "business",
      })
    ).toEqual({ action: "apply", plan: "free", subscriptionStatus: "canceled" });
  });
});

describe("decideClerkBillingUpdate — canceled keeps the paid plan", () => {
  it("keeps the plan and only changes the status", () => {
    const decision = decideClerkBillingUpdate({
      eventType: "subscriptionItem.canceled",
      slug: "pro",
      currentPlan: "pro",
    });
    expect(decision).toEqual({ action: "apply", plan: "pro", subscriptionStatus: "canceled" });
    expect(decision).not.toMatchObject({ plan: "free" });
  });

  it("ignores a cancel of the old item after a plan switch", () => {
    expect(
      decideClerkBillingUpdate({
        eventType: "subscriptionItem.canceled",
        slug: "pro",
        currentPlan: "business",
      })
    ).toEqual({ action: "ignore", reason: "stale_item_plan_mismatch" });
  });

  it("lets the event type win over a payload status of active", () => {
    expect(
      decideClerkBillingUpdate({
        eventType: "subscriptionItem.canceled",
        eventStatus: "active",
        slug: "pro",
        currentPlan: "pro",
      })
    ).toEqual({ action: "apply", plan: "pro", subscriptionStatus: "canceled" });
  });
});

describe("decideClerkBillingUpdate — past_due", () => {
  it("recognises the camelCase event name with no payload status", () => {
    expect(
      decideClerkBillingUpdate({
        eventType: "subscriptionItem.pastDue",
        eventStatus: undefined,
        slug: "pro",
        currentPlan: "pro",
      })
    ).toEqual({ action: "apply", plan: "pro", subscriptionStatus: "past_due" });
  });

  it("still tolerates the snake_case spelling", () => {
    expect(
      decideClerkBillingUpdate({
        eventType: "subscriptionItem.past_due",
        slug: "pro",
        currentPlan: "pro",
      })
    ).toEqual({ action: "apply", plan: "pro", subscriptionStatus: "past_due" });
  });

  // A dunning transition is a status change ON an item; it must never move the plan.
  // Reachable without any Svix reordering: a pro payer whose card is failing switches to
  // business with a good card, and the still-open pro invoice then emits pastDue(pro) AFTER
  // active(business), in genuine time order.
  it("does not downgrade a business payer on a past_due for the old pro item", () => {
    expect(
      decideClerkBillingUpdate({
        eventType: "subscriptionItem.pastDue",
        slug: "pro",
        currentPlan: "business",
      })
    ).toEqual({ action: "ignore", reason: "stale_item_plan_mismatch" });
  });

  it("does not grant business to a pro payer on a past_due for a business item", () => {
    expect(
      decideClerkBillingUpdate({
        eventType: "subscriptionItem.pastDue",
        slug: "business",
        currentPlan: "pro",
      })
    ).toEqual({ action: "ignore", reason: "stale_item_plan_mismatch" });
  });
});

describe("decideClerkBillingUpdate — trialing", () => {
  it("records a trial rather than reporting it as active", () => {
    expect(
      decideClerkBillingUpdate({
        eventType: "subscriptionItem.active",
        eventStatus: "trialing",
        slug: "pro",
        currentPlan: "free",
      })
    ).toEqual({ action: "apply", plan: "pro", subscriptionStatus: "trialing" });
  });

  it("self-heals a trialing status on the plan already held", () => {
    expect(
      decideClerkBillingUpdate({
        eventType: "subscriptionItem.updated",
        eventStatus: "trialing",
        slug: "pro",
        currentPlan: "pro",
      })
    ).toEqual({ action: "apply", plan: "pro", subscriptionStatus: "trialing" });
  });

  it("does not resurrect a trialing status over a recorded cancel", () => {
    expect(
      decideClerkBillingUpdate({
        eventType: "subscriptionItem.updated",
        eventStatus: "trialing",
        slug: "pro",
        currentPlan: "pro",
        currentSubscriptionStatus: "canceled",
      })
    ).toEqual({ action: "ignore", reason: "would_resurrect_canceled_status" });
  });
});

describe("clerkUserIdFromPayer", () => {
  it("takes the documented user_id field", () => {
    expect(clerkUserIdFromPayer({ id: "payer_abc", user_id: "user_123" })).toBe("user_123");
  });

  // payer.id identifies the payer record (an organization payer, for instance), so using it
  // as a clerkId is a guaranteed lookup miss — which now costs an hour of 503 retries.
  it.each([
    { id: "payer_abc" },
    { id: "org_abc" },
    { id: "" },
    { user_id: "" },
    {},
    null,
    undefined,
  ])("refuses the unusable payer %o", (payer) => {
    expect(clerkUserIdFromPayer(payer)).toBeUndefined();
  });

  it("still accepts an id that is unambiguously a Clerk user id", () => {
    expect(clerkUserIdFromPayer({ id: "user_123" })).toBe("user_123");
  });
});

describe("decideClerkBillingUpdate — activation and unmapped slugs", () => {
  it("applies an upgrade", () => {
    expect(
      decideClerkBillingUpdate({
        eventType: "subscriptionItem.active",
        slug: "business",
        currentPlan: "pro",
      })
    ).toEqual({ action: "apply", plan: "business", subscriptionStatus: "active" });
  });

  it.each(["", "free_user", undefined, null])("never acts on slug %o", (slug) => {
    expect(
      decideClerkBillingUpdate({
        eventType: "subscriptionItem.ended",
        slug,
        currentPlan: "pro",
      })
    ).toEqual({ action: "ignore", reason: "unmapped_or_free_slug" });
  });
});

describe("decideClerkBillingUpdate — an undocumented type is a STATUS-ONLY self-heal", () => {
  // subscriptionItem.updated fires when a property changed WITHOUT a status change (every
  // renewal moves the period), so its payload status is no evidence about which item is
  // current. It may refresh the status of the held plan and nothing else.
  it("refreshes the status of the plan the user already holds", () => {
    expect(
      decideClerkBillingUpdate({
        eventType: "subscriptionItem.updated",
        eventStatus: "active",
        slug: "pro",
        currentPlan: "pro",
      })
    ).toEqual({ action: "apply", plan: "pro", subscriptionStatus: "active" });
  });

  it("never flips a paying customer onto another plan (cross-item race, paid to paid)", () => {
    expect(
      decideClerkBillingUpdate({
        eventType: "subscriptionItem.updated",
        eventStatus: "active",
        slug: "pro",
        currentPlan: "business",
      })
    ).toEqual({ action: "ignore", reason: "stale_item_plan_mismatch" });
  });

  it("never grants a plan the user does not hold", () => {
    expect(
      decideClerkBillingUpdate({
        eventType: "subscriptionItem.updated",
        eventStatus: "active",
        slug: "business",
        currentPlan: "pro",
      })
    ).toEqual({ action: "ignore", reason: "stale_item_plan_mismatch" });
  });

  it("never revokes a plan from an inferred `ended` status", () => {
    expect(
      decideClerkBillingUpdate({
        eventType: "subscriptionItem.updated",
        eventStatus: "ended",
        slug: "pro",
        currentPlan: "pro",
      })
    ).toEqual({ action: "ignore", reason: "plan_change_needs_typed_event" });
  });

  it("does not resurrect an `active` status over a recorded cancel (grace period)", () => {
    expect(
      decideClerkBillingUpdate({
        eventType: "subscriptionItem.updated",
        eventStatus: "active",
        slug: "pro",
        currentPlan: "pro",
        currentSubscriptionStatus: "canceled",
      })
    ).toEqual({ action: "ignore", reason: "would_resurrect_canceled_status" });
  });

  it("still lets an explicit `active` event clear a canceled status", () => {
    expect(
      decideClerkBillingUpdate({
        eventType: "subscriptionItem.active",
        slug: "pro",
        currentPlan: "pro",
        currentSubscriptionStatus: "canceled",
      })
    ).toEqual({ action: "apply", plan: "pro", subscriptionStatus: "active" });
  });

  it("ignores an upcoming item", () => {
    expect(
      decideClerkBillingUpdate({
        eventType: "subscriptionItem.updated",
        eventStatus: "upcoming",
        slug: "pro",
        currentPlan: "pro",
      })
    ).toEqual({ action: "ignore", reason: "no_actionable_status" });
  });
});
