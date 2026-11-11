import ReactMarkdown from "react-markdown";

export default function Markdown({ children, className = "" }: { children: string; className?: string }) {
  return (
    <div className={`markdown ${className}`}>
      <ReactMarkdown>{children}</ReactMarkdown>
    </div>
  );
}
