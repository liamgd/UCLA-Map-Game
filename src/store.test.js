import { describe, it, expect, afterEach } from 'vitest';
import { useStore } from './store';

afterEach(() => {
  useStore.setState({ selectedId: null, query: '', activeIndex: -1 });
});

describe('useStore', () => {
  it('updates selectedId', () => {
    const { setSelectedId } = useStore.getState();
    setSelectedId('abc');
    expect(useStore.getState().selectedId).toBe('abc');
  });

  it('updates query and activeIndex', () => {
    const { setQuery, setActiveIndex } = useStore.getState();
    setQuery('hi');
    setActiveIndex(2);
    const state = useStore.getState();
    expect(state.query).toBe('hi');
    expect(state.activeIndex).toBe(2);
  });
});
