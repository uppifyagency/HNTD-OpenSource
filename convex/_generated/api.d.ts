/* eslint-disable */
/**
 * Generated `api` utility.
 *
 * THIS CODE IS AUTOMATICALLY GENERATED.
 *
 * To regenerate, run `npx convex dev`.
 * @module
 */

import type * as adminAuthz from "../adminAuthz.js";
import type * as clerkBillingDecision from "../clerkBillingDecision.js";
import type * as developerViews from "../developerViews.js";
import type * as developers from "../developers.js";
import type * as erasure from "../erasure.js";
import type * as favorites from "../favorites.js";
import type * as frontendConfig from "../frontendConfig.js";
import type * as http from "../http.js";
import type * as localAuth from "../localAuth.js";
import type * as migrations from "../migrations.js";
import type * as pipelineLogs from "../pipelineLogs.js";
import type * as planLimits from "../planLimits.js";
import type * as taskResults from "../taskResults.js";
import type * as tasks from "../tasks.js";
import type * as users from "../users.js";
import type * as vectorSearch from "../vectorSearch.js";
import type * as webhookEvents from "../webhookEvents.js";
import type * as webhookOutcome from "../webhookOutcome.js";

import type {
  ApiFromModules,
  FilterApi,
  FunctionReference,
} from "convex/server";

declare const fullApi: ApiFromModules<{
  adminAuthz: typeof adminAuthz;
  clerkBillingDecision: typeof clerkBillingDecision;
  developerViews: typeof developerViews;
  developers: typeof developers;
  erasure: typeof erasure;
  favorites: typeof favorites;
  frontendConfig: typeof frontendConfig;
  http: typeof http;
  localAuth: typeof localAuth;
  migrations: typeof migrations;
  pipelineLogs: typeof pipelineLogs;
  planLimits: typeof planLimits;
  taskResults: typeof taskResults;
  tasks: typeof tasks;
  users: typeof users;
  vectorSearch: typeof vectorSearch;
  webhookEvents: typeof webhookEvents;
  webhookOutcome: typeof webhookOutcome;
}>;

/**
 * A utility for referencing Convex functions in your app's public API.
 *
 * Usage:
 * ```js
 * const myFunctionReference = api.myModule.myFunction;
 * ```
 */
export declare const api: FilterApi<
  typeof fullApi,
  FunctionReference<any, "public">
>;

/**
 * A utility for referencing Convex functions in your app's internal API.
 *
 * Usage:
 * ```js
 * const myFunctionReference = internal.myModule.myFunction;
 * ```
 */
export declare const internal: FilterApi<
  typeof fullApi,
  FunctionReference<any, "internal">
>;

export declare const components: {};
