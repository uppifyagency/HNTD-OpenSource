import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Geist, Geist_Mono, Instrument_Serif } from "next/font/google";
import "./globals.css";
import { SessionProvider } from "@/lib/session";
import { SessionRoot } from "@/lib/session/server";
import { VisibilityPreviewProvider } from "@/contexts/VisibilityPreviewContext";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800", "900"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

// Editorial skin fonts (additive — used only under `.skin-editorial`)
const geist = Geist({
  variable: "--font-geist",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const instrumentSerif = Instrument_Serif({
  variable: "--font-instrument",
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
});

const siteUrl = "https://hntd.it";
const siteName = "HNTD Intel";
const siteDescription =
  "Piattaforma di recruiting intelligence che analizza l'attività reale su GitHub per trovare e valutare sviluppatori. Scoring AI su 6 dimensioni tecniche, non keyword su LinkedIn.";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "HNTD Intel — Trova developer da GitHub, non da LinkedIn",
    template: "%s | HNTD Intel",
  },
  description: siteDescription,
  keywords: [
    "recruiting developer",
    "GitHub recruiting",
    "developer sourcing",
    "technical hiring",
    "AI scoring developer",
    "recruiting intelligence",
    "trovare programmatori",
    "assumere sviluppatori",
    "GitHub talent search",
    "code quality assessment",
  ],
  authors: [{ name: siteName, url: siteUrl }],
  creator: siteName,
  publisher: siteName,
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  alternates: {
    canonical: siteUrl,
  },
  openGraph: {
    type: "website",
    locale: "it_IT",
    url: siteUrl,
    siteName: siteName,
    title: "HNTD Intel — Developer sourcing da GitHub",
    description:
      "I developer più forti non sono su LinkedIn. Stanno pushando su GitHub. Scoring AI su qualità del codice, architettura e testing.",
    images: [
      {
        url: `${siteUrl}/og-image.png`,
        width: 1200,
        height: 630,
        alt: "HNTD Intel — Recruiting intelligence per team tecnici",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "HNTD Intel — Trova developer da GitHub, non da LinkedIn",
    description:
      "Scoring AI su qualità del codice, architettura e testing. 50M+ profili GitHub analizzati.",
    images: [`${siteUrl}/og-image.png`],
  },
  other: {
    "theme-color": "#111111",
  },
};

// JSON-LD structured data
const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": `${siteUrl}/#organization`,
      name: siteName,
      url: siteUrl,
      description:
        "Recruiting intelligence platform that analyzes real GitHub activity to find and score software developers.",
      foundingDate: "2025",
      areaServed: "Worldwide",
      knowsAbout: [
        "Software Developer Recruiting",
        "GitHub Analysis",
        "AI-powered Code Assessment",
        "Technical Hiring",
      ],
    },
    {
      "@type": "SoftwareApplication",
      "@id": `${siteUrl}/#application`,
      name: siteName,
      url: siteUrl,
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
      description: siteDescription,
      offers: [
        {
          "@type": "Offer",
          name: "Free",
          price: "0",
          priceCurrency: "EUR",
          description:
            "1 ricerca al mese, scoring limitato, export CSV, talent pool limitato",
        },
        {
          "@type": "Offer",
          name: "Pro",
          price: "390",
          priceCurrency: "EUR",
          billingDuration: "P1M",
          description:
            "50 ricerche, matching AI da job description, pipeline kanban completa, export PDF + CSV",
        },
        {
          "@type": "Offer",
          name: "Business",
          price: "590",
          priceCurrency: "EUR",
          billingDuration: "P1M",
          description:
            "Ricerche illimitate, posti team multipli, accesso API, supporto prioritario",
        },
      ],
      featureList: [
        "AI-powered code quality scoring across 6 dimensions",
        "GitHub-based developer search (50M+ profiles)",
        "Job description matching with AI",
        "Candidate pipeline management (kanban)",
        "Export to CSV, PDF, JSON",
        "GDPR compliant — public data only",
      ],
      provider: {
        "@id": `${siteUrl}/#organization`,
      },
    },
    {
      "@type": "FAQPage",
      "@id": `${siteUrl}/#faq`,
      mainEntity: [
        {
          "@type": "Question",
          name: "Come fate ad accedere ai dati di GitHub?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Utilizziamo esclusivamente le API ufficiali di GitHub. Non facciamo scraping. Analizziamo solo dati pubblici: repository, commit, pull request, e profili che gli sviluppatori hanno scelto di rendere pubblici.",
          },
        },
        {
          "@type": "Question",
          name: "Lo scoring AI è affidabile?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "L'AI analizza il codice reale su 6 dimensioni distinte (qualità, architettura, testing, documentazione, complessità, consistenza). Non è un singolo numero magico — è un breakdown dettagliato che puoi interpretare in base alle tue priorità.",
          },
        },
        {
          "@type": "Question",
          name: "Funziona solo per sviluppatori con profilo GitHub attivo?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Sì. Questo è il nostro punto di forza e il nostro limite: analizziamo solo developer con contribuzioni pubbliche su GitHub. Questo esclude una parte del mercato, ma garantisce che ogni candidato ha codice verificabile.",
          },
        },
        {
          "@type": "Question",
          name: "Posso cercare developer in una specifica località?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Sì. Puoi filtrare per paese, città, o combinazione di entrambi. La località viene estratta dal profilo GitHub dello sviluppatore. Supportiamo ricerche in tutto il mondo.",
          },
        },
        {
          "@type": "Question",
          name: "Come funziona il matching da job description?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Incolla una JD completa e la nostra AI estrae automaticamente: linguaggi richiesti, livello di seniority, dominio tecnico, e soft requirements. Poi calcola un punteggio di match per ogni candidato trovato, con una spiegazione testuale del perché.",
          },
        },
        {
          "@type": "Question",
          name: "Posso esportare i risultati per il mio ATS?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Sì. Esporta in CSV (compatibile con qualsiasi ATS), PDF (schede candidato dettagliate per il team), o JSON (per integrazioni custom). Il piano Business include anche l'accesso API per automazioni.",
          },
        },
        {
          "@type": "Question",
          name: "Siete GDPR compliant?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Sì. Processiamo solo dati pubblicamente disponibili su GitHub. Non raccogliamo né conserviamo dati personali oltre a quelli che lo sviluppatore ha reso pubblici.",
          },
        },
        {
          "@type": "Question",
          name: "Posso cancellare il mio account?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Sì, in qualsiasi momento dalle impostazioni del tuo account. Tutti i tuoi dati (ricerche, pipeline, preferiti) vengono eliminati permanentemente. Nessun lock-in.",
          },
        },
      ],
    },
    {
      "@type": "WebSite",
      "@id": `${siteUrl}/#website`,
      url: siteUrl,
      name: siteName,
      description: siteDescription,
      inLanguage: "it-IT",
      publisher: {
        "@id": `${siteUrl}/#organization`,
      },
    },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SessionRoot>
      <html lang="it" suppressHydrationWarning>
        <head>
          <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
          />
        </head>
        <body
          className={`${inter.variable} ${jetbrainsMono.variable} ${geist.variable} ${geistMono.variable} ${instrumentSerif.variable} font-sans antialiased`}
          suppressHydrationWarning
        >
          <VisibilityPreviewProvider>
            <SessionProvider>{children}</SessionProvider>
          </VisibilityPreviewProvider>
        </body>
      </html>
    </SessionRoot>
  );
}
