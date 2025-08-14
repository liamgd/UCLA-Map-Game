import { describe, it, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { useStore } from './store.js';

afterEach(() => {
  useStore.setState({ selectedId: null, query: '', activeIndex: -1 });
});

describe('useStore', () => {
  it('updates selectedId', () => {
    const { setSelectedId } = useStore.getState();
    setSelectedId('abc');
    assert.equal(useStore.getState().selectedId, 'abc');
  });

  it('updates query and activeIndex', () => {
    const { setQuery, setActiveIndex } = useStore.getState();
    setQuery('hi');
    setActiveIndex(2);
    const state = useStore.getState();
    assert.equal(state.query, 'hi');
    assert.equal(state.activeIndex, 2);
  });
});
