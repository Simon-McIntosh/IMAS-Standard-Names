import { Filters } from '../components/Filters.jsx';
import { ResultsList } from '../components/ResultsList.jsx';
import { DetailPanel } from '../components/DetailPanel.jsx';

// Three-pane browse layout. Thin wrapper around the three top-level
// components so App.jsx stays focused on state.
export function Browse({
  filters, setFilters, faceted, allCounts,
  results, selected, setSelected,
  dense, groupBy, setGroupBy,
  childIndex, groupIndex,
}) {
  return (
    <div className="app-body">
      <Filters
        filters={filters}
        setFilters={setFilters}
        faceted={faceted}
        allCounts={allCounts}
      />
      <ResultsList
        results={results}
        selected={selected}
        onSelect={setSelected}
        dense={dense}
        groupBy={groupBy}
        setGroupBy={setGroupBy}
      />
      <DetailPanel
        name={selected}
        onSelect={setSelected}
        onClose={() => setSelected(null)}
        childIndex={childIndex}
        groupIndex={groupIndex}
      />
    </div>
  );
}
