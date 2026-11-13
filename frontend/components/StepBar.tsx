// The 4-step strip in the header: Upload → Concepts → Review → Quiz.

const STEPS = ["Upload", "Concepts", "Review", "Quiz"];

export default function StepBar({ current }: { current: 1 | 2 | 3 | 4 }) {
  return (
    <nav aria-label="Steps" className="stepbar">
      {STEPS.map((s, i) => (
        <span key={s} className={`step ${i + 1 === current ? "now" : i + 1 < current ? "past" : ""}`}>
          {i + 1} {s}
        </span>
      ))}
    </nav>
  );
}
