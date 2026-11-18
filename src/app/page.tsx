import { redirect } from "next/navigation";

// The open-source build has no marketing landing: `/` opens the app.
export default function Home() {
  redirect("/dashboard");
}
