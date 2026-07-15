import { describe, expect, it } from 'vitest';
import { ddDocumentationUrl } from '../../src/lib/dd-links.js';

describe('DD documentation links', () => {
  it('links to the exact pinned version and deterministic node anchor', () => {
    expect(ddDocumentationUrl('summary/global_quantities/energy_thermal/value', '4.0.0')).toBe(
      'https://imas-data-dictionary.readthedocs.io/en/4.0.0/generated/ids/summary.html#summary-global_quantities-energy_thermal-value',
    );
  });

  it('fails closed when the pinned version is absent', () => {
    expect(ddDocumentationUrl('summary/global_quantities/ip', '')).toBeNull();
  });
});
