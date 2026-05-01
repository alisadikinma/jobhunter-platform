import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, test, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { EasyApplyModal } from "@/components/easy-apply/EasyApplyModal";

vi.mock("@/hooks/useEasyApply", () => ({
  useEasyApply: () => ({
    mutate: vi.fn(),
    data: {
      application_id: 1,
      cv_agent_job_id: 10,
      email_agent_job_id: 11,
      generated_cv_id: 5,
    },
    isPending: false,
    isError: false,
    error: null,
    reset: vi.fn(),
  }),
}));

vi.mock("@/hooks/useProgress", () => ({
  useProgress: (id: number | null) =>
    id === null
      ? null
      : {
          agent_job_id: id,
          job_type: id === 10 ? "cv_tailor" : "cold_email",
          status: "completed",
          progress_pct: 100,
          current_step: "done",
          latest_log: null,
          error_message: null,
          result: {},
        },
}));

vi.mock("@/hooks/useEmails", () => ({
  useEmails: () => ({
    data: [
      {
        id: 99,
        application_id: 1,
        job_id: null,
        email_type: "initial",
        subject: "Hi",
        body: "Body",
        recipient_email: "x@y.z",
        recipient_name: "X",
        strategy: null,
        status: "draft",
        sent_at: null,
      },
      {
        id: 100,
        application_id: 1,
        job_id: null,
        email_type: "follow_up_1",
        subject: "Quick follow-up",
        body: "Following up...",
        recipient_email: "x@y.z",
        recipient_name: "X",
        strategy: null,
        status: "draft",
        sent_at: null,
      },
    ],
    isLoading: false,
  }),
  useUpdateEmail: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useSendEmail: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

function wrap(ui: ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("EasyApplyModal", () => {
  test("when both jobs completed, shows review pane with editable subject + body", () => {
    wrap(<EasyApplyModal jobId={113} onClose={() => {}} />);
    expect(screen.getByLabelText(/subject/i)).toBeTruthy();
    expect(screen.getByLabelText(/body/i)).toBeTruthy();
    expect(screen.getByLabelText(/recipient email/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: /send now/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /save draft/i })).toBeTruthy();
  });

  test("shows initial email subject in subject input", () => {
    wrap(<EasyApplyModal jobId={113} onClose={() => {}} />);
    const subject = screen.getByLabelText(/subject/i) as HTMLInputElement;
    expect(subject.value).toBe("Hi");
  });

  test("shows initial email body in body textarea", () => {
    wrap(<EasyApplyModal jobId={113} onClose={() => {}} />);
    const body = screen.getByLabelText(/body/i) as HTMLTextAreaElement;
    expect(body.value).toBe("Body");
  });

  test("recipient email is prefilled from initial draft", () => {
    wrap(<EasyApplyModal jobId={113} onClose={() => {}} />);
    const recipient = screen.getByLabelText(/recipient email/i) as HTMLInputElement;
    expect(recipient.value).toBe("x@y.z");
  });

  test("renders tailored CV download link with correct generated_cv_id", () => {
    wrap(<EasyApplyModal jobId={113} onClose={() => {}} />);
    const links = screen.getAllByRole("link");
    const cvLink = links.find((a) =>
      a.getAttribute("href")?.includes("/api/cv/5/download/pdf"),
    );
    expect(cvLink).toBeTruthy();
  });
});
