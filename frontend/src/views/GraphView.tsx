"use client";

/**
 * The shared career knowledge graph (backend: app/knowledge, routes in API_ENDPOINTS.graph).
 *
 * Everything drawn here is anonymous: edges from profiles appear only once `minUsers`
 * people back them, edges from real job postings always. "You have" / "gap" marks come
 * from the signed-in user's own (private) links.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, Search } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/context/AuthContext";
import { API_ENDPOINTS } from "@/lib/api";
import { cn } from "@/lib/utils";

interface GraphNode {
  kind: "skill" | "role" | "company";
  key: string;
  label: string;
}
interface Neighbour {
  node: GraphNode;
  relation: string;
  users: number;
  postings: number;
  yours: boolean;
}
interface MyGraph {
  links: { relation: string; node: GraphNode }[];
  roles: { role: GraphNode; skills: Neighbour[]; companies: Neighbour[]; nextRoles: Neighbour[] }[];
  adjacentSkills: Neighbour[];
  minUsers: number;
}
interface NodeDetail {
  node: GraphNode;
  groups: Record<string, Neighbour[]>;
}

const GROUP_LABELS: Record<string, string> = {
  skills: "Skills most associated",
  companies: "Companies seen hiring",
  nextRoles: "People move on to",
  // node detail groups arrive with the backend's snake_case keys
  next_roles: "People move on to",
  previous_roles: "People arrive from",
  roles: "Roles that use it",
  pairs_with: "Often paired with",
  hires_for: "Hires for",
};

function support(n: Neighbour): string {
  const parts: string[] = [];
  if (n.postings) parts.push(`${n.postings} posting${n.postings === 1 ? "" : "s"}`);
  if (n.users) parts.push(`${n.users} people`);
  return parts.join(" · ");
}

/* ── Radial graph ─────────────────────────────────────────────────────────── */

const SIZE = 440;
const CENTER = SIZE / 2;
const RADIUS = 150;

function RadialGraph({
  center,
  neighbours,
  onSelect,
}: {
  center: GraphNode;
  neighbours: Neighbour[];
  onSelect: (node: GraphNode) => void;
}) {
  const shown = neighbours.slice(0, 18);
  const max = Math.max(1, ...shown.map((n) => n.users + n.postings));
  return (
    <svg
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      className="h-auto w-full max-w-[520px]"
      role="img"
      aria-label={`${center.label} and ${shown.length} connected nodes`}
    >
      {shown.map((n, i) => {
        const angle = (2 * Math.PI * i) / shown.length - Math.PI / 2;
        const x = CENTER + RADIUS * Math.cos(angle);
        const y = CENTER + RADIUS * Math.sin(angle);
        const weight = (n.users + n.postings) / max;
        const right = Math.cos(angle) >= 0;
        const gap = n.node.kind === "skill" && !n.yours;
        return (
          <g
            key={`${n.node.kind}:${n.node.key}`}
            className="cursor-pointer"
            onClick={() => onSelect(n.node)}
            role="button"
            tabIndex={0}
            onKeyDown={(event) => (event.key === "Enter" ? onSelect(n.node) : undefined)}
          >
            <title>{`${n.node.label} — ${support(n)}`}</title>
            <line
              x1={CENTER}
              y1={CENTER}
              x2={x}
              y2={y}
              className="stroke-border"
              strokeWidth={1 + 3 * weight}
            />
            <circle
              cx={x}
              cy={y}
              r={5 + 5 * weight}
              className={cn(
                n.node.kind === "company"
                  ? "fill-background stroke-muted-foreground"
                  : n.node.kind === "role"
                    ? "fill-muted-foreground stroke-muted-foreground"
                    : gap
                      ? "fill-background stroke-foreground"
                      : "fill-foreground stroke-foreground",
              )}
              strokeWidth={1.5}
              strokeDasharray={gap ? "2 2" : undefined}
            />
            <text
              x={x + (right ? 12 : -12)}
              y={y + 3}
              textAnchor={right ? "start" : "end"}
              className="fill-foreground text-[10px]"
            >
              {n.node.label.length > 22 ? `${n.node.label.slice(0, 21)}…` : n.node.label}
            </text>
          </g>
        );
      })}
      <circle cx={CENTER} cy={CENTER} r={30} className="fill-foreground" />
      <text
        x={CENTER}
        y={CENTER + 3}
        textAnchor="middle"
        className="fill-background text-[9px] font-semibold"
      >
        {center.label.length > 14 ? `${center.label.slice(0, 13)}…` : center.label}
      </text>
    </svg>
  );
}

