import type { ReactNode } from "react";

type StatusBannerProps = {
  tone?: "info" | "warning" | "success";
  title: string;
  children: ReactNode;
};

export function StatusBanner({ tone = "info", title, children }: StatusBannerProps) {
  return (
    <div className={`status-banner status-banner--${tone}`}>
      <strong>{title}</strong>
      <p>{children}</p>
    </div>
  );
}
