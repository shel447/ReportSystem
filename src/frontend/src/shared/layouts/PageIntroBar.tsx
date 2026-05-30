import type { ReactNode } from "react";

type PageIntroBarProps = {
  title: string;
  description?: string;
  actions?: ReactNode;
  badge?: ReactNode;
  eyebrow?: string;
};

export function PageIntroBar({
  title,
  description,
  actions,
  badge,
  eyebrow,
}: PageIntroBarProps) {
  return (
    <div className="page-intro-bar">
      <div className="page-intro-bar__body">
        <div className="page-intro-bar__title-row">
          <h1>{title}</h1>
          {eyebrow ? <span>{eyebrow}</span> : null}
        </div>
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
