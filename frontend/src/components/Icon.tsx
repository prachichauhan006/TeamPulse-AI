import type { SVGProps } from "react";

const paths: Record<string, string> = {
  dashboard: "M4 13h6V4H4v9Zm0 7h6v-5H4v5Zm10 0h6v-9h-6v9Zm0-16v5h6V4h-6Z",
  projects: "M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z",
  tasks: "m5 12 4 4L19 6M4 4h16v16H4z",
  sparkles: "m12 3 1.4 4.6L18 9l-4.6 1.4L12 15l-1.4-4.6L6 9l4.6-1.4L12 3Zm7 11 .8 2.2L22 17l-2.2.8L19 20l-.8-2.2L16 17l2.2-.8L19 14Z",
  notes: "M5 3h14v18H5zM8 7h8M8 11h8M8 15h5",
  documents: "M6 2h8l4 4v16H6zM14 2v5h5M9 12h6M9 16h6",
  search: "m20 20-4.5-4.5M11 18a7 7 0 1 1 0-14 7 7 0 0 1 0 14Z",
  audit: "M12 8v5l3 2M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z",
  settings: "M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm0-13 1 3 3 .8 2.5-1.5 2 3.5-2 2.5.5 3 2 2.5-2 3.5-3.5-1-2.5 2-.5 3h-4l-.5-3-2.5-2-3.5 1-2-3.5 2-2.5.5-3-2-2.5 2-3.5 3.5 1 2.5-2 .5-3h4Z",
  menu: "M4 6h16M4 12h16M4 18h16",
  close: "m6 6 12 12M18 6 6 18",
  plus: "M12 5v14M5 12h14",
  logout: "M10 4H5v16h5M14 8l4 4-4 4M8 12h10",
  users: "M16 20v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2M9.5 10a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm7.5 1a3 3 0 0 0 0-6M21 20v-2a4 4 0 0 0-3-3.8",
  check: "m5 12 4 4L19 6",
  warning: "M12 9v4m0 4h.01M10.3 3.7 2.5 18a2 2 0 0 0 1.8 3h15.4a2 2 0 0 0 1.8-3L13.7 3.7a2 2 0 0 0-3.4 0Z",
  edit: "m4 16-.8 4.8L8 20l11-11-4-4L4 16Zm9-9 4 4M14 5l2-2 4 4-2 2",
  trash: "M4 7h16M10 11v6M14 11v6M6 7l1 14h10l1-14M9 7V4h6v3",
  chevron: "m9 18 6-6-6-6",
  shield: "M12 3 4 6v5c0 5 3.4 8.5 8 10 4.6-1.5 8-5 8-10V6l-8-3Zm-3 9 2 2 4-4",
  upload: "M12 16V4m0 0L7 9m5-5 5 5M4 15v5h16v-5",
  grip: "M8 6h.01M8 12h.01M8 18h.01M16 6h.01M16 12h.01M16 18h.01",
  link: "M10 13a5 5 0 0 0 7.1.1l2-2a5 5 0 0 0-7.1-7.1l-1.1 1.1M14 11a5 5 0 0 0-7.1-.1l-2 2A5 5 0 0 0 12 20l1.1-1.1",
  calendar: "M6 2v4M18 2v4M3 9h18M5 4h14a2 2 0 0 1 2 2v14H3V6a2 2 0 0 1 2-2Z",
  filter: "M4 5h16M7 12h10M10 19h4",
  arrow: "M5 12h14m-6-6 6 6-6 6",
};

export function Icon({ name, ...props }: { name: keyof typeof paths } & SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      <path d={paths[name]} />
    </svg>
  );
}
