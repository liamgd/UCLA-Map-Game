import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import SearchBox from './SearchBox';
import { useStore } from '../store';

const mockFuse = {
  search: vi.fn(() => [{ item: { properties: { id: '1', name: 'Test Building' } } }]),
};

describe('SearchBox', () => {
  beforeEach(() => {
    useStore.setState({ selectedId: null, query: '', activeIndex: -1 });
    mockFuse.search.mockClear();
  });

  it('shows results and updates store on select', () => {
    render(<SearchBox fuse={mockFuse} />);
    const input = screen.getByPlaceholderText(/search buildings/i);
    fireEvent.change(input, { target: { value: 'Te' } });

    expect(mockFuse.search).toHaveBeenCalledWith('Te');

    const option = screen.getByRole('option', { name: 'Test Building' });
    fireEvent.mouseDown(option);

    expect(useStore.getState().selectedId).toBe('1');
    expect(input.value).toBe('Test Building');
  });
});
