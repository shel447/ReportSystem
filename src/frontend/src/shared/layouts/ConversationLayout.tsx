import type { ReactNode } from "react";

type ConversationLayoutProps = {
  intro?: ReactNode;
  notices?: ReactNode;
  stream: ReactNode;
  composer: ReactNode;
};

export function ConversationLayout({
  intro,
  notices,
  stream,
  composer,
}: ConversationLayoutProps) {
  return (
    <div className="conversation-layout">
      {intro ? <div className="conversation-layout__intro">{intro}</div> : null}
      {notices ? <div className="conversation-layout__notices">{notices}</div> : null}
      <div className="conversation-layout__surface">
        <div className="conversation-layout__stream">{stream}</div>
        <div className="conversation-layout__composer">{composer}</div>
      </div>
    </div>
  );
}
