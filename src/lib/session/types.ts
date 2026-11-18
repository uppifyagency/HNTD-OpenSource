export type SessionUser = {
  id: string;
  email: string;
  name: string;
  firstName?: string;
};

export type Session =
  | { status: "loading" }
  | { status: "signedOut" }
  | { status: "signedIn"; user: SessionUser; getToken: () => Promise<string | null> };
