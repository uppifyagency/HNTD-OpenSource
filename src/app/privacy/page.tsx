import LegalPageLayout from "@/components/LegalPageLayout";
import { LEGAL_CONTACT_EMAIL } from "@/lib/legal";

const sections = [
  { id: "introduction", title: "Introduction" },
  { id: "data-we-collect", title: "Data We Collect" },
  { id: "how-we-use-data", title: "How We Use Data" },
  { id: "data-storage", title: "Data Storage & Security" },
  { id: "data-retention", title: "Data Retention" },
  { id: "third-party-sharing", title: "Third-Party Sharing" },
  { id: "your-rights", title: "Your Rights" },
  { id: "contact", title: "Contact" },
  { id: "updates", title: "Updates to This Policy" },
];

export default function PrivacyPage() {
  return (
    <LegalPageLayout title="Privacy Policy" lastUpdated="August 2, 2026" sections={sections}>
      <section id="introduction">
        <h2>1. Introduction</h2>
        <p>
          GitHub HR (&quot;we,&quot; &quot;us,&quot; or &quot;our&quot;) operates a SaaS platform that helps
          recruiters find and evaluate software developers using publicly available GitHub data. This Privacy
          Policy explains what data we collect, how we use it, and your rights regarding that data.
        </p>
        <p>
          This policy applies to all users of our platform, including recruiters who create accounts and
          developers whose public GitHub profiles are indexed by our service.
        </p>
      </section>

      <section id="data-we-collect">
        <h2>2. Data We Collect</h2>

        <h3>Developer Data (from Public GitHub)</h3>
        <p>
          We collect publicly available information from GitHub profiles through GitHub&apos;s official API.
          This includes:
        </p>
        <ul>
          <li>Username, display name, bio, location, company, personal website and public social handles</li>
          <li>Public repository names, descriptions, primary languages and language byte counts</li>
          <li>Contribution activity (commit counts, pull requests, reviews, recent push dates)</li>
          <li>Follower and following counts, and the &quot;available for hire&quot; flag if set</li>
          <li>Public email address (only if the developer has made it public on GitHub)</li>
          <li>
            <strong>Excerpts of public source code, and public commit metadata</strong> — to assess
            code quality we retain samples of file contents, README files, dependency manifests,
            directory listings, and commit messages with their dates and identifiers, all from
            public repositories.
          </li>
          <li>Profile picture, organisation memberships, account creation date, and GitHub programme badges</li>
          <li>
            Aggregate counters GitHub exposes about activity in repositories we cannot see
            (a total count of restricted contributions). This is a number only — no private
            repository content, names or metadata.
          </li>
          <li>
            <strong>Assessments we generate</strong> — an AI-produced written summary, numeric
            scores, and a vector embedding derived from the material above. These are our own
            inferences about the developer, not data GitHub provided.
          </li>
          <li>
            <strong>Recruiter activity about a developer</strong> — whether a recruiter saved,
            contacted, shortlisted or rejected the profile, any free-text note they wrote, and
            aggregate view and save counts.
          </li>
        </ul>
        <p>
          <strong>We do not access private repositories, private profile information, or any data
          requiring GitHub authentication on behalf of indexed developers.</strong> All developer data
          is sourced exclusively from publicly available GitHub API endpoints.
        </p>

        <h3>Recruiter Account Data</h3>
        <p>
          When you create an account, we collect the information you provide through our authentication
          provider Clerk, including:
        </p>
        <ul>
          <li>Email address</li>
          <li>Full name</li>
          <li>Company name (if provided)</li>
          <li>Authentication credentials (managed securely by Clerk)</li>
        </ul>

        <h3>Payment Data</h3>
        <p>
          Payment processing is handled by Clerk Billing, which uses Stripe as its payment
          processor. We do not store credit card numbers, bank account details, or other sensitive
          payment information on our servers. We receive only limited transaction data (plan type,
          subscription status, billing dates) necessary to manage your account.
        </p>
      </section>

      <section id="how-we-use-data">
        <h2>3. How We Use Data</h2>
        <p>We use the data we collect for the following purposes:</p>
        <ul>
          <li>
            <strong>AI-Powered Scoring:</strong> We analyze public GitHub activity using artificial
            intelligence to generate code quality scores across multiple dimensions (code quality,
            activity level, project diversity, documentation, community engagement, and technical breadth).
          </li>
          <li>
            <strong>Candidate Matching:</strong> We match developer profiles against job descriptions
            or search criteria provided by recruiters.
          </li>
          <li>
            <strong>Ranked Leaderboards:</strong> We present scored and ranked developer profiles to
            recruiters through our dashboard.
          </li>
          <li>
            <strong>Account Management:</strong> We use recruiter data to manage accounts, process
            subscriptions, and provide customer support.
          </li>
        </ul>
      </section>

      <section id="data-storage">
        <h2>4. Data Storage & Security</h2>
        <p>Your data is stored and processed using the following infrastructure providers:</p>
        <ul>
          <li><strong>Convex</strong> (Convex, Inc., a United States company; our deployment runs in the EU West 1 region) — Primary database for developer profiles, task data, and application state</li>
          <li><strong>Clerk</strong> (managed service) — Authentication and user account management</li>
          <li><strong>Clerk Billing / Stripe</strong> (managed services) — Payment processing and subscription management</li>
          <li><strong>Vercel</strong> (global CDN) — Application hosting and delivery</li>
          <li>
            <strong>Anthropic</strong> (United States) — The AI models that assess public code and
            interpret job descriptions. Public repository excerpts and recruiter search text are
            sent for processing.
          </li>
          <li>
            <strong>Voyage AI</strong> (United States) — Generates the numeric embeddings used for
            similarity search. Receives username, name, location, bio, repository names and the
            generated summary.
          </li>
        </ul>
        <p>
          All data is transmitted over encrypted connections (TLS/HTTPS). We rely on the security
          practices of our infrastructure providers, all of which maintain industry-standard security
          certifications.
        </p>
      </section>

      <section id="data-retention">
        <h2>5. Data Retention</h2>
        <ul>
          <li>
            <strong>Developer profiles</strong> are retained until a deletion request is received
            from the developer. Profiles may be refreshed periodically with updated public GitHub data.
          </li>
          <li>
            <strong>Recruiter accounts</strong> are retained for the duration of the active subscription
            and in accordance with Clerk&apos;s data retention policies.
          </li>
          <li>
            <strong>Payment records</strong> are retained as required by applicable tax and accounting
            regulations, managed by Stripe.
          </li>
          <li>
            <strong>Pipeline logs</strong> (internal processing records) are retained for as long as
            the deployment keeps them. We do not currently operate an automated deletion schedule
            for them, so we do not claim a fixed retention period. They contain task identifiers,
            phase names, diagnostic messages and — when processing a specific profile fails — the
            GitHub username it failed on.
          </li>
        </ul>
      </section>

      <section id="third-party-sharing">
        <h2>6. Third-Party Sharing</h2>
        <p>
          We do not sell, rent, or share personal data with third parties for marketing purposes.
          Data is shared only with the infrastructure and AI providers listed in section 4
          (Convex, Clerk, Clerk Billing/Stripe, Vercel, Anthropic, Voyage AI) as necessary to
          operate the service. These providers act as data processors on our behalf
          and are contractually obligated to protect your data.
        </p>
      </section>

      <section id="your-rights">
        <h2>7. Your Rights</h2>
        <p>You have the right to:</p>
        <ul>
          <li><strong>Access</strong> — Request a copy of the data we hold about you</li>
          <li><strong>Correction</strong> — Request correction of inaccurate data</li>
          <li><strong>Deletion</strong> — Request deletion of your data from our systems</li>
          <li><strong>Portability</strong> — Request your data in a machine-readable format</li>
          <li><strong>Objection</strong> — Object to the processing of your data</li>
        </ul>
        <p>
          <strong>Developers:</strong> If your public GitHub profile has been indexed by our service
          and you would like it removed, please contact us at the email below. We will process
          removal requests within 30 days.
        </p>
        <p>
          <strong>Recruiters:</strong> You can manage your account data through your dashboard
          settings. For account deletion, contact us at the email below.
        </p>
      </section>

      <section id="contact">
        <h2>8. Contact</h2>
        <p>
          For any privacy-related requests or questions, contact us at:{" "}
          <a href={`mailto:${LEGAL_CONTACT_EMAIL}`}>{LEGAL_CONTACT_EMAIL}</a>
        </p>
      </section>

      <section id="updates">
        <h2>9. Updates to This Policy</h2>
        <p>
          We may update this Privacy Policy from time to time. When we make material changes we
          update the &quot;Last updated&quot; date at the top of this page. We do not currently operate an
          individual notification channel, so we do not promise email or in-app notice; the date
          above is the record. Continued use of the
          service after changes constitutes acceptance of the updated policy.
        </p>
      </section>
    </LegalPageLayout>
  );
}
