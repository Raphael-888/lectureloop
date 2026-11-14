// Re-mounts on every navigation (unlike layout.tsx), so each page fades in.
// Opacity only on this wrapper: a transform here would break the fixed dock and chat.

export default function Template({ children }: { children: React.ReactNode }) {
  return <div className="route-in">{children}</div>;
}
