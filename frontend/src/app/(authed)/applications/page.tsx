"use client";

import {
  closestCenter,
  DndContext,
  type DragEndEvent,
  PointerSensor,
  useDroppable,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical } from "lucide-react";
import Link from "next/link";

import {
  useKanban,
  useUpdateApplication,
  type Application,
} from "@/hooks/useApplications";
import { cn } from "@/lib/utils";

/** Phases group related statuses so the board reads "early → late". Each
 *  phase is a vertically-stacked group of columns sharing one tone. */
const PHASES: { tone: string; statuses: { id: string; label: string }[] }[] = [
  {
    tone: "neutral",
    statuses: [
      { id: "targeting", label: "Targeting" },
      { id: "cv_generating", label: "CV Generating" },
      { id: "cv_ready", label: "CV Ready" },
    ],
  },
  {
    tone: "blue",
    statuses: [
      { id: "applied", label: "Applied" },
      { id: "email_sent", label: "Email Sent" },
      { id: "replied", label: "Replied" },
    ],
  },
  {
    tone: "amber",
    statuses: [
      { id: "interview_scheduled", label: "Interview Scheduled" },
      { id: "interviewed", label: "Interviewed" },
    ],
  },
  {
    tone: "emerald",
    statuses: [
      { id: "offered", label: "Offered" },
      { id: "accepted", label: "Accepted" },
    ],
  },
  {
    tone: "red",
    statuses: [
      { id: "rejected", label: "Rejected" },
      { id: "ghosted", label: "Ghosted" },
    ],
  },
];

const TONE_DOT: Record<string, string> = {
  neutral: "bg-neutral-500",
  blue: "bg-brand-blue",
  amber: "bg-amber-500",
  emerald: "bg-emerald-500",
  red: "bg-red-500",
};

export default function ApplicationsPage() {
  const { data, isLoading } = useKanban();
  const update = useUpdateApplication();
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
  );

  function onDragEnd(e: DragEndEvent) {
    const id = e.active?.id;
    const targetStatus = e.over?.id;
    if (!id || !targetStatus || typeof targetStatus !== "string") return;

    const parsed = String(id).replace(/^app-/, "");
    const numericId = Number(parsed);
    if (Number.isNaN(numericId)) return;

    update.mutate({ id: numericId, patch: { status: targetStatus } });
  }

  const totalApps = data
    ? Object.values(data.columns ?? {}).flat().length
    : null;

  return (
    <div className="mx-auto max-w-[1600px] space-y-4">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="flex items-baseline gap-3 text-2xl font-semibold tracking-tight">
            Applications
            <span className="text-sm font-normal text-neutral-500">
              {totalApps !== null ? `${totalApps} active` : "…"}
            </span>
          </h1>
          <p className="text-sm text-neutral-500">
            Drag cards between columns to update status.
          </p>
        </div>
      </header>

      {isLoading ? (
        <KanbanSkeleton />
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={onDragEnd}
        >
          <div className="flex gap-4 overflow-x-auto pb-4">
            {PHASES.map((phase) => (
              <div key={phase.tone} className="flex shrink-0 gap-2">
                {phase.statuses.map((s) => {
                  const items = data?.columns?.[s.id] ?? [];
                  return (
                    <KanbanColumn
                      key={s.id}
                      status={s.id}
                      label={s.label}
                      tone={phase.tone}
                      items={items}
                    />
                  );
                })}
                <div className="h-full w-px bg-neutral-800/60 last:hidden" aria-hidden />
              </div>
            ))}
          </div>
        </DndContext>
      )}
    </div>
  );
}

function KanbanColumn({
  status,
  label,
  tone,
  items,
}: {
  status: string;
  label: string;
  tone: string;
  items: Application[];
}) {
  const { setNodeRef, isOver } = useDroppable({ id: status });
  return (
    <div
      ref={setNodeRef}
      className={cn(
        "flex w-[240px] shrink-0 flex-col rounded-card border bg-neutral-900/40 p-2 transition-colors",
        isOver
          ? "border-brand-blue bg-neutral-900"
          : "border-neutral-800/80",
      )}
    >
      <div className="mb-2.5 flex items-center justify-between px-1.5">
        <h2 className="flex items-center gap-2 text-[11px] font-medium uppercase tracking-wider text-neutral-300">
          <span className={cn("h-1.5 w-1.5 rounded-full", TONE_DOT[tone])} />
          {label}
        </h2>
        <span className="font-mono text-[11px] text-neutral-500">{items.length}</span>
      </div>
      <SortableContext
        items={items.map((a) => `app-${a.id}`)}
        strategy={verticalListSortingStrategy}
      >
        <div className="flex min-h-[40px] flex-col gap-2">
          {items.length === 0 ? (
            <div className="rounded-button border border-dashed border-neutral-800/80 px-2 py-3 text-center text-[11px] text-neutral-600">
              empty
            </div>
          ) : (
            items.map((app) => <ApplicationCard key={app.id} application={app} />)
          )}
        </div>
      </SortableContext>
    </div>
  );
}

function ApplicationCard({ application }: { application: Application }) {
  const { setNodeRef, attributes, listeners, transform, transition, isDragging } =
    useSortable({ id: `app-${application.id}` });
  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Translate.toString(transform),
        transition,
      }}
      className={cn(
        "group relative rounded-button border border-neutral-800 bg-neutral-950/80 p-2.5 transition-colors hover:border-neutral-700",
        isDragging && "z-10 shadow-lg shadow-black/50",
      )}
    >
      <div className="flex items-start gap-2">
        <button
          type="button"
          {...attributes}
          {...listeners}
          className="cursor-grab pt-0.5 text-neutral-700 hover:text-neutral-400 active:cursor-grabbing"
          aria-label="Drag to reorder"
        >
          <GripVertical className="h-3.5 w-3.5" strokeWidth={1.75} />
        </button>
        <div className="min-w-0 flex-1">
          <Link
            href={`/applications/${application.id}`}
            className="block truncate text-sm font-medium hover:text-brand-blue"
          >
            App #{application.id}
          </Link>
          <div className="truncate text-[11px] text-neutral-500">
            Job #{application.job_id ?? "—"}
          </div>
          {application.notes && (
            <p className="mt-1.5 line-clamp-2 text-[11px] leading-relaxed text-neutral-400">
              {application.notes}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function KanbanSkeleton() {
  return (
    <div className="flex gap-2 overflow-x-auto pb-4">
      {Array.from({ length: 6 }, (_, i) => (
        <div
          key={i}
          className="flex w-[240px] shrink-0 flex-col gap-2 rounded-card border border-neutral-800/60 bg-neutral-900/30 p-2"
        >
          <div className="h-3 w-20 rounded skeleton" />
          <div className="h-16 rounded-button skeleton" />
          <div className="h-12 rounded-button skeleton" />
        </div>
      ))}
    </div>
  );
}
