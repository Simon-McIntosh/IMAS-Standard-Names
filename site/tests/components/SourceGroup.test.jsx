import { describe, expect, it } from 'vitest';
import { fireEvent, render } from '@testing-library/react';
import { SourceGroup } from '../../src/components/SourceGroup.jsx';

const source = {
  kind: 'imas-dd',
  ref: 'summary/global_quantities/energy_thermal/value',
  version: '4.0.0',
  leaf_definition: 'Value',
  parent_path: 'summary/global_quantities/energy_thermal',
  parent_definition: 'Thermal plasma energy.',
  enhanced_context: 'Generated contextual explanation.',
  enhancement_kind: 'generated',
};

describe('SourceGroup', () => {
  it('uses pinned links and labels generated context separately', () => {
    const { getByRole, getByText } = render(<SourceGroup ids="summary" items={[source]} />);
    expect(getByRole('link', { name: /summary/ }).href).toContain('/en/4.0.0/');
    fireEvent.click(getByRole('button', { name: /Show source information/ }));
    expect(getByText('Thermal plasma energy.')).toBeInTheDocument();
    expect(getByText('Derived context')).toBeInTheDocument();
    expect(getByText(/From parent/)).toBeInTheDocument();
  });

  it('does not invent a latest link for an unpinned source', () => {
    const { container } = render(
      <SourceGroup ids="summary" items={[{ kind: 'imas-dd', ref: source.ref }]} />,
    );
    expect(container.querySelector('a.source-path')).toBeNull();
    expect(container.textContent).not.toContain('latest');
  });

  it('keeps an unresolved binding visible with its own content', () => {
    const unresolved = {
      kind: 'imas-dd',
      ref: 'summary/global_quantities/not_a_dd_leaf',
      version: '4.0.0',
      resolution_status: 'unresolved',
      resolution_error: 'LookupError: no such leaf',
    };
    const { getByText } = render(
      <SourceGroup ids="summary" items={[unresolved]} />,
    );
    expect(getByText('global_quantities/not_a_dd_leaf ↗')).toBeInTheDocument();
    expect(getByText('Unresolved')).toBeVisible();
  });
});
