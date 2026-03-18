import type { ReactNode } from "react";

type DetailPageLayoutProps = {
  intro?: ReactNode;
  summary?: ReactNode;
  content: ReactNode;
};

export function DetailPageLayout({ intro, summary, content }: DetailPageLayoutProps) {
  return (
    <div className="detail-page-layout">
      {intro ? <div className="detail-page-layout__intro">{intro}</div> : null}
      {summary ? <div className="detail-page-layout__summary">{summary}</div> : null}
      <div className="detail-page-layout__content">{content}</div>
    </div>
  );
}
