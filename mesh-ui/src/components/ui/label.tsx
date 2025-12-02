//components/ui/label.tsx
import React from 'react'
import { cn } from '@/lib/utils'

export type LabelProps = React.LabelHTMLAttributes<HTMLLabelElement>

export const Label = React.forwardRef<HTMLLabelElement, LabelProps>(
  ({ className, ...props }, ref) => (
    <label
      ref={ref}
      className={cn(
        'text-sm font-medium text-slate-700 dark:text-slate-200',
        className,
      )}
      {...props}
    />
  ),
)

Label.displayName = 'Label'
