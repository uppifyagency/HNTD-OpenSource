import LegalPageLayout from "@/components/LegalPageLayout";
import { LEGAL_CONTACT_EMAIL } from "@/lib/legal";

const sections = [
  { id: "service-description", title: "Service Description" },
  { id: "account-terms", title: "Account Terms" },
  { id: "billing", title: "Billing & Subscriptions" },
  { id: "acceptable-use", title: "Acceptable Use" },
  { id: "intellectual-property", title: "Intellectual Property" },
  { id: "disclaimers", title: "Disclaimers" },
  { id: "limitation-of-liability", title: "Limitation of Liability" },
  { id: "termination", title: "Termination" },
  { id: "governing-law", title: "Governing Law" },
  { id: "contact", title: "Contact" },
];

export default function TermsPage() {
  return (
    <LegalPageLayout title="Terms of Service" lastUpdated="March 4, 2026" sections={sections}>
      <section id="service-description">
        <h2>1. Service Description</h2>
        <p>
          GitHub HR is a SaaS platform that helps recruiters discover and evaluate software developers
          by analyzing publicly available GitHub data. Our service uses artificial intelligence to score
          developer profiles across multiple dimensions and present ranked candidate leaderboards.
        </p>
        <p>
          The service is designed for professional recruiters and hiring managers. By using GitHub HR,
          you agree to these Terms of Service.
        </p>
      </section>

      <section id="account-terms">
        <h2>2. Account Terms</h2>
        <p>
          To use GitHub HR, you must create an account and provide accurate, complete registration
          information. You are responsible for maintaining the confidentiality of your account
          credentials and for all activity that occurs under your account.
        </p>
        <h3>Plans</h3>
        <ul>
          <li><strong>Free:</strong> Up to 3 search tasks, basic scoring, limited results</li>
          <li><strong>Pro:</strong> Up to 50 search tasks, full AI scoring, priority processing</li>
          <li><strong>Business:</strong> Up to 200 search tasks, advanced analytics, dedicated support</li>
        </ul>
        <p>
          You must be at least 18 years old and have the legal authority to enter into these terms
          on behalf of yourself or your organization.
        </p>
      </section>

      <section id="billing">
        <h2>3. Billing & Subscriptions</h2>
        <p>
          Paid plans are billed on a recurring basis (monthly or annually) through Stripe. By
          subscribing to a paid plan, you authorize us to charge your payment method at the
          beginning of each billing cycle.
        </p>
        <ul>
          <li><strong>Billing cycle:</strong> Subscriptions renew automatically unless cancelled before the renewal date</li>
          <li><strong>Cancellation:</strong> You may cancel your subscription at any time through your account settings. Access continues until the end of the current billing period</li>
          <li><strong>Refunds:</strong> We do not provide refunds for partial billing periods. If you believe you have been charged in error, contact us within 30 days</li>
          <li><strong>Price changes:</strong> We will notify you at least 30 days before any price increases take effect</li>
        </ul>
      </section>

      <section id="acceptable-use">
        <h2>4. Acceptable Use</h2>
        <p>You agree NOT to:</p>
        <ul>
          <li><strong>Scrape or redistribute:</strong> Systematically download, scrape, or redistribute developer data obtained through our platform</li>
          <li><strong>Resell data:</strong> Resell, sublicense, or commercially redistribute candidate information from GitHub HR</li>
          <li><strong>Harass developers:</strong> Use information obtained through our platform to spam, harass, or send unsolicited bulk communications to developers</li>
          <li><strong>Automated access:</strong> Access the platform via automated means (bots, scrapers, scripts) without our written permission</li>
          <li><strong>Circumvent limits:</strong> Create multiple accounts or use other methods to circumvent plan limits</li>
          <li><strong>Misrepresent:</strong> Misrepresent your identity, affiliation, or the purpose of your use of the platform</li>
        </ul>
        <p>
          Violation of these terms may result in immediate account suspension or termination
          without refund.
        </p>
      </section>

      <section id="intellectual-property">
        <h2>5. Intellectual Property</h2>
        <p>
          The GitHub HR platform, including its design, code, algorithms, and scoring methodologies,
          is proprietary and protected by intellectual property laws. You may not copy, modify,
          reverse-engineer, or create derivative works from our platform.
        </p>
        <p>
          Developer profile data displayed on our platform is sourced from publicly available
          GitHub data. We do not claim ownership over this public data. AI-generated scores
          and analyses are our proprietary output based on public data inputs.
        </p>
      </section>

      <section id="disclaimers">
        <h2>6. Disclaimers</h2>
        <ul>
          <li>
            <strong>AI Scores Are Estimates:</strong> Developer scores generated by our AI are
            computational estimates based on publicly available data. They are not guarantees of
            developer skill, reliability, or suitability for any specific role. Scores should be
            used as one factor among many in hiring decisions.
          </li>
          <li>
            <strong>Public Data Limitations:</strong> Developer profiles are based solely on
            publicly available GitHub activity. A developer&apos;s GitHub profile may not reflect
            their full experience, skills, or professional work (e.g., private repositories,
            non-GitHub contributions).
          </li>
          <li>
            <strong>No Employment Guarantee:</strong> GitHub HR is a sourcing tool, not a
            recruitment agency. We do not guarantee that any developer is available for hire,
            interested in opportunities, or suitable for your specific needs.
          </li>
        </ul>
      </section>

      <section id="limitation-of-liability">
        <h2>7. Limitation of Liability</h2>
        <p>
          To the maximum extent permitted by applicable law, GitHub HR and its operators shall not
          be liable for any indirect, incidental, special, consequential, or punitive damages,
          including but not limited to loss of profits, data, or business opportunities, arising
          from your use of the service.
        </p>
        <p>
          Our total liability for any claim arising from these terms or your use of the service
          shall not exceed the amount you paid us in the 12 months preceding the claim.
        </p>
      </section>

      <section id="termination">
        <h2>8. Termination</h2>
        <p>
          We may suspend or terminate your account at any time if you violate these Terms of Service.
          Upon termination, your right to use the platform ceases immediately. We may retain your
          data as required by law or for legitimate business purposes (e.g., resolving disputes,
          enforcing agreements).
        </p>
        <p>
          You may close your account at any time by contacting us. Upon account closure, we will
          delete your personal data within 30 days, except where retention is required by law.
        </p>
      </section>

      <section id="governing-law">
        <h2>9. Governing Law</h2>
        <p>
          These Terms of Service are governed by the laws of Italy and the European Union.
          Any disputes arising from these terms shall be subject to the exclusive jurisdiction
          of the courts of Italy. Nothing in these terms limits your rights under mandatory
          consumer protection laws of your country of residence.
        </p>
      </section>

      <section id="contact">
        <h2>10. Contact</h2>
        <p>
          For questions about these Terms of Service, contact us at:{" "}
          <a href={`mailto:${LEGAL_CONTACT_EMAIL}`}>{LEGAL_CONTACT_EMAIL}</a>
        </p>
      </section>
    </LegalPageLayout>
  );
}
