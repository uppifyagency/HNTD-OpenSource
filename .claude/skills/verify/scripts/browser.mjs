// One-shot browser driver for the verify skill. Runs the steps in order in one page, then exits.
// Usage: hntd-verify browser --out DIR STEP [ARG...] STEP [ARG...] ...
//
//   goto PATH              open PATH on the instance (for example /dashboard)
//   click SELECTOR         click the element
//   fill SELECTOR VALUE    replace the value of an input or textarea
//   type SELECTOR VALUE    type VALUE key by key (for inputs that react to keys)
//   press KEY              press a key in the focused element (for example Enter)
//   select SELECTOR VALUE  choose an <option> by value
//   expect SELECTOR        wait until the element is visible
//   absent SELECTOR        wait until no such element is visible
//   url REGEX              wait until the page URL matches
//   text SELECTOR          print the element's text
//   download SELECTOR NAME click the element and save the file it downloads as DIR/NAME
//   aria NAME              write the ARIA snapshot of the page to DIR/NAME.aria.txt
//   shot NAME              write a full-page screenshot to DIR/NAME.png
//
// SELECTOR is a Playwright selector: role=button[name="Elimina"], text="New search.", css.
// Every step is echoed to stdout and appended to DIR/steps.log. Browser console errors go to
// DIR/console.log. On a failed step the page is saved as DIR/FAILED.png and the exit code is 1.
import fs from "node:fs";
import path from "node:path";
import { chromium } from "@playwright/test";

const ARITY = { goto: 1, click: 1, fill: 2, type: 2, press: 1, select: 2, expect: 1, absent: 1, url: 1, text: 1, download: 2, aria: 1, shot: 1 };
const TIMEOUT = Number(process.env.HNTD_VERIFY_TIMEOUT ?? 20000);

async function launch() {
  try {
    return await chromium.launch({ channel: "chrome" });
  } catch {
    return await chromium.launch();
  }
}

const args = process.argv.slice(2);
if (args[0] === "--check") {
  await (await launch()).close();
  process.exit(0);
}

let out = `test-results/verify/${new Date().toISOString().replace(/[:.]/g, "-")}`;
if (args[0] === "--out") out = args.splice(0, 2)[1];
const base = process.env.HNTD_VERIFY_BASE;
if (!base) throw new Error("run this through hntd-verify browser, which sets the instance URL");

const steps = [];
for (let i = 0; i < args.length; ) {
  const name = args[i];
  if (!(name in ARITY)) throw new Error(`unknown step "${name}". Steps: ${Object.keys(ARITY).join(", ")}`);
  const params = args.slice(i + 1, i + 1 + ARITY[name]);
  if (params.length < ARITY[name]) throw new Error(`step "${name}" needs ${ARITY[name]} argument(s)`);
  steps.push({ name, params });
  i += 1 + ARITY[name];
}

fs.mkdirSync(out, { recursive: true });
const log = (line) => {
  console.log(line);
  fs.appendFileSync(path.join(out, "steps.log"), line + "\n");
};

const browser = await launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
// The cookie a browser gets from the link `npm run local` prints. Without it the app signs no session.
if (process.env.HNTD_VERIFY_BROWSER_KEY) {
  await context.addCookies([
    { name: "hntd_local", value: process.env.HNTD_VERIFY_BROWSER_KEY, url: base, httpOnly: true, sameSite: "Strict" },
  ]);
}
const page = await context.newPage();
page.setDefaultTimeout(TIMEOUT);
page.on("console", (m) => {
  if (m.type() === "error") fs.appendFileSync(path.join(out, "console.log"), m.text() + "\n");
});
page.on("pageerror", (e) => fs.appendFileSync(path.join(out, "console.log"), `pageerror: ${e.message}\n`));

const run = {
  goto: (p) => page.goto(base + p, { waitUntil: "domcontentloaded" }),
  click: (s) => page.locator(s).first().click(),
  fill: (s, v) => page.locator(s).first().fill(v),
  type: (s, v) => page.locator(s).first().pressSequentially(v, { delay: 20 }),
  press: (k) => page.keyboard.press(k),
  select: (s, v) => page.locator(s).first().selectOption(v),
  expect: (s) => page.locator(s).first().waitFor({ state: "visible" }),
  absent: (s) => page.locator(s).first().waitFor({ state: "hidden" }),
  url: (re) => page.waitForURL(new RegExp(re)),
  text: async (s) => log(`  = ${(await page.locator(s).first().innerText()).replace(/\s+/g, " ").trim()}`),
  download: async (s, n) => {
    const [file] = await Promise.all([page.waitForEvent("download"), page.locator(s).first().click()]);
    await file.saveAs(path.join(out, n));
  },
  aria: async (n) => fs.writeFileSync(path.join(out, `${n}.aria.txt`), `# ${page.url()}\n` + (await page.locator("body").ariaSnapshot())),
  shot: (n) => page.screenshot({ path: path.join(out, `${n}.png`), fullPage: true }),
};

let code = 0;
log(`# ${new Date().toISOString()} ${base} -> ${out}`);
for (const { name, params } of steps) {
  try {
    await run[name](...params);
    log(`ok   ${name} ${params.join(" ")}  [${page.url().replace(base, "")}]`);
  } catch (e) {
    log(`FAIL ${name} ${params.join(" ")}: ${String(e.message).split("\n")[0]}`);
    await page.screenshot({ path: path.join(out, "FAILED.png"), fullPage: true }).catch(() => {});
    code = 1;
    break;
  }
}
await browser.close();
process.exit(code);
