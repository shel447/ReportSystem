import type { ReactNode } from "react";

type PageIntroBarProps = {
  description?: string;
  actions?: ReactNode;
  badge?: ReactNode;
  eyebrow?: string;
};

export function PageIntroBar({
  description,
  actions,
  badge,
  eyebrow = "Workspace",
}: PageIntroBarProps) {
  return (
    <div className="page-intro-bar">
      <div className="page-intro-bar__body">
        <p className="page-intro-bar__eyebrow">{eyebrow}</p>
        {description ? <p className="page-intro-bar__description">{description}</p> : null}
      </div>
      {badge || actions ? (
        <div className="page-intro-bar__aside">
          {badge ? <span className="inline-badge">{badge}</span> : null}
          {actions ? <div className="page-intro-bar__actions">{actions}</div> : null}
        </div>
      ) : null}
    </div>
  );
}
