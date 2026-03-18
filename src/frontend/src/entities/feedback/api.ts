import { postJson } from "../../shared/api/http";

type FeedbackPayload = {
  submitter: string;
  content: string;
  priority: string;
  images: string[];
};

export function submitFeedback(payload: FeedbackPayload) {
  return postJson<{ status: string; feedback_id: string }>("/api/feedback/", payload);
}
