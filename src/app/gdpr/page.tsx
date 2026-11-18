import LegalPageLayout from "@/components/LegalPageLayout";
import { LEGAL_CONTACT_EMAIL } from "@/lib/legal";

const sections = [
  { id: "data-controller", title: "Data Controller" },
  { id: "legal-basis", title: "Legal Basis for Processing" },
  { id: "data-subject-rights", title: "Data Subject Rights" },
  { id: "right-to-opt-out", title: "Right to Opt-Out" },
  { id: "data-processors", title: "Data Processors" },
  { id: "international-transfers", title: "International Transfers" },
  { id: "data-protection-officer", title: "Data Protection Officer" },
  { id: "supervisory-authority", title: "Supervisory Authority" },
];

export default function GdprPage() {
  return (
    <LegalPageLayout title="GDPR Compliance" lastUpdated="August 2, 2026" sections={sections}>
      <section id="data-controller">
        <h2>1. Data Controller</h2>
        <p>
          The data controller for the processing of personal data through GitHub HR is:
        </p>
        <ul>
          <li><strong>Entity:</strong> GitHub HR (operated by the operator of this deployment)</li>
          <li><strong>Email:</strong> <a href={`mailto:${LEGAL_CONTACT_EMAIL}`}>{LEGAL_CONTACT_EMAIL}</a></li>
          <li><strong>Jurisdiction:</strong> Italy, European Union</li>
        </ul>
        <p>
          The data controller determines the purposes and means of processing personal data
          in connection with the GitHub HR platform.
        </p>
      </section>

      <section id="legal-basis">
        <h2>2. Legal Basis for Processing</h2>
        <p>
          We process personal data under the following legal bases as defined by Article 6
          of the General Data Protection Regulation (GDPR):
        </p>

        <h3>Developer Data — Legitimate Interest (Art. 6(1)(f))</h3>
        <p>
          We process publicly available GitHub profile data under our legitimate interest in
          providing a recruitment technology service. This data is already made public by the
          developers themselves on GitHub. We have conducted a Legitimate Interest Assessment
          and concluded that:
        </p>
        <ul>
          <li>The data is already publicly available and accessible to anyone</li>
          <li>Processing serves the legitimate purpose of facilitating recruitment</li>
          <li>Developers can opt out at any time (see Section 4)</li>
          <li>We do not process sensitive/special categories of personal data</li>
          <li>The impact on developers is minimal given the data is already public</li>
        </ul>

        <h3>Recruiter Data — Contract Performance (Art. 6(1)(b))</h3>
        <p>
          We process recruiter account data as necessary for the performance of the contract
          between the recruiter and GitHub HR (i.e., providing the service you signed up for).
        </p>

        <h3>Payment Data — Legal Obligation (Art. 6(1)(c))</h3>
        <p>
          We process payment-related data as required by applicable tax, accounting, and
          financial regulations. Payment processing is handled by Clerk Billing with Stripe as its processor, which acts as
          an independent data controller for payment card data.
        </p>
      </section>

      <section id="data-subject-rights">
        <h2>3. Data Subject Rights</h2>
        <p>
          Under the GDPR, you have the following rights regarding your personal data:
        </p>
        <ul>
          <li>
            <strong>Right of Access (Art. 15):</strong> You may request a copy of the personal
            data we hold about you.
          </li>
          <li>
            <strong>Right to Rectification (Art. 16):</strong> You may request correction of
            inaccurate or incomplete personal data.
          </li>
          <li>
            <strong>Right to Erasure (Art. 17):</strong> You may request deletion of your
            personal data, subject to legal retention obligations.
          </li>
          <li>
            <strong>Right to Restriction (Art. 18):</strong> You may request that we restrict
            the processing of your data in certain circumstances.
          </li>
          <li>
            <strong>Right to Data Portability (Art. 20):</strong> You may request your data in
            a structured, commonly used, machine-readable format.
          </li>
          <li>
            <strong>Right to Object (Art. 21):</strong> You may object to the processing of
            your data based on legitimate interest. We will cease processing unless we
            demonstrate compelling legitimate grounds.
          </li>
        </ul>
        <p>
          To exercise any of these rights, contact us at{" "}
          <a href={`mailto:${LEGAL_CONTACT_EMAIL}`}>{LEGAL_CONTACT_EMAIL}</a>.
          We will respond to your request within 30 days.
        </p>
      </section>

      <section id="right-to-opt-out">
        <h2>4. Right to Opt-Out</h2>
        <p>
          <strong>For developers:</strong> If your public GitHub profile has been indexed by
          GitHub HR and you would like it removed from our database, you may request removal
          by emailing us at{" "}
          <a href={`mailto:${LEGAL_CONTACT_EMAIL}`}>{LEGAL_CONTACT_EMAIL}</a>{" "}
          with the subject line &quot;Profile Removal Request&quot; and your GitHub username.
        </p>
        <p>
          Upon receiving your request, we will:
        </p>
        <ul>
          <li>
            Delete your profile from our database within 30 days — including the assessments and
            code excerpts we derived from it, any saved shortlist entries referencing you, and your
            presence in past search results
          </li>
          <li>
            Add your GitHub username to an exclusion list that our indexing pipeline checks, so
            your profile is not collected again by a later search
          </li>
          <li>Confirm the removal to you by email</li>
        </ul>
        <p>
          The exclusion is enforced at the point where profiles are written to our database, not
          only at the point where they are searched, so it applies to every way a profile could
          otherwise re-enter the system.
        </p>
        <p>
          <strong>What we keep after erasure:</strong> to honour the exclusion we must retain your
          GitHub username on a suppression list indefinitely — that single record is the only way
          to recognise and refuse your profile in future. It holds the username and the date, and
          nothing else. If you later want to be indexable again, write to us and we will remove it.
        </p>
      </section>

      <section id="data-processors">
        <h2>5. Data Processors</h2>
        <p>
          We use the following third-party services as data processors in accordance with
          Article 28 of the GDPR:
        </p>
        <ul>
          <li>
            <strong>Convex</strong> (Convex, Inc. — United States) — Database hosting and
            real-time application backend. Stores developer profiles, task data, and pipeline logs.
          </li>
          <li>
            <strong>Clerk</strong> (Clerk, Inc. — United States) — Authentication and user
            identity management. Stores recruiter account credentials and session data.
          </li>
          <li>
            <strong>Clerk Billing / Stripe</strong> (Clerk, Inc. and Stripe, Inc. — United
            States) — Payment processing and subscription management. Billing is operated through
            Clerk Billing, which uses Stripe as its payment processor; Stripe acts as both a data
            processor and an independent data controller for payment card data.
          </li>
          <li>
            <strong>Anthropic</strong> (Anthropic, PBC — United States) — AI processing of public
            repository excerpts and job-description text to produce code-quality assessments.
          </li>
          <li>
            <strong>Voyage AI</strong> (Voyage AI, Inc. — United States) — Generates the numeric
            embeddings used for developer similarity search.
          </li>
          <li>
            <strong>Vercel</strong> (Vercel, Inc. — United States) — Application hosting,
            content delivery, and serverless function execution.
          </li>
        </ul>
        <p>
          Each processor is contractually obligated to process data only as instructed by us
          and to implement appropriate technical and organizational security measures.
        </p>
      </section>

      <section id="international-transfers">
        <h2>6. International Transfers</h2>
        <p>
          Our data processors are primarily located in the United States. Data transfers from
          the European Economic Area (EEA) to the United States are conducted in compliance
          with GDPR requirements using:
        </p>
        <ul>
          <li>EU-US Data Privacy Framework (where applicable)</li>
          <li>Standard Contractual Clauses (SCCs) as approved by the European Commission</li>
        </ul>
        <p>
          Our primary database (Convex) operates from the EU West 1 region, ensuring that
          core application data remains within the European Economic Area where possible.
        </p>
      </section>

      <section id="data-protection-officer">
        <h2>7. Data Protection Officer</h2>
        <p>
          For data protection inquiries, you may contact:{" "}
          <a href={`mailto:${LEGAL_CONTACT_EMAIL}`}>{LEGAL_CONTACT_EMAIL}</a>
        </p>
        <p>
          We are committed to addressing your data protection concerns promptly and will
          respond to all inquiries within 30 days.
        </p>
      </section>

      <section id="supervisory-authority">
        <h2>8. Supervisory Authority</h2>
        <p>
          If you believe that our processing of your personal data violates the GDPR, you have
          the right to lodge a complaint with a supervisory authority. The relevant authority
          for Italy is:
        </p>
        <ul>
          <li><strong>Garante per la protezione dei dati personali</strong></li>
          <li>Piazza Venezia 11, 00187 Roma, Italia</li>
          <li>Website: <a href="https://www.garanteprivacy.it" target="_blank" rel="noopener noreferrer">www.garanteprivacy.it</a></li>
          <li>Email: garante@gpdp.it</li>
        </ul>
        <p>
          You may also lodge a complaint with the supervisory authority of your country of
          residence if different from Italy.
        </p>
      </section>
    </LegalPageLayout>
  );
}
