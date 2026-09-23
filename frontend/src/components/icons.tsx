import type { SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement>

function base(props: IconProps, children: React.ReactNode) {
  return (
    <svg
      width={props.width ?? 18}
      height={props.height ?? 18}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      {children}
    </svg>
  )
}

export const ChevronLeftIcon = (p: IconProps) => base(p, <path d="M15 18l-6-6 6-6" />)
export const ChevronDownIcon = (p: IconProps) => base(p, <path d="M6 9l6 6 6-6" />)
export const ChevronRightIcon = (p: IconProps) => base(p, <path d="M9 18l6-6-6-6" />)
export const PlusIcon = (p: IconProps) => base(p, <path d="M12 5v14M5 12h14" />)
export const XIcon = (p: IconProps) => base(p, <path d="M18 6L6 18M6 6l12 12" />)
export const SearchIcon = (p: IconProps) =>
  base(p, <><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.35-4.35" /></>)
export const SendIcon = (p: IconProps) =>
  base(p, <><path d="M22 2L11 13" /><path d="M22 2l-7 20-4-9-9-4 20-7z" /></>)
export const PaperclipIcon = (p: IconProps) =>
  base(p, <path d="M21 11.05l-9.19 9.19a5 5 0 01-7.07-7.07l9.19-9.19a3 3 0 014.24 4.24l-9.2 9.19a1 1 0 01-1.41-1.41l8.49-8.48" />)
export const BellIcon = (p: IconProps) =>
  base(p, <><path d="M18 8a6 6 0 00-12 0c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 01-3.46 0" /></>)
export const GearIcon = (p: IconProps) =>
  base(p, <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" /></>)
export const HelpCircleIcon = (p: IconProps) =>
  base(p, <><circle cx="12" cy="12" r="9" /><path d="M9.1 9a3 3 0 015.8 1c0 2-3 2-3 4" /><circle cx="12" cy="17" r="0.6" fill="currentColor" stroke="none" /></>)
export const GridIcon = (p: IconProps) =>
  base(p, <>{[5, 12, 19].flatMap((cy) => [5, 12, 19].map((cx) => (
    <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r="1.4" fill="currentColor" stroke="none" />
  )))}</>)
export const PencilIcon = (p: IconProps) =>
  base(p, <><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" /><path d="M18.5 2.5a2.12 2.12 0 013 3L12 15l-4 1 1-4 9.5-9.5z" /></>)
export const ClockIcon = (p: IconProps) =>
  base(p, <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" /></>)
export const DocumentIcon = (p: IconProps) =>
  base(p, <><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" /><path d="M14 2v6h6" /></>)
export const CheckIcon = (p: IconProps) => base(p, <path d="M20 6L9 17l-5-5" />)
export const InfoCircleIcon = (p: IconProps) =>
  base(p, <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="8" r="0.6" fill="currentColor" stroke="none" /><path d="M12 11.5v5" /></>)
export const SparkleIcon = (p: IconProps) => base(p, <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" />)
export const AlertTriangleIcon = (p: IconProps) =>
  base(p, <><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" /><path d="M12 9v4" /><circle cx="12" cy="17" r="0.6" fill="currentColor" stroke="none" /></>)
