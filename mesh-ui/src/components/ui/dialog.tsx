//components/ui/dialog.tsx
import React from 'react'
import { cn } from '@/lib/utils'

type DialogProps = {
  open?: boolean
  onOpenChange?: (open: boolean) => void
  children: React.ReactNode
}

const DialogContext = React.createContext<
  { open: boolean; setOpen: (v: boolean) => void } | undefined
>(undefined)

export function Dialog({ open, onOpenChange, children }: DialogProps) {
  const [internalOpen, setInternalOpen] = React.useState(!!open)
  const actualOpen = open ?? internalOpen

  const setOpen = (v: boolean) => {
    if (onOpenChange) onOpenChange(v)
    else setInternalOpen(v)
  }

  return (
    <DialogContext.Provider value={{ open: actualOpen, setOpen }}>
      {children}
    </DialogContext.Provider>
  )
}

export function DialogTrigger({
  asChild,
  children,
}: {
  asChild?: boolean
  children: React.ReactElement<any>
}) {
  const ctx = React.useContext(DialogContext)
  if (!ctx) return children

  const onClick = (e: React.MouseEvent) => {
    (children.props as any).onClick?.(e)
    ctx.setOpen(true)
  }

  return React.cloneElement(children, { onClick })
}

export function DialogContent({
  className,
  children,
}: {
  className?: string
  children: React.ReactNode
}) {
  const ctx = React.useContext(DialogContext)
  if (!ctx || !ctx.open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div
        className={cn(
          'w-full max-w-md rounded-2xl bg-white dark:bg-slate-900 p-6 shadow-xl',
          className,
        )}
      >
        {children}
      </div>
    </div>
  )
}




export function DialogHeader({
  children,
}: {
  children: React.ReactNode
}) {
  return <div className="mb-2">{children}</div>
}

export function DialogTitle({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
      {children}
    </h2>
  )
}