/* ── Page ─────────────────────────────────────────────────────────────────── */

export function GraphPage() {
  return (
    <AppShell>
      <GraphExplorer />
    </AppShell>
  );
}

function GraphExplorer() {
  const { authFetch } = useAuth();
  const [me, setMe] = useState<MyGraph | null>(null);
  const [roleIndex, setRoleIndex] = useState(0);
  const [detail, setDetail] = useState<NodeDetail | null>(null); // exploring another node
  const [paths, setPaths] = useState<GraphNode[][]>([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<GraphNode[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    authFetch<MyGraph>(API_ENDPOINTS.graph.me)
      .then((response) => setMe(response.data))
      .catch((err: Error) => setError(err.message));
  }, [authFetch]);

  const mySkills = useMemo(
    () => new Set(me?.links.filter((l) => l.relation === "has_skill").map((l) => l.node.key) ?? []),
    [me],
  );

  const role = me?.roles[roleIndex];
  const center: GraphNode | undefined = detail?.node ?? role?.role;
  const groups: Record<string, Neighbour[]> = useMemo(() => {
    if (detail) {
      // Mark "yours" on explored nodes too (from your own links, client-side).
      return Object.fromEntries(
        Object.entries(detail.groups).map(([name, items]) => [
          name,
          items.map((n) => ({ ...n, yours: n.node.kind === "skill" && mySkills.has(n.node.key) })),
        ]),
      );
    }
    if (!role) return {};
    return { skills: role.skills, companies: role.companies, nextRoles: role.nextRoles };
  }, [detail, role, mySkills]);
  const neighbours = useMemo(() => Object.values(groups).flat(), [groups]);

  useEffect(() => {
    if (!center || center.kind !== "role") {
      setPaths([]);
      return;
    }
    const params = new URLSearchParams({ role: center.label });
    authFetch<{ paths: GraphNode[][] }>(`${API_ENDPOINTS.graph.paths}?${params}`)
      .then((response) => setPaths(response.data?.paths ?? []))
      .catch(() => setPaths([]));
  }, [authFetch, center]);

  const explore = useCallback(
    (node: GraphNode) => {
      setResults([]);
      authFetch<NodeDetail>(API_ENDPOINTS.graph.node(node.kind, node.key))
        .then((response) => setDetail(response.data))
        .catch((err: Error) => setError(err.message));
    },
    [authFetch],
  );

  const search = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!query.trim()) return;
    const params = new URLSearchParams({ q: query.trim() });
    try {
      const response = await authFetch<GraphNode[]>(`${API_ENDPOINTS.graph.search}?${params}`);
      setResults(response.data ?? []);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="mx-auto w-full max-w-[1440px] px-6 py-10 lg:px-10 xl:px-14">
      <header className="mb-8 max-w-2xl">
        <h1 className="text-2xl font-semibold tracking-tight">Career graph</h1>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          Shared, anonymous knowledge from everyone&apos;s profiles and from real job postings:
          which skills go with which roles, who is hiring, and where people move next. A link from
          profiles appears only once {me?.minUsers ?? 3}+ people share it. Your own skills and roles
          stay private and only mark what you already have.
        </p>
      </header>

      {error ? (
        <p className="mb-6 rounded-md border border-dashed border-border p-3 text-xs text-muted-foreground">
          {error}
        </p>
      ) : null}

      <div className="mb-6 flex flex-wrap items-center gap-2">
        {me?.roles.map((r, i) => (
          <button
            key={r.role.key}
            type="button"
            onClick={() => {
              setDetail(null);
              setRoleIndex(i);
            }}
            className={cn(
              "rounded-full border px-3 py-1 text-xs transition-colors",
              !detail && i === roleIndex
                ? "border-foreground bg-foreground text-background"
                : "border-border hover:border-foreground",
            )}
          >
            {r.role.label}
          </button>
        ))}
        {detail ? (
          <button
            type="button"
            onClick={() => setDetail(null)}
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft size={12} /> Back to my roles
          </button>
        ) : null}
        <form onSubmit={search} className="ml-auto flex items-center gap-2">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search a skill, role or company"
            aria-label="Search the graph"
            className="h-8 w-64 rounded-md border border-border bg-background px-3 text-xs outline-none focus:border-foreground"
          />
          <button
            type="submit"
            aria-label="Search"
            className="flex h-8 w-8 items-center justify-center rounded-md border border-border hover:border-foreground"
          >
            <Search size={13} />
          </button>
        </form>
      </div>

      {results.length > 0 ? (
        <div className="mb-6 flex flex-wrap gap-2">
          {results.map((node) => (
            <button
              key={`${node.kind}:${node.key}`}
              type="button"
              onClick={() => explore(node)}
              className="rounded-md border border-border px-2.5 py-1 text-xs hover:border-foreground"
            >
              {node.label} <span className="text-muted-foreground">· {node.kind}</span>
            </button>
          ))}
        </div>
      ) : null}

      {me && !center ? (
        <p className="text-sm text-muted-foreground">
          Add target roles and skills to your profile to place yourself in the graph.
        </p>
      ) : null}

      {center ? (
        <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div className="flex flex-col items-center">
            {neighbours.length > 0 ? (
              <RadialGraph center={center} neighbours={neighbours} onSelect={explore} />
            ) : (
              <p className="max-w-sm py-16 text-center text-sm text-muted-foreground">
                Nothing shared about {center.label} yet. It fills in as more people add it and as
                the Job Search agent finds postings for it.
              </p>
            )}
            <div className="mt-4 flex flex-wrap justify-center gap-4 text-[10px] text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-foreground" /> skill you have
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full border border-dashed border-foreground" />{" "}
                skill gap
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-muted-foreground" /> role
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full border border-muted-foreground" /> company
              </span>
            </div>
          </div>

          <div className="space-y-6">
            {Object.entries(groups)
              .filter(([, items]) => items.length > 0)
              .map(([name, items]) => (
                <section key={name}>
                  <h2 className="mb-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                    {GROUP_LABELS[name] ?? name}
                  </h2>
                  <ul className="divide-y divide-border rounded-md border border-border">
                    {items.map((n) => (
                      <li key={`${n.node.kind}:${n.node.key}`}>
                        <button
                          type="button"
                          onClick={() => explore(n.node)}
                          className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-xs hover:bg-muted/50"
                        >
                          <span className="flex items-center gap-2">
                            {n.node.label}
                            {n.node.kind === "skill" ? (
                              <span
                                className={cn(
                                  "rounded-full px-1.5 py-px text-[9px]",
                                  n.yours
                                    ? "bg-muted text-foreground"
                                    : "border border-dashed border-border text-muted-foreground",
                                )}
                              >
                                {n.yours ? "you have" : "gap"}
                              </span>
                            ) : null}
                          </span>
                          <span className="shrink-0 text-[10px] tabular-nums text-muted-foreground">
                            {support(n)}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              ))}

            {paths.length > 0 ? (
              <section>
                <h2 className="mb-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                  Career paths from {center.label}
                </h2>
                <ul className="space-y-1.5 text-xs">
                  {paths.map((path) => (
                    <li key={path.map((n) => n.key).join(">")} className="text-muted-foreground">
                      {path.map((n, i) => (
                        <span key={n.key}>
                          {i > 0 ? " → " : ""}
                          <span className={i === 0 ? "" : "text-foreground"}>{n.label}</span>
                        </span>
                      ))}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            {!detail && me && me.adjacentSkills.length > 0 ? (
              <section>
                <h2 className="mb-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                  Skills often paired with yours
                </h2>
                <div className="flex flex-wrap gap-1.5">
                  {me.adjacentSkills.map((n) => (
                    <button
                      key={n.node.key}
                      type="button"
                      onClick={() => explore(n.node)}
                      title={support(n)}
                      className="rounded-full border border-dashed border-border px-2 py-0.5 text-[10px] hover:border-foreground"
                    >
                      {n.node.label}
                    </button>
                  ))}
                </div>
              </section>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
