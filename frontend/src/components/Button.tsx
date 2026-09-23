import type { ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'secondary' | 'danger-outline' | 'ghost'

const VARIANT_CLASSES: Record<Variant, string> = {
  primary: 'bg-brand-blue text-white hover:bg-brand-blue-dark border border-transparent',
  secondary: 'bg-bg-card text-text-primary border border-border-strong hover:bg-bg-hover',
  'danger-outline': 'bg-white text-danger-text border border-danger-border hover:bg-danger-bg',
  ghost: 'bg-transparent text-text-secondary border border-transparent hover:bg-bg-hover',
}

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
}

export function Button({ variant = 'primary', className = '', ...rest }: Props) {
  return (
    <button
      className={`inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${VARIANT_CLASSES[variant]} ${className}`}
      {...rest}
    />
  )
}

export function IconButton({ className = '', ...rest }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={`inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border-default bg-white text-text-secondary hover:bg-bg-hover ${className}`}
      {...rest}
    />
  )
}
