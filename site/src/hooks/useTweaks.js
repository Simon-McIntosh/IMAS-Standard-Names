import { useCallback, useState } from 'react';

const KEY = 'isnc-tweaks-v1';

export const TWEAK_DEFAULTS = {
  density: 'comfortable',
  theme: 'light',
  groupBy: 'cluster',
  showWelcome: true,
  accent: '#3654c8',
};

// Tweak values are persisted to localStorage. Reload preserves every
// user-visible choice (theme, density, accent, grouping) so the SPA
// "remembers" its appearance per browser. There is no host-protocol
// fallback — this is the production replacement for the prototype's
// __edit_mode_set_keys postMessage scheme.
export function useTweaks() {
  const [values, setValues] = useState(() => {
    if (typeof localStorage === 'undefined') return TWEAK_DEFAULTS;
    try {
      const raw = localStorage.getItem(KEY);
      return raw ? { ...TWEAK_DEFAULTS, ...JSON.parse(raw) } : TWEAK_DEFAULTS;
    } catch {
      return TWEAK_DEFAULTS;
    }
  });

  // Accepts either setTweak('key', value) or setTweak({ key: value, ... }).
  const setTweak = useCallback((keyOrEdits, val) => {
    const edits =
      typeof keyOrEdits === 'object' && keyOrEdits !== null
        ? keyOrEdits
        : { [keyOrEdits]: val };
    setValues((prev) => {
      const next = { ...prev, ...edits };
      try {
        if (typeof localStorage !== 'undefined') {
          localStorage.setItem(KEY, JSON.stringify(next));
        }
      } catch {
        /* ignore quota / private-mode errors */
      }
      return next;
    });
  }, []);

  return [values, setTweak];
}
