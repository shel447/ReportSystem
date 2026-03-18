import type { ReactNode } from "react";

type PageSectionProps = {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
};

export function PageSection({ title, description, actions, children }: PageSectionProps) {
  return (
    <section className="page-section">
      <header className="page-section__header">
        <div>
          {title ? <h2>{title}</h2> : null}
          {description ? <p>{description}</p> : null}
        </div>
        {actions ? <div className="page-section__actions">{actions}</div> : null}
      </header>
      {children}
    </section>
  );
}
