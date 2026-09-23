import { BellIcon, GearIcon, GridIcon, HelpCircleIcon } from './icons'

export function AppHeader() {
  return (
    <header className="flex h-14 items-center justify-between border-b border-border-default bg-white px-6">
      <div className="flex items-center gap-4">
        <span className="text-lg font-bold tracking-tight text-text-primary">
          AERCH<span className="text-brand-blue">A</span>IN
        </span>
        <GridIcon className="text-text-tertiary" />
      </div>
      <div className="flex items-center gap-4">
        <HelpCircleIcon className="text-text-secondary" />
        <GearIcon className="text-text-secondary" />
        <div className="relative">
          <BellIcon className="text-text-secondary" />
          <span className="absolute -right-1.5 -top-1.5 rounded-full bg-danger-text px-1 text-[10px] font-semibold leading-tight text-white">
            9+
          </span>
        </div>
        <div className="ml-2 flex items-center gap-2 border-l border-border-default pl-4">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-amber-500 text-xs font-semibold text-white">
            Y
          </span>
          <span className="text-sm text-text-secondary">YoloMart</span>
        </div>
      </div>
    </header>
  )
}
