import { describe, expect, it } from 'vitest';
import { act, render } from '@testing-library/react';
import { Header } from '../../src/components/Header.jsx';
import { DataProvider } from '../../src/lib/data.js';

function renderHeader() {
  return render(
    <DataProvider>
      <Header
        query=""
        setQuery={() => {}}
        theme="light"
        setTheme={() => {}}
        dense="comfortable"
        setDense={() => {}}
        view="browse"
        setView={() => {}}
      />
    </DataProvider>,
  );
}

describe('Header density segment', () => {
  it('renders three list-row mock buttons (not three text glyphs)', async () => {
    let container;
    await act(async () => {
      ({ container } = renderHeader());
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    const seg = container.querySelector('.seg.density-seg');
    expect(seg).not.toBeNull();
    const buttons = seg.querySelectorAll('button');
    expect(buttons.length).toBe(3);
    // Each density button should embed an SVG, not a unicode character.
    buttons.forEach((btn) => {
      expect(btn.querySelector('svg')).not.toBeNull();
    });
  });
});

describe('Header Browse icon', () => {
  it('renders the Browse button with a 2×2 grid SVG (four rects)', async () => {
    let container;
    await act(async () => {
      ({ container } = renderHeader());
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    const browseBtn = Array.from(container.querySelectorAll('button')).find(
      (b) => b.textContent.includes('Browse'),
    );
    expect(browseBtn).toBeTruthy();
    const rects = browseBtn.querySelectorAll('svg rect');
    expect(rects.length).toBe(4);
  });
});
