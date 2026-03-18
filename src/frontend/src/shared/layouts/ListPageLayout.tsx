import type { ReactNode } from "react";

type ListPageLayoutProps = {
  intro?: ReactNode;
  content: ReactNode;
};

export function ListPageLayout({ intro, content }: ListPageLayoutProps) {
  return (
    <div className="list-page-layout">
      {intro ? <div className="list-page-layout__intro">{intro}</div> : null}
      <div className="list-page-layout__content">{content}</div>
    </div>
  );
}
