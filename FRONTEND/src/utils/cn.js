import clsx from 'clsx'

/**
 * Tiny className combiner. Thin wrapper over clsx so we have a single
 * import (`cn`) everywhere and can swap implementations later.
 */
export function cn(...inputs) {
  return clsx(inputs)
}
